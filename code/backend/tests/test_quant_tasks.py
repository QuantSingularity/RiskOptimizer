import os
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from src.tasks import report_tasks, risk_tasks
from src.tasks.celery_app import TaskValidationError
from src.tasks.portfolio_tasks import (
    analyze_portfolio_performance,
    optimize_portfolio,
    rebalance_portfolio,
)
from src.tasks.quant_adapter import (
    portfolio_returns_from_records,
    returns_frame,
    safe_filename,
)
from src.tasks.report_tasks import (
    export_portfolio_data,
    generate_daily_reports,
    generate_portfolio_report,
    generate_risk_report,
)
from src.tasks.risk_tasks import (
    efficient_frontier_calculation,
    monte_carlo_simulation,
    stress_test_portfolio,
)


@pytest.fixture(autouse=True)
def isolated_output(tmp_path, monkeypatch):
    monkeypatch.setenv("QUANT_ML_ARTIFACT_DIR", str(tmp_path))
    for name in list(os.environ):
        if name.startswith("QUANT_ML_SMTP_"):
            monkeypatch.delenv(name)
    with patch("src.tasks.celery_app.task_result_manager"), patch(
        "src.tasks.risk_tasks.task_result_manager"
    ), patch("src.tasks.portfolio_tasks.task_result_manager"), patch(
        "src.tasks.report_tasks.task_result_manager"
    ):
        yield tmp_path


@pytest.fixture(scope="module")
def returns():
    rng = np.random.default_rng(21)
    common = rng.standard_t(5, 600) * 0.008
    return np.column_stack(
        [
            0.0004 + b * common + rng.normal(0, s, 600)
            for b, s in [(1.0, 0.006), (0.8, 0.009), (1.2, 0.012)]
        ]
    )


@pytest.fixture
def task_self():
    task = MagicMock()
    task.request.id = "task-1"
    return task


def portfolio(returns):
    return {
        "weights": [0.5, 0.3, 0.2],
        "historical_returns": returns.tolist(),
        "seed": 3,
    }


class TestRiskTasksUseQuantMl:
    def test_monte_carlo_reports_real_drawdowns_and_reproduces(
        self, task_self, returns
    ):
        first = monte_carlo_simulation(task_self, portfolio(returns), 2000, 60)
        second = monte_carlo_simulation(task_self, portfolio(returns), 2000, 60)
        assert (
            first["drawdown"]["worst_max_drawdown"]
            <= first["drawdown"]["mean_max_drawdown"]
            <= 0
        )
        assert first["simulation_data"] == second["simulation_data"]
        daily = (returns @ np.array([0.5, 0.3, 0.2])).mean()
        assert first["statistics"]["mean_final_value"] == pytest.approx(
            np.exp(60 * daily), rel=0.05
        )

    def test_monte_carlo_input_errors(self, task_self, returns):
        with pytest.raises(TaskValidationError):
            monte_carlo_simulation(task_self, {"weights": [1, 0]}, 100, 10)
        with pytest.raises(TaskValidationError):
            monte_carlo_simulation(
                task_self, {**portfolio(returns), "weights": [0.5, 0.5]}, 100, 10
            )
        with pytest.raises(TaskValidationError):
            monte_carlo_simulation(
                task_self, {**portfolio(returns), "copula_type": "frank"}, 100, 10
            )
        with pytest.raises(TaskValidationError):
            monte_carlo_simulation(task_self, portfolio(returns), 10**7, 10)

    def test_var_cvar_matches_the_empirical_distribution(self, task_self, returns):
        result = risk_tasks.calculate_var_cvar(task_self, portfolio(returns), [0.95])
        series = returns @ np.array([0.5, 0.3, 0.2])
        assert result["var"]["95%"] == pytest.approx(-np.quantile(series, 0.05))
        assert result["model_estimates"]["evt"]["var_95"] > 0
        assert (
            result["model_estimates"]["parametric"]["es_95"]
            >= result["model_estimates"]["parametric"]["var_95"]
        )

    def test_frontier_returns_the_requested_number_and_a_pareto_set(
        self, task_self, returns
    ):
        result = efficient_frontier_calculation(
            task_self,
            {"returns": returns.tolist(), "asset_names": ["A", "B", "C"]},
            800,
        )
        assert (
            len(result["portfolios"]["returns"])
            == 800
            == result["statistics"]["num_portfolios"]
        )
        frontier = result["efficient_frontier"]
        assert np.all(np.diff(frontier["returns"]) > 0) and np.all(
            np.diff(frontier["volatilities"]) >= 0
        )
        best = result["optimal_portfolios"]["max_sharpe"]
        assert sum(best["weights"]) == pytest.approx(1.0) and set(
            best["weights_by_asset"]
        ) == {"A", "B", "C"}
        assert best["sharpe_ratio"] == pytest.approx(
            max(result["portfolios"]["sharpe_ratios"])
        )

    def test_frontier_validation(self, task_self, returns):
        with pytest.raises(TaskValidationError):
            efficient_frontier_calculation(task_self, {"returns": returns.tolist()}, 0)
        with pytest.raises(TaskValidationError):
            efficient_frontier_calculation(
                task_self, {"returns": returns[:, :1].tolist()}, 100
            )
        with pytest.raises(TaskValidationError):
            efficient_frontier_calculation(task_self, {"nothing": 1}, 100)

    def test_stress_crash_is_a_shock_not_a_per_day_shift(self, task_self, returns):
        result = stress_test_portfolio(
            task_self, portfolio(returns), [{"type": "market_crash", "shock": -0.3}]
        )
        stressed = result["stress_results"][0]
        assert stressed["stressed_return"] == pytest.approx(
            result["baseline"]["return"] - 0.3
        )
        assert stressed["stressed_volatility"] == pytest.approx(
            result["baseline"]["volatility"]
        )

    def test_stress_unknown_scenario_is_a_validation_error(self, task_self, returns):
        with pytest.raises(TaskValidationError):
            stress_test_portfolio(
                task_self, portfolio(returns), [{"type": "alien_invasion"}]
            )


class TestPortfolioTasksUseQuantMl:
    def data(self, returns):
        return {"returns": returns.tolist(), "asset_names": ["A", "B", "C"]}

    def test_weight_bounds_are_enforced(self, task_self, returns):
        for method in (
            "mean_variance",
            "minimum_variance",
            "risk_parity",
            "black_litterman",
        ):
            result = optimize_portfolio(
                task_self,
                self.data(returns),
                {"method": method, "max_weight_per_asset": 0.4},
            )
            assert max(result["weights"].values()) <= 0.4 + 1e-6
            assert result["constraints_satisfied"]["max_weight_constraint"] is True

    def test_black_litterman_uses_the_views(self, task_self, returns):
        base = optimize_portfolio(
            task_self, self.data(returns), {"method": "black_litterman"}
        )
        view = {"assets": {"C": 1.0}, "return": 0.6, "confidence": 0.9}
        tilted = optimize_portfolio(
            task_self,
            self.data(returns),
            {"method": "black_litterman", "views": [view]},
        )
        assert tilted["weights"]["C"] > base["weights"]["C"] + 0.05
        assert set(tilted["details"]) == {
            "implied_equilibrium_returns",
            "posterior_returns",
            "market_weights",
        }

    def test_risk_parity_balances_risk(self, task_self, returns):
        result = optimize_portfolio(
            task_self, self.data(returns), {"method": "risk_parity"}
        )
        assert np.allclose(
            list(result["risk_contributions"].values()), 1 / 3, atol=0.02
        )

    def test_target_return_is_honoured_or_rejected(self, task_self, returns):
        achievable = optimize_portfolio(
            task_self, self.data(returns), {"method": "mean_variance"}
        )
        target = achievable["portfolio_metrics"]["expected_return"] * 0.9
        met = optimize_portfolio(
            task_self,
            self.data(returns),
            {"method": "mean_variance", "target_return": target},
        )
        assert met["portfolio_metrics"]["expected_return"] >= target - 1e-6
        with pytest.raises(TaskValidationError):
            optimize_portfolio(
                task_self,
                self.data(returns),
                {"method": "mean_variance", "target_return": 9.0},
            )

    def test_infeasible_bounds_are_rejected(self, task_self, returns):
        with pytest.raises(TaskValidationError):
            optimize_portfolio(
                task_self,
                self.data(returns),
                {"method": "mean_variance", "max_weight_per_asset": 0.2},
            )
        with pytest.raises(TaskValidationError):
            optimize_portfolio(
                task_self,
                {**self.data(returns), "asset_names": ["A"]},
                {"method": "mean_variance"},
            )

    def test_rebalance_reports_residual_tracking_error_for_skipped_trades(
        self, task_self
    ):
        plan = rebalance_portfolio(
            task_self,
            {"holdings": {"A": 5050, "B": 4950}},
            {"A": 0.5, "B": 0.5},
            {"min_transaction_size": 100, "transaction_cost_rate": 0.001},
        )
        analysis = plan["rebalancing_analysis"]
        assert plan["transactions"] == {} and analysis[
            "tracking_error_after"
        ] == pytest.approx(analysis["tracking_error_before"])
        assert analysis["tracking_error_after"] > 0

    def test_rebalance_removes_drift_when_trades_execute(self, task_self):
        plan = rebalance_portfolio(
            task_self,
            {"holdings": {"A": 8000, "B": 2000}},
            {"A": 0.5, "B": 0.5},
            {"min_transaction_size": 100},
        )
        analysis = plan["rebalancing_analysis"]
        assert analysis["tracking_error_after"] == pytest.approx(
            0.0, abs=1e-12
        ) and analysis["turnover_rate"] == pytest.approx(0.6)

    @pytest.mark.parametrize(
        "holdings,targets",
        [
            ({"A": -5, "B": 10}, {"A": 0.5, "B": 0.5}),
            ({"A": 0, "B": 0}, {"A": 0.5, "B": 0.5}),
            ({"A": 100, "B": 100}, {"A": 0.7, "B": 0.7}),
            ({}, {"A": 1.0}),
        ],
    )
    def test_rebalance_validation(self, task_self, holdings, targets):
        with pytest.raises(TaskValidationError):
            rebalance_portfolio(task_self, {"holdings": holdings}, targets, {})

    def test_performance_analysis_is_computed_from_the_series(self, task_self, returns):
        port = returns @ np.array([0.5, 0.3, 0.2])
        result = analyze_portfolio_performance(
            task_self,
            {"returns": port.tolist()},
            {"returns": returns[:, 0].tolist()},
            {"risk_free_rate": 0.0},
        )
        assert result["performance_summary"]["total_return"] == pytest.approx(
            np.prod(1 + port) - 1
        )
        assert result["metadata"]["number_of_observations"] == 600
        assert result["benchmark_comparison"]["beta"] > 0

    def test_performance_analysis_requires_returns(self, task_self):
        with pytest.raises(TaskValidationError):
            analyze_portfolio_performance(task_self, {}, {"returns": [0.1] * 10}, {})


class TestAdapter:
    def test_portfolio_returns_from_records(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="B")
        prices = {
            "A": list(zip(dates, np.linspace(100, 130, 60))),
            "B": list(zip(dates, np.linspace(50, 40, 60))),
        }
        series = portfolio_returns_from_records([("A", 60.0), ("B", 40.0)], prices)
        expected = np.column_stack(
            [
                np.diff(np.linspace(100, 130, 60)) / np.linspace(100, 130, 60)[:-1],
                np.diff(np.linspace(50, 40, 60)) / np.linspace(50, 40, 60)[:-1],
            ]
        ) @ np.array([0.6, 0.4])
        assert np.allclose(series.to_numpy(), expected)

    def test_missing_or_short_data_is_a_validation_error(self):
        dates = pd.date_range("2024-01-01", periods=10, freq="B")
        short = {"A": list(zip(dates, np.linspace(1, 2, 10)))}
        with pytest.raises(TaskValidationError):
            portfolio_returns_from_records([("A", 100.0)], short)
        with pytest.raises(TaskValidationError):
            portfolio_returns_from_records([("A", 100.0)], {})
        with pytest.raises(TaskValidationError):
            portfolio_returns_from_records([], short)

    def test_returns_frame_rules(self):
        with pytest.raises(TaskValidationError):
            returns_frame({}, "returns")
        with pytest.raises(TaskValidationError):
            returns_frame(
                {"returns": np.zeros((40, 2)).tolist(), "asset_names": ["only"]},
                "returns",
            )

    @pytest.mark.parametrize(
        "name,expected",
        [
            ("../../etc/passwd", "etc_passwd"),
            ("A B/C", "A_B_C"),
            ("", "report"),
            ("<b>x</b>", "b_x_b"),
        ],
    )
    def test_safe_filename(self, name, expected):
        assert safe_filename(name) == expected


class TestReportTasks:
    def report_data(self, name="Growth Fund"):
        return {
            "portfolio_name": name,
            "holdings": {"AAPL": 5000, "MSFT": 3000, "BTC": 2000},
            "performance_data": {
                "total_return": 0.12,
                "annualized_return": 0.1,
                "volatility": 0.2,
                "sharpe_ratio": 0.8,
                "max_drawdown": -0.15,
            },
            "risk_metrics": {
                "var_95": 0.03,
                "var_99": 0.05,
                "cvar_95": 0.04,
                "cvar_99": 0.06,
            },
        }

    def test_pdf_report_is_written_inside_the_managed_directory(
        self, task_self, isolated_output
    ):
        pypdf = pytest.importorskip("pypdf")
        result = generate_portfolio_report(
            task_self, self.report_data(), {"format": "pdf"}
        )
        path = result["report_path"]
        assert (
            path.startswith(str(isolated_output))
            and path.endswith(".pdf")
            and result["file_size_bytes"] > 1000
        )
        text = "\n".join(page.extract_text() for page in pypdf.PdfReader(path).pages)
        for expected in (
            "Portfolio Analysis Report",
            "Growth Fund",
            "AAPL",
            "50.00%",
            "Sharpe Ratio",
            "VaR (95%)",
        ):
            assert expected in text

    def test_html_report_escapes_hostile_names_and_cannot_traverse(
        self, task_self, isolated_output
    ):
        hostile = "../../tmp/<script>alert(1)</script>"
        result = generate_portfolio_report(
            task_self, self.report_data(hostile), {"format": "html"}
        )
        assert os.path.dirname(result["report_path"]).startswith(str(isolated_output))
        assert ".." not in os.path.basename(result["report_path"])
        html = open(result["report_path"], encoding="utf-8").read()
        assert "<script>alert(1)</script>" not in html and "&lt;script&gt;" in html

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda d: d.pop("holdings"),
            lambda d: d.update(holdings={}),
            lambda d: d.update(holdings={"A": -1}),
            lambda d: d.update(holdings={"A": 0}),
        ],
    )
    def test_portfolio_report_validation(self, task_self, mutate):
        data = self.report_data()
        mutate(data)
        with pytest.raises(TaskValidationError):
            generate_portfolio_report(task_self, data, {})

    def test_unsupported_format(self, task_self):
        with pytest.raises(TaskValidationError):
            generate_portfolio_report(task_self, self.report_data(), {"format": "docx"})

    def test_email_delivery_uses_the_configured_transport(self, task_self):
        sent = []
        fake = MagicMock(
            side_effect=lambda path, recipients: sent.append((path, list(recipients)))
            or True
        )
        with patch(
            "src.tasks.report_tasks.EmailDelivery.from_environment", return_value=fake
        ):
            result = generate_portfolio_report(
                task_self,
                self.report_data(),
                {"format": "pdf", "recipients": ["ops@example.com"]},
            )
        assert result["delivery"] == {"delivered": True, "error": None}
        assert sent[0][1] == ["ops@example.com"] and sent[0][0] == result["report_path"]

    def test_delivery_without_smtp_is_reported_honestly(self, task_self):
        result = generate_portfolio_report(
            task_self,
            self.report_data(),
            {"format": "html", "recipients": ["ops@example.com"]},
        )
        assert (
            result["delivery"]["delivered"] is False
            and "No delivery handler" in result["delivery"]["error"]
        )

    def test_invalid_recipients_are_rejected_before_sending(self, task_self):
        with pytest.raises(TaskValidationError):
            generate_portfolio_report(
                task_self, self.report_data(), {"recipients": ["not-an-address"]}
            )

    def test_risk_report_sections(self, task_self):
        pypdf = pytest.importorskip("pypdf")
        mc = {
            "num_simulations": 5000,
            "time_horizon": 252,
            "var_95": 0.2,
            "var_99": 0.3,
            "cvar_95": 0.25,
            "cvar_99": 0.35,
            "probability_of_loss": 0.4,
        }
        stress = {
            "stress_results": [
                {
                    "scenario": {"type": "market_crash"},
                    "return_impact": -0.3,
                    "volatility_impact": 0.0,
                    "stressed_var_95": 0.35,
                }
            ]
        }
        result = generate_risk_report(
            task_self,
            {"monte_carlo_results": mc, "stress_test_results": stress},
            {"format": "pdf"},
        )
        text = "\n".join(
            page.extract_text() for page in pypdf.PdfReader(result["report_path"]).pages
        )
        for expected in (
            "Monte Carlo Simulation Results",
            "5,000",
            "Stress Test Results",
            "market_crash",
            "-30.00%",
        ):
            assert expected in text

    def test_risk_report_needs_content(self, task_self):
        with pytest.raises(TaskValidationError):
            generate_risk_report(task_self, {}, {})

    def test_exports(self, task_self):
        data = self.report_data()
        data["historical_returns"] = [[0.01, 0.02], [0.0, -0.01]]
        excel = export_portfolio_data(task_self, data, {"format": "excel"})
        sheets = pd.ExcelFile(excel["export_path"]).sheet_names
        assert {"Holdings", "Performance", "Risk_Metrics", "Historical_Returns"} <= set(
            sheets
        )
        csv = export_portfolio_data(task_self, data, {"format": "csv"})
        frame = pd.read_csv(csv["export_path"])
        assert frame["Weight"].sum() == pytest.approx(1.0)

    def test_export_validation(self, task_self):
        with pytest.raises(TaskValidationError):
            export_portfolio_data(task_self, {"holdings": {"A": 0}}, {})
        with pytest.raises(TaskValidationError):
            export_portfolio_data(task_self, self.report_data(), {"format": "xml"})
        result = export_portfolio_data(
            task_self, self.report_data("../../evil"), {"format": "csv"}
        )
        assert "/" not in result["export_filename"]


class TestDailyReports:
    def run(self, portfolios, returns_by_id, **env):
        def loader(portfolio_id):
            value = returns_by_id[portfolio_id]
            if isinstance(value, Exception):
                raise value
            return pd.Series(value)

        with patch.object(
            report_tasks, "list_portfolios", return_value=portfolios
        ), patch.object(report_tasks, "load_portfolio_returns", side_effect=loader):
            return generate_daily_reports.run()

    def test_reports_are_generated_from_stored_data_not_fabricated(
        self, returns, isolated_output
    ):
        series = returns @ np.array([0.5, 0.3, 0.2])
        outcome = self.run(
            [{"id": 1, "name": "Alpha", "owner_email": "a@example.com"}], {1: series}
        )
        assert outcome["portfolios_processed"] == 1 and outcome["generated"] == 1
        entry = outcome["reports"][0]
        assert (
            entry["status"] == "generated"
            and os.path.exists(entry["report_path"])
            and os.path.exists(entry["archived_path"])
        )
        assert entry["report_path"].startswith(str(isolated_output))
        assert "emailed" not in entry

    def test_problem_portfolios_are_reported_individually(self, returns):
        series = returns @ np.array([0.5, 0.3, 0.2])
        outcome = self.run(
            [
                {"id": 1, "name": "Good"},
                {"id": 2, "name": "Empty"},
                {"id": 3, "name": "Broken"},
            ],
            {
                1: series,
                2: TaskValidationError("Portfolio 2 has no allocations"),
                3: RuntimeError("db down"),
            },
        )
        statuses = {e["portfolio_id"]: e["status"] for e in outcome["reports"]}
        assert statuses == {1: "generated", 2: "skipped", 3: "failed"}
        assert (outcome["generated"], outcome["skipped"], outcome["failed"]) == (
            1,
            1,
            1,
        )

    def test_no_portfolios(self):
        assert self.run([], {})["portfolios_processed"] == 0

    def test_owner_emails_only_when_explicitly_enabled(self, returns, monkeypatch):
        series = returns @ np.array([0.5, 0.3, 0.2])
        fake = MagicMock(return_value=True)
        portfolios = [{"id": 1, "name": "Alpha", "owner_email": "owner@example.com"}]
        with patch(
            "src.tasks.report_tasks.EmailDelivery.from_environment", return_value=fake
        ):
            assert "emailed" not in self.run(portfolios, {1: series})["reports"][0]
            monkeypatch.setenv("DAILY_REPORTS_EMAIL_OWNERS", "true")
            entry = self.run(portfolios, {1: series})["reports"][0]
        assert entry["emailed"] is True and fake.call_args.args[1] == [
            "owner@example.com"
        ]

    def test_email_failure_is_recorded_without_failing_the_report(
        self, returns, monkeypatch
    ):
        monkeypatch.setenv("DAILY_REPORTS_EMAIL_OWNERS", "true")
        fake = MagicMock(side_effect=OSError("smtp down"))
        series = returns @ np.array([0.5, 0.3, 0.2])
        with patch(
            "src.tasks.report_tasks.EmailDelivery.from_environment", return_value=fake
        ):
            entry = self.run(
                [{"id": 1, "name": "Alpha", "owner_email": "o@example.com"}],
                {1: series},
            )["reports"][0]
        assert (
            entry["status"] == "generated"
            and entry["emailed"] is False
            and "smtp down" in entry["email_error"]
        )
