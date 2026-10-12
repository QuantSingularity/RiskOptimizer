import json

import numpy as np
import pandas as pd
from quant_ml.data.loaders import load_close_prices
from quant_ml.optimization.portfolio import AdvancedPortfolioOptimizer
from quant_ml.reporting import (
    ReportArchive,
    ReportGenerator,
    ReportScheduler,
    ReportTemplate,
)
from quant_ml.risk import CopulaMLRiskModel, ExtremeValueRisk, ParallelRiskEngine
from quant_ml.risk.analysis import run_risk_analysis
from quant_ml.serialization import to_jsonable
from quant_ml.training.cli import main as train_main
from quant_ml.training.trainer import train_and_save

SYMBOLS = ["AAPL", "MSFT", "TSLA", "BTC_USD"]


class TestTrainingToServing:
    def test_train_save_reload_optimize(self, tmp_path):
        path = tmp_path / "model.joblib"
        trained, report, saved = train_and_save(str(path), SYMBOLS)
        loaded = AdvancedPortfolioOptimizer.load_model(saved)
        prices = load_close_prices(SYMBOLS)
        before, _ = trained.optimize_portfolio(prices)
        after, _ = loaded.optimize_portfolio(prices)
        assert np.allclose(list(before.values()), list(after.values()))
        assert report["prediction_metrics"]["samples"] > 100

    def test_cli_trains_and_saves(self, tmp_path):
        path = tmp_path / "cli.joblib"
        code = train_main(
            ["--symbols", *SYMBOLS, "--model-path", str(path), "--visualize"]
        )
        assert code == 0 and path.exists()
        assert (tmp_path / "visualizations" / "efficient_frontier.png").exists()

    def test_environment_model_path_is_honoured(self, tmp_path, monkeypatch):
        monkeypatch.setenv("MODEL_PATH", str(tmp_path / "env.joblib"))
        _, _, saved = train_and_save(None, SYMBOLS)
        assert saved == str(tmp_path / "env.joblib")


class TestRiskStack:
    def test_models_agree_within_reason(self, real_returns):
        weights = np.full(real_returns.shape[1], 1 / real_returns.shape[1])
        series = real_returns.to_numpy() @ weights
        empirical = -np.quantile(series, 0.05)
        copula = (
            CopulaMLRiskModel("t", 30000, seed=1)
            .fit(real_returns)
            .calculate_var(weights, 0.95)
        )
        engine = ParallelRiskEngine(n_jobs=1, seed=1)
        batch = engine.parallel_batch_risk_calculation(
            real_returns, ["historical", "evt", "parametric"], [0.95]
        )
        values = [copula] + [m["var_95"] for m in batch["risk_metrics"].values()]
        assert all(abs(v - empirical) / empirical < 0.2 for v in values)

    def test_every_engine_output_is_json_serializable(self, real_returns):
        weights = {c: 1 / real_returns.shape[1] for c in real_returns.columns}
        engine = ParallelRiskEngine(n_jobs=1, seed=2)
        model = CopulaMLRiskModel("gaussian", 2000, seed=1).fit(real_returns)
        outputs = [
            engine.parallel_monte_carlo(model, weights, 2000),
            engine.parallel_portfolio_optimization(real_returns, "markowitz", 500),
            engine.parallel_batch_risk_calculation(real_returns, weights=weights),
            engine.parallel_stress_testing(
                real_returns, weights, n_custom_scenarios=20
            ),
            engine.parallel_backtest(real_returns, weights=weights, step_size=60),
            engine.parallel_sensitivity_analysis(real_returns, weights),
            engine.parallel_risk_decomposition(real_returns, weights, "es"),
            run_risk_analysis(returns=real_returns, seed=1),
        ]
        for output in outputs:
            assert json.dumps(to_jsonable(output), allow_nan=False)

    def test_evt_on_portfolio_returns_feeds_stress_scenarios(self, real_returns):
        series = real_returns.mean(axis=1).to_numpy()
        evt = ExtremeValueRisk(seed=1).fit_pot(series)
        scenarios = evt.simulate_extreme_scenarios(50, 0.99)
        assert (scenarios > evt.calculate_var(0.99)).all()


class TestReportingFromRiskResults:
    def test_schedule_generate_archive(self, real_returns, tmp_path):
        weights = {c: 1 / real_returns.shape[1] for c in real_returns.columns}
        engine = ParallelRiskEngine(n_jobs=1, seed=3)
        batch = engine.parallel_batch_risk_calculation(
            real_returns, weights=weights, confidence_levels=[0.95]
        )
        table = (
            pd.DataFrame(batch["risk_metrics"])
            .T.reset_index()
            .rename(columns={"index": "model"})
        )
        template = ReportTemplate("Portfolio Risk", author="Desk")
        template.add_section("Summary", "Tail risk by model", "text")
        template.add_section(
            "Metrics",
            {"data_key": "metrics", "options": {"show_index": False}},
            "table",
        )
        ReportScheduler.register_data_provider(
            "integration", lambda: {"metrics": table}
        )
        scheduler = ReportScheduler(str(tmp_path / "sched"))
        template_path = str(tmp_path / "sched" / "template.json")
        template.save(template_path)
        output = str(tmp_path / "sched" / "report.html")
        schedule_id = scheduler.add_schedule(
            "daily-risk", template_path, output, "daily", "integration"
        )
        assert scheduler.run_report(schedule_id)["success"]
        archive = ReportArchive(str(tmp_path / "archive"))
        stored = archive.archive_report(output, "risk", {"source": "integration"})
        html = archive.get_report(stored)
        assert "parametric" in html and "historical" in html and "evt" in html
        assert "Portfolio Risk" in ReportGenerator(template).render_html(
            {"metrics": table}
        )
