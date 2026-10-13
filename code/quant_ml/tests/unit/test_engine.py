import numpy as np
import pandas as pd
import pytest
from risk.copula import CopulaMLRiskModel
from risk.engine import ParallelRiskEngine, infer_asset_class, kupiec_pvalue


@pytest.fixture(scope="module")
def engine():
    return ParallelRiskEngine(n_jobs=2, seed=5)


@pytest.fixture(scope="module")
def weights():
    return {"A0": 0.5, "A1": 0.3, "A2": 0.2}


class TestConstruction:
    @pytest.mark.parametrize(
        "kwargs",
        [{"n_jobs": 0}, {"n_jobs": True}, {"n_jobs": "2"}, {"backend": "bogus"}],
    )
    def test_invalid(self, kwargs):
        with pytest.raises(ValueError):
            ParallelRiskEngine(**kwargs)

    def test_defaults(self):
        import multiprocessing as mp

        assert ParallelRiskEngine().n_jobs == mp.cpu_count()
        assert ParallelRiskEngine(n_jobs=-1).n_jobs == mp.cpu_count()

    def test_system_info(self, engine):
        assert {"cpu_count", "backend", "n_jobs"} <= set(engine.system_info())


class TestMonteCarlo:
    def test_reproducible_and_complete(self, engine, returns_frame, weights):
        model = CopulaMLRiskModel("gaussian", 1000, seed=1).fit(returns_frame)
        first = engine.parallel_monte_carlo(model, weights, 5003)
        second = engine.parallel_monte_carlo(model, weights, 5003)
        assert first["n_scenarios"] == 5003
        assert first["risk_metrics"] == second["risk_metrics"]
        assert first["risk_metrics"]["var_99"] > first["risk_metrics"]["var_95"] > 0

    def test_batches_use_distinct_random_streams(self, engine, returns_frame):
        model = CopulaMLRiskModel("gaussian", 1000, seed=1).fit(returns_frame)
        sizes = engine.batches(2000)
        assert sum(sizes) == 2000 and len(sizes) > 1
        seeds = __import__("risk.common", fromlist=["spawn_seeds"]).spawn_seeds(
            5, len(sizes)
        )
        frames = [
            model.generate_scenarios(size, seed=s)
            for size, s in zip(sizes, seeds, strict=False)
        ]
        assert not np.allclose(frames[0].to_numpy()[:5], frames[1].to_numpy()[:5])

    @pytest.mark.parametrize("count", [0, -1, True, 10**9])
    def test_invalid_counts(self, engine, returns_frame, weights, count):
        model = CopulaMLRiskModel(seed=1).fit(returns_frame)
        with pytest.raises(ValueError):
            engine.parallel_monte_carlo(model, weights, count)


class TestOptimization:
    @pytest.mark.parametrize("model", ["markowitz", "cvar", "mad"])
    def test_models(self, engine, returns_frame, model):
        result = engine.parallel_portfolio_optimization(returns_frame, model, 600)
        table = result["all_portfolios"]
        assert result["n_portfolios"] == len(table) == 600
        assert np.allclose(table[["A0", "A1", "A2"]].sum(axis=1), 1.0)
        assert (table[["A0", "A1", "A2"]] >= 0).all().all()

    def test_frontier_is_pareto_efficient(self, engine, returns_frame):
        result = engine.parallel_portfolio_optimization(
            returns_frame, "markowitz", 2000
        )
        frontier = result["efficient_frontier"]
        assert (frontier["return"].diff().dropna() > 0).all()
        assert (frontier["volatility"].diff().dropna() >= 0).all()
        table = result["all_portfolios"]
        for _, row in frontier.iterrows():
            dominated = table[
                (table["return"] > row["return"] + 1e-12)
                & (table["volatility"] < row["volatility"] - 1e-12)
            ]
            assert dominated.empty

    def test_special_portfolios(self, engine, returns_frame):
        result = engine.parallel_portfolio_optimization(
            returns_frame, "markowitz", 1000, target_return=0.1, target_risk=0.1
        )
        table = result["all_portfolios"]
        assert result["max_sharpe_portfolio"]["sharpe_ratio"] == pytest.approx(
            table["sharpe_ratio"].max()
        )
        assert result["min_volatility_portfolio"]["volatility"] == pytest.approx(
            table["volatility"].min()
        )
        assert set(result["target_portfolios"]) == {"target_return", "target_risk"}

    def test_seed_reproducible(self, returns_frame):
        a = ParallelRiskEngine(n_jobs=2, seed=9).parallel_portfolio_optimization(
            returns_frame, "markowitz", 300
        )
        b = ParallelRiskEngine(n_jobs=2, seed=9).parallel_portfolio_optimization(
            returns_frame, "markowitz", 300
        )
        assert a["all_portfolios"].equals(b["all_portfolios"])

    def test_validation(self, engine, returns_frame):
        with pytest.raises(ValueError):
            engine.parallel_portfolio_optimization(returns_frame, "bogus", 100)
        with pytest.raises(ValueError):
            engine.parallel_portfolio_optimization(
                returns_frame.iloc[:, :1], "markowitz", 100
            )


class TestBatchRisk:
    def test_uses_portfolio_not_pooled_assets(self, engine, returns_frame, weights):
        result = engine.parallel_batch_risk_calculation(
            returns_frame, ["historical"], [0.95], weights
        )
        series = returns_frame.to_numpy() @ np.array([0.5, 0.3, 0.2])
        assert result["risk_metrics"]["historical"]["var_95"] == pytest.approx(
            -np.quantile(series, 0.05)
        )

    def test_evt_differs_from_historical(self, engine, returns_frame):
        metrics = engine.parallel_batch_risk_calculation(
            returns_frame, ["historical", "evt"], [0.99]
        )["risk_metrics"]
        assert metrics["evt"]["var_99"] != metrics["historical"]["var_99"]

    def test_parametric_formula(self, engine, returns_frame):
        from scipy import stats

        series = returns_frame.mean(axis=1).to_numpy()
        expected = -series.mean() + stats.norm.ppf(0.95) * series.std()
        metrics = engine.parallel_batch_risk_calculation(
            returns_frame, ["parametric"], [0.95]
        )["risk_metrics"]
        assert metrics["parametric"]["var_95"] == pytest.approx(expected)

    def test_unknown_model_rejected(self, engine, returns_frame):
        with pytest.raises(ValueError):
            engine.parallel_batch_risk_calculation(returns_frame, ["garch"])


class TestStress:
    def test_asset_class_inference(self):
        assert infer_asset_class("BTC_USD") == "crypto"
        assert infer_asset_class("eth-usd") == "crypto"
        assert infer_asset_class("AAPL") == "equity"

    def test_class_shocks_apply_to_matching_assets(self, engine):
        rng = np.random.default_rng(0)
        frame = pd.DataFrame(
            rng.normal(0, 0.01, (300, 3)), columns=["AAPL", "BTC_USD", "MSFT"]
        )
        result = engine.parallel_stress_testing(
            frame, [0.4, 0.4, 0.2], n_custom_scenarios=20
        )
        crash = result["predefined_scenarios"]["crypto_crash"]
        assert crash["assets_affected"] == ["BTC_USD"]
        assert crash["portfolio_return"] == pytest.approx(-0.30 * 0.4)
        assert result["predefined_scenarios"]["market_crash"][
            "portfolio_return"
        ] == pytest.approx(-0.15)

    def test_unmatched_scenario_is_flagged(self, engine, returns_frame, weights):
        scenarios = {"bonds": {"description": "x", "shocks": {"bonds": -0.05}}}
        result = engine.parallel_stress_testing(returns_frame, weights, scenarios, 10)
        assert result["predefined_scenarios"]["bonds"]["applied"] is False

    def test_explicit_asset_shock_and_class_override(
        self, engine, returns_frame, weights
    ):
        scenarios = {"hit": {"description": "x", "shocks": {"A0": -0.2}}}
        result = engine.parallel_stress_testing(
            returns_frame, weights, scenarios, 10, asset_classes={"A1": "bonds"}
        )
        assert result["predefined_scenarios"]["hit"][
            "portfolio_return"
        ] == pytest.approx(-0.1)

    def test_custom_scenarios_reproducible(self, returns_frame, weights):
        a = ParallelRiskEngine(n_jobs=1, seed=3).parallel_stress_testing(
            returns_frame, weights, n_custom_scenarios=50
        )
        b = ParallelRiskEngine(n_jobs=1, seed=3).parallel_stress_testing(
            returns_frame, weights, n_custom_scenarios=50
        )
        assert a["custom_scenarios_summary"] == b["custom_scenarios_summary"]
        assert (
            a["custom_scenarios_summary"]["min_return"]
            <= a["custom_scenarios_summary"]["max_return"]
        )

    def test_invalid_counts(self, engine, returns_frame, weights):
        with pytest.raises(ValueError):
            engine.parallel_stress_testing(returns_frame, weights, n_custom_scenarios=0)


class TestBacktest:
    def test_counts_every_out_of_sample_day(self, engine, returns_frame, weights):
        result = engine.parallel_backtest(
            returns_frame,
            ["historical"],
            0.95,
            window_size=252,
            step_size=20,
            weights=weights,
        )
        total = result["summary"]["historical"]["total"]
        assert total == len(returns_frame) - 252
        assert sum(w["n_test"] for w in result["windows"]) == total

    def test_breach_rates_are_calibrated(self, engine, real_returns):
        result = engine.parallel_backtest(real_returns, ["historical", "evt"], 0.95)
        for stats_ in result["summary"].values():
            assert 0.025 < stats_["breach_rate"] < 0.09
            assert 0.0 <= stats_["kupiec_pvalue"] <= 1.0

    def test_kupiec(self):
        assert kupiec_pvalue(50, 1000, 0.05) == pytest.approx(1.0, abs=1e-9)
        assert kupiec_pvalue(100, 1000, 0.05) < 0.001
        assert 0 <= kupiec_pvalue(0, 1000, 0.05) < 0.001
        assert np.isnan(kupiec_pvalue(0, 0, 0.05))

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"window_size": 10},
            {"window_size": 5000},
            {"step_size": 0},
            {"confidence_level": 1.2},
        ],
    )
    def test_validation(self, engine, returns_frame, kwargs):
        with pytest.raises(ValueError):
            engine.parallel_backtest(returns_frame, **kwargs)


class TestSensitivityAndDecomposition:
    def test_sensitivity(self, engine, returns_frame, weights):
        result = engine.parallel_sensitivity_analysis(
            returns_frame, weights, (-0.1, 0.1), 5
        )
        factor = result["factor_results"]["A0"]
        assert len(factor["shocks"]) == 5
        assert result["sensitivities"]["A0"]["return_sensitivity"] == pytest.approx(0.5)
        assert np.ptp(factor["portfolio_volatilities"]) < 1e-12
        assert result["sensitivities"]["A2"]["return_sensitivity"] == pytest.approx(0.2)

    def test_sensitivity_validation(self, engine, returns_frame, weights):
        with pytest.raises(ValueError):
            engine.parallel_sensitivity_analysis(returns_frame, weights, n_points=1)

    @pytest.mark.parametrize("measure", ["volatility", "var", "es"])
    def test_decomposition_is_additive(self, engine, returns_frame, weights, measure):
        result = engine.parallel_risk_decomposition(returns_frame, weights, measure)
        assert sum(result["component_contributions"]) == pytest.approx(
            result["portfolio_risk"], rel=1e-6
        )
        assert sum(result["percentage_contributions"]) == pytest.approx(1.0, rel=1e-6)

    def test_volatility_matches_closed_form(self, engine, returns_frame, weights):
        vector = np.array([0.5, 0.3, 0.2])
        expected = np.sqrt(
            vector @ np.cov(returns_frame.to_numpy(), rowvar=False) @ vector
        )
        assert engine.parallel_risk_decomposition(returns_frame, weights)[
            "portfolio_risk"
        ] == pytest.approx(expected)

    def test_largest_weight_dominates_for_equal_assets(
        self, engine, returns_frame, weights
    ):
        result = engine.parallel_risk_decomposition(returns_frame, weights, "es")
        assert (
            result["contributions"][0]["percentage_contribution"]
            >= result["contributions"][-1]["percentage_contribution"]
        )

    def test_unsupported_measure(self, engine, returns_frame, weights):
        with pytest.raises(ValueError):
            engine.parallel_risk_decomposition(returns_frame, weights, "beta")
