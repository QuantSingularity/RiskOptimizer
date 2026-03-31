"""
Test suite for RiskOptimizer enhancements

This module provides comprehensive tests for the new features and enhancements:
1. Extreme Value Theory risk models
2. Machine Learning risk models
3. Parallel risk calculation engine
4. Flexible reporting framework
5. Customizable dashboards
"""

import logging
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from typing import Any

import numpy as np
import pandas as pd
from frontend.dashboard.dashboard_framework import ChartComponent, Dashboard
from reporting.reporting_framework import ReportGenerator, ReportTemplate
from risk_engine.parallel_risk_engine import ParallelRiskEngine
from risk_models.extreme_value_theory import ExtremeValueRisk
from risk_models.ml_risk_models import CopulaMLRiskModel, MLRiskModel

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestExtremeValueTheory(unittest.TestCase):
    """Test cases for Extreme Value Theory module"""

    def setUp(self) -> Any:
        """Set up test data"""
        np.random.seed(42)
        n_samples = 1000
        self.returns = np.random.standard_t(3, n_samples) * 0.02 + 0.001
        self.evt_model = ExtremeValueRisk()

    def test_pot_fitting(self) -> Any:
        """Test Peaks Over Threshold fitting"""
        self.evt_model.fit_pot(self.returns, threshold_quantile=0.1)
        self.assertIsNotNone(self.evt_model.pot_params)
        self.assertIn("shape", self.evt_model.pot_params)
        self.assertIn("scale", self.evt_model.pot_params)
        self.assertIn("threshold", self.evt_model.pot_params)

    def test_block_maxima(self) -> Any:
        """Test Block Maxima method"""
        self.evt_model.fit_block_maxima(self.returns, block_size=20)
        self.assertIsNotNone(self.evt_model.bm_params)
        self.assertIn("shape", self.evt_model.bm_params)
        self.assertIn("loc", self.evt_model.bm_params)
        self.assertIn("scale", self.evt_model.bm_params)

    def test_var_calculation(self) -> Any:
        """Test Value at Risk calculation"""
        self.evt_model.fit_pot(self.returns, threshold_quantile=0.1)
        var_95 = self.evt_model.calculate_var(0.95)
        var_99 = self.evt_model.calculate_var(0.99)
        self.assertGreater(var_95, 0)
        self.assertGreater(var_99, var_95)
        hist_var_95 = self.evt_model.calculate_var(0.95, method="historical")
        self.assertIsNotNone(hist_var_95)

    def test_es_calculation(self) -> Any:
        """Test Expected Shortfall calculation"""
        self.evt_model.fit_pot(self.returns, threshold_quantile=0.1)
        es_95 = self.evt_model.calculate_es(0.95)
        es_99 = self.evt_model.calculate_es(0.99)
        self.assertGreater(es_95, 0)
        self.assertGreater(es_99, es_95)
        var_95 = self.evt_model.calculate_var(0.95)
        self.assertGreater(es_95, var_95)

    def test_stress_scenarios(self) -> Any:
        """Test extreme scenario generation"""
        self.evt_model.fit_pot(self.returns, threshold_quantile=0.1)
        scenarios = self.evt_model.generate_scenarios(n_scenarios=100)
        self.assertEqual(len(scenarios), 100)
        self.assertGreater(np.min(scenarios), np.min(self.returns))

    def test_tail_dependence(self) -> Any:
        """Test tail dependence calculation"""
        np.random.seed(42)
        n_samples = 1000
        mean = [0, 0]
        cov = [[1, 0.7], [0.7, 1]]
        data = np.random.multivariate_normal(mean, cov, n_samples)
        df = 3
        t_data = data * np.sqrt(df / np.random.chisquare(df, size=(n_samples, 1)))
        tail_dep = self.evt_model.calculate_tail_dependence(t_data[:, 0], t_data[:, 1])
        self.assertGreaterEqual(tail_dep, 0)
        self.assertLessEqual(tail_dep, 1)


class TestMLRiskModels(unittest.TestCase):
    """Test cases for Machine Learning Risk Models module"""

    def setUp(self) -> Any:
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        self.returns = pd.DataFrame(
            {
                "Asset_1": np.random.normal(0.001, 0.02, n_samples),
                "Asset_2": np.random.normal(0.0005, 0.015, n_samples),
                "Asset_3": np.random.normal(0.0008, 0.025, n_samples),
            }
        )
        self.returns.index = pd.date_range(
            start="2020-01-01", periods=n_samples, freq="B"
        )
        self.weights = {"Asset_1": 0.4, "Asset_2": 0.3, "Asset_3": 0.3}

    def test_ml_model_training(self) -> Any:
        """Test ML model training"""
        ml_model = MLRiskModel(model_type="gbm")
        ml_model.fit(self.returns, feature_window=10, horizon=1)
        self.assertTrue(ml_model.trained)
        self.assertIsNotNone(ml_model.model)

    def test_ml_var_prediction(self) -> Any:
        """Test ML VaR prediction"""
        ml_model = MLRiskModel(model_type="gbm")
        ml_model.fit(self.returns, feature_window=10, horizon=1)
        var_pred = ml_model.predict_var(self.returns, confidence=0.95)
        self.assertEqual(len(var_pred), len(self.returns) - 10)
        self.assertTrue(np.all(var_pred > 0))

    def test_ml_es_prediction(self) -> Any:
        """Test ML ES prediction"""
        ml_model = MLRiskModel(model_type="gbm")
        ml_model.fit(self.returns, feature_window=10, horizon=1)
        es_pred = ml_model.predict_es(self.returns, confidence=0.95)
        self.assertEqual(len(es_pred), len(self.returns) - 10)
        self.assertTrue(np.all(es_pred > 0))
        var_pred = ml_model.predict_var(self.returns, confidence=0.95)
        self.assertTrue(np.all(es_pred >= var_pred))

    def test_ml_model_save_load(self) -> Any:
        """Test ML model saving and loading"""
        with tempfile.TemporaryDirectory() as temp_dir:
            ml_model = MLRiskModel(model_type="gbm")
            ml_model.fit(self.returns, feature_window=10, horizon=1)
            model_path = os.path.join(temp_dir, "ml_model.joblib")
            ml_model.save_model(model_path)
            self.assertTrue(os.path.exists(model_path))
            loaded_model = MLRiskModel.load_model(model_path)
            self.assertTrue(loaded_model.trained)
            self.assertEqual(loaded_model.model_type, ml_model.model_type)
            self.assertEqual(loaded_model.quantile, ml_model.quantile)

    def test_copula_fitting(self) -> Any:
        """Test copula model fitting"""
        copula_model = CopulaMLRiskModel(copula_type="gaussian")
        copula_model.fit(self.returns)
        self.assertTrue(copula_model.trained)
        self.assertIsNotNone(copula_model.correlation_matrix)
        self.assertEqual(len(copula_model.asset_names), 3)

    def test_copula_var_calculation(self) -> Any:
        """Test VaR calculation with copula model"""
        copula_model = CopulaMLRiskModel(copula_type="gaussian")
        copula_model.fit(self.returns)
        var_95 = copula_model.calculate_var(self.weights, confidence=0.95)
        var_99 = copula_model.calculate_var(self.weights, confidence=0.99)
        self.assertGreater(var_95, 0)
        self.assertGreater(var_99, var_95)

    def test_copula_es_calculation(self) -> Any:
        """Test ES calculation with copula model"""
        copula_model = CopulaMLRiskModel(copula_type="gaussian")
        copula_model.fit(self.returns)
        es_95 = copula_model.calculate_es(self.weights, confidence=0.95)
        es_99 = copula_model.calculate_es(self.weights, confidence=0.99)
        self.assertGreater(es_95, 0)
        self.assertGreater(es_99, es_95)
        var_95 = copula_model.calculate_var(self.weights, confidence=0.95)
        self.assertGreater(es_95, var_95)

    def test_copula_risk_metrics(self) -> Any:
        """Test risk metrics calculation with copula model"""
        copula_model = CopulaMLRiskModel(copula_type="gaussian")
        copula_model.fit(self.returns)
        metrics = copula_model.calculate_risk_metrics(self.weights)
        self.assertIn("var_95", metrics)
        self.assertIn("es_95", metrics)
        self.assertIn("var_99", metrics)
        self.assertIn("es_99", metrics)
        self.assertIn("mean", metrics)
        self.assertIn("std", metrics)
        self.assertGreater(metrics["var_99"], metrics["var_95"])
        self.assertGreater(metrics["es_99"], metrics["es_95"])
        self.assertGreater(metrics["es_95"], metrics["var_95"])
        self.assertGreater(metrics["es_99"], metrics["var_99"])

    def test_hybrid_model(self) -> Any:
        """Test hybrid risk model"""
        hybrid_model = HybridRiskModel(traditional_weight=0.7)
        hybrid_model.fit(self.returns)
        self.assertTrue(hybrid_model.trained)
        self.assertTrue(hybrid_model.ml_model.trained)
        self.assertTrue(hybrid_model.copula_model.trained)
        var = hybrid_model.calculate_var(self.returns, self.weights, confidence=0.95)
        es = hybrid_model.calculate_es(self.returns, self.weights, confidence=0.95)
        self.assertGreater(var, 0)
        self.assertGreater(es, var)


class TestParallelRiskEngine(unittest.TestCase):
    """Test cases for Parallel Risk Engine module"""

    def setUp(self) -> Any:
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        self.returns = pd.DataFrame(
            {
                "Asset_1": np.random.normal(0.001, 0.02, n_samples),
                "Asset_2": np.random.normal(0.0005, 0.015, n_samples),
                "Asset_3": np.random.normal(0.0008, 0.025, n_samples),
            }
        )
        self.returns.index = pd.date_range(
            start="2020-01-01", periods=n_samples, freq="B"
        )
        self.weights = {"Asset_1": 0.4, "Asset_2": 0.3, "Asset_3": 0.3}
        self.engine = ParallelRiskEngine(n_jobs=1, backend="threading")

    def test_parallel_monte_carlo(self) -> Any:
        """Test parallel Monte Carlo simulation"""
        copula_model = CopulaMLRiskModel(copula_type="gaussian")
        copula_model.fit(self.returns)
        result = self.engine.parallel_monte_carlo(
            copula_model, self.weights, n_scenarios=1000
        )
        self.assertIn("portfolio_metrics", result)
        self.assertIn("risk_metrics", result)
        self.assertIn("time_taken", result)
        self.assertIn("var_95", result["risk_metrics"])
        self.assertIn("es_95", result["risk_metrics"])
        self.assertGreater(result["risk_metrics"]["var_95"], 0)
        self.assertGreater(
            result["risk_metrics"]["es_95"], result["risk_metrics"]["var_95"]
        )

    def test_parallel_portfolio_optimization(self) -> Any:
        """Test parallel portfolio optimization"""
        result = self.engine.parallel_portfolio_optimization(
            self.returns, risk_model="markowitz", n_portfolios=100
        )
        self.assertIsNotNone(result)
        self.assertIn("efficient_frontier", result)
        self.assertIn("max_sharpe_portfolio", result)
        self.assertIn("min_volatility_portfolio", result)
        max_sharpe = result["max_sharpe_portfolio"]
        self.assertIn("weights", max_sharpe)
        self.assertIn("return", max_sharpe)
        self.assertIn("volatility", max_sharpe)
        self.assertIn("sharpe_ratio", max_sharpe)
        min_vol = result["min_volatility_portfolio"]
        self.assertIn("weights", min_vol)
        self.assertIn("return", min_vol)
        self.assertIn("volatility", min_vol)
        self.assertIn("sharpe_ratio", min_vol)

    def test_parallel_batch_risk_calculation(self) -> Any:
        """Test parallel batch risk calculation"""
        result = self.engine.parallel_batch_risk_calculation(
            self.returns.mean(axis=1),
            risk_models=["parametric", "historical"],
            confidence_levels=[0.95, 0.99],
        )
        self.assertIn("risk_metrics", result)
        self.assertIn("time_taken", result)
        for model in ["parametric", "historical"]:
            self.assertIn(model, result["risk_metrics"])
            self.assertIn("var_95", result["risk_metrics"][model])
            self.assertIn("var_99", result["risk_metrics"][model])
            self.assertIn("es_95", result["risk_metrics"][model])
            self.assertIn("es_99", result["risk_metrics"][model])
            self.assertGreaterEqual(
                result["risk_metrics"][model]["var_99"],
                result["risk_metrics"][model]["var_95"],
            )
            self.assertGreaterEqual(
                result["risk_metrics"][model]["es_99"],
                result["risk_metrics"][model]["es_95"],
            )
            self.assertGreaterEqual(
                result["risk_metrics"][model]["es_95"],
                result["risk_metrics"][model]["var_95"],
            )
            self.assertGreaterEqual(
                result["risk_metrics"][model]["es_99"],
                result["risk_metrics"][model]["var_99"],
            )

    def test_parallel_stress_testing(self) -> Any:
        """Test parallel stress testing"""
        result = self.engine.parallel_stress_testing(
            self.returns, self.weights, n_custom_scenarios=10
        )
        self.assertIn("predefined_scenarios", result)
        self.assertIn("custom_scenarios_summary", result)
        self.assertIn("worst_case_scenarios", result)
        self.assertIn("time_taken", result)
        self.assertGreater(len(result["predefined_scenarios"]), 0)
        summary = result["custom_scenarios_summary"]
        self.assertEqual(summary["count"], 10)
        self.assertIn("avg_return", summary)
        self.assertIn("min_return", summary)
        self.assertIn("max_return", summary)
        self.assertIn("avg_var_95", summary)

    def test_parallel_backtest(self) -> Any:
        """Test parallel backtesting"""
        result = self.engine.parallel_backtest(
            self.returns.mean(axis=1),
            risk_models=["parametric", "historical"],
            confidence_level=0.95,
            window_size=100,
            step_size=50,
        )
        self.assertIn("summary", result)
        self.assertIn("windows", result)
        self.assertIn("time_taken", result)
        for model in ["parametric", "historical"]:
            self.assertIn(model, result["summary"])
            self.assertIn("breaches", result["summary"][model])
            self.assertIn("total", result["summary"][model])
            self.assertIn("breach_rate", result["summary"][model])
            self.assertIn("expected_breach_rate", result["summary"][model])
            self.assertLessEqual(result["summary"][model]["breach_rate"], 0.2)

    def test_parallel_sensitivity_analysis(self) -> Any:
        """Test parallel sensitivity analysis"""
        result = self.engine.parallel_sensitivity_analysis(
            self.returns, self.weights, n_points=5
        )
        self.assertIn("factor_results", result)
        self.assertIn("sensitivities", result)
        self.assertIn("time_taken", result)
        for factor in self.returns.columns:
            self.assertIn(factor, result["factor_results"])
            self.assertIn("shocks", result["factor_results"][factor])
            self.assertIn("portfolio_returns", result["factor_results"][factor])
            self.assertIn("var_95", result["factor_results"][factor])
            self.assertIn(factor, result["sensitivities"])
            self.assertIn("return_sensitivity", result["sensitivities"][factor])
            self.assertIn("var_sensitivity", result["sensitivities"][factor])

    def test_parallel_risk_decomposition(self) -> Any:
        """Test parallel risk decomposition"""
        result = self.engine.parallel_risk_decomposition(
            self.returns, self.weights, risk_measure="volatility"
        )
        self.assertIn("risk_measure", result)
        self.assertIn("total_risk", result)
        self.assertIn("contributions", result)
        self.assertIn("time_taken", result)
        self.assertEqual(result["risk_measure"], "volatility")
        self.assertGreater(result["total_risk"], 0)
        self.assertEqual(len(result["contributions"]), 3)
        total_contribution = sum(
            (c["percentage_contribution"] for c in result["contributions"])
        )
        self.assertAlmostEqual(total_contribution, 1.0, delta=0.01)


class TestReportingFramework(unittest.TestCase):
    """Test cases for Reporting Framework module"""

    def setUp(self) -> Any:
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        self.returns = pd.DataFrame(
            {
                "Asset_1": np.random.normal(0.001, 0.02, n_samples),
                "Asset_2": np.random.normal(0.0005, 0.015, n_samples),
                "Asset_3": np.random.normal(0.0008, 0.025, n_samples),
            }
        )
        self.returns.index = pd.date_range(
            start="2020-01-01", periods=n_samples, freq="B"
        )
        self.weights = {"Asset_1": 0.4, "Asset_2": 0.3, "Asset_3": 0.3}
        self.report_dir = tempfile.mkdtemp()

    def tearDown(self) -> Any:
        """Clean up temporary directory"""
        shutil.rmtree(self.report_dir)

    def test_report_template_creation(self) -> Any:
        """Test report template creation"""
        template = ReportTemplate(
            title="Risk Analysis Report",
            sections=[
                {
                    "title": "Portfolio Overview",
                    "content": "Overview of portfolio performance",
                },
                {"title": "Risk Metrics", "content": "Analysis of risk metrics"},
            ],
        )
        self.assertEqual(template.title, "Risk Analysis Report")
        self.assertEqual(len(template.sections), 2)
        self.assertEqual(template.sections[0]["title"], "Portfolio Overview")

    def test_report_template_save_load(self) -> Any:
        """Test saving and loading report templates"""
        template = ReportTemplate(
            title="Risk Analysis Report",
            sections=[
                {
                    "title": "Portfolio Overview",
                    "content": "Overview of portfolio performance",
                },
                {"title": "Risk Metrics", "content": "Analysis of risk metrics"},
            ],
        )
        template_path = os.path.join(self.report_dir, "template.json")
        template.save(template_path)
        self.assertTrue(os.path.exists(template_path))
        loaded_template = ReportTemplate.load(template_path)
        self.assertEqual(loaded_template.title, template.title)
        self.assertEqual(len(loaded_template.sections), len(template.sections))
        self.assertEqual(
            loaded_template.sections[0]["title"], template.sections[0]["title"]
        )

    def test_html_report_generation(self) -> Any:
        """Test HTML report generation"""
        template = ReportTemplate(
            title="Risk Analysis Report",
            sections=[
                {
                    "title": "Portfolio Overview",
                    "content": "Overview of portfolio performance",
                },
                {"title": "Risk Metrics", "content": "Analysis of risk metrics"},
            ],
        )
        generator = ReportGenerator(template)
        report_path = os.path.join(self.report_dir, "report.html")
        generator.generate_html(
            report_path,
            data={
                "portfolio_name": "Test Portfolio",
                "date": datetime.now().strftime("%Y-%m-%d"),
                "returns": self.returns,
                "weights": self.weights,
            },
        )
        self.assertTrue(os.path.exists(report_path))
        with open(report_path, "r") as f:
            content = f.read()
            self.assertIn("Risk Analysis Report", content)
            self.assertIn("Portfolio Overview", content)
            self.assertIn("Risk Metrics", content)

    def test_pdf_report_generation(self) -> Any:
        """Test PDF report generation"""
        template = ReportTemplate(
            title="Risk Analysis Report",
            sections=[
                {
                    "title": "Portfolio Overview",
                    "content": "Overview of portfolio performance",
                },
                {"title": "Risk Metrics", "content": "Analysis of risk metrics"},
            ],
        )
        generator = ReportGenerator(template)
        report_path = os.path.join(self.report_dir, "report.pdf")
        try:
            generator.generate_pdf(
                report_path,
                data={
                    "portfolio_name": "Test Portfolio",
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "returns": self.returns,
                    "weights": self.weights,
                },
            )
            self.assertTrue(os.path.exists(report_path))
        except ImportError:
            pass


class TestDashboardFramework(unittest.TestCase):
    """Test cases for Dashboard Framework module"""

    def setUp(self) -> Any:
        """Set up test data"""
        np.random.seed(42)
        n_samples = 500
        self.returns = pd.DataFrame(
            {
                "Asset_1": np.random.normal(0.001, 0.02, n_samples),
                "Asset_2": np.random.normal(0.0005, 0.015, n_samples),
                "Asset_3": np.random.normal(0.0008, 0.025, n_samples),
            }
        )
        self.returns.index = pd.date_range(
            start="2020-01-01", periods=n_samples, freq="B"
        )
        self.cumulative_returns = (1 + self.returns).cumprod() - 1
        self.risk_metrics = pd.DataFrame(
            {
                "Metric": [
                    "Volatility",
                    "VaR (95%)",
                    "ES (95%)",
                    "Sharpe Ratio",
                    "Max Drawdown",
                ],
                "Portfolio": [0.02, 0.033, 0.041, 0.8, 0.15],
                "Benchmark": [0.015, 0.025, 0.031, 0.6, 0.12],
            }
        )
        dashboard_dir = tempfile.mkdtemp()
        self.dashboard_dir = dashboard_dir
        self.manager = DashboardManager(storage_dir=dashboard_dir)

    def tearDown(self) -> Any:
        """Clean up temporary directory"""
        shutil.rmtree(self.dashboard_dir)

    def test_dashboard_creation(self) -> Any:
        """Test dashboard creation"""
        dashboard = Dashboard(
            "Risk Analysis Dashboard", "Analysis of portfolio risk metrics"
        )
        dashboard.add_component(
            ChartComponent(
                title="Cumulative Returns",
                chart_type="line",
                data=self.cumulative_returns,
                options={"ylabel": "Return", "legend": True},
                width=12,
                height=6,
                position=(0, 0),
            )
        )
        self.assertEqual(dashboard.title, "Risk Analysis Dashboard")
        self.assertEqual(len(dashboard.components), 1)
        self.assertEqual(dashboard.components[0].title, "Cumulative Returns")

    def test_dashboard_save_load(self) -> Any:
        """Test saving and loading dashboards"""
        dashboard = Dashboard(
            "Risk Analysis Dashboard", "Analysis of portfolio risk metrics"
        )
        dashboard.add_component(
            ChartComponent(
                title="Cumulative Returns",
                chart_type="line",
                data=self.cumulative_returns,
                options={"ylabel": "Return", "legend": True},
                width=12,
                height=6,
                position=(0, 0),
            )
        )
        dashboard_path = os.path.join(self.dashboard_dir, "dashboard.json")
        dashboard.save(dashboard_path)
        self.assertTrue(os.path.exists(dashboard_path))
        loaded_dashboard = Dashboard.load(dashboard_path)
        self.assertEqual(loaded_dashboard.title, dashboard.title)
        self.assertEqual(len(loaded_dashboard.components), len(dashboard.components))
        self.assertEqual(
            loaded_dashboard.components[0].title, dashboard.components[0].title
        )

    def test_dashboard_manager(self) -> Any:
        """Test dashboard manager"""
        dashboard = self.manager.create_dashboard(
            title="Risk Analysis Dashboard",
            description="Analysis of portfolio risk metrics",
        )
        dashboard.add_component(
            ChartComponent(
                title="Cumulative Returns",
                chart_type="line",
                data=self.cumulative_returns,
                options={"ylabel": "Return", "legend": True},
                width=12,
                height=6,
                position=(0, 0),
            )
        )
        self.manager.update_dashboard(dashboard)
        dashboards = self.manager.list_dashboards()
        self.assertEqual(len(dashboards), 1)
        self.assertEqual(dashboards[0]["title"], "Risk Analysis Dashboard")
        retrieved_dashboard = self.manager.get_dashboard(dashboard.id)
        self.assertEqual(retrieved_dashboard.title, dashboard.title)
        self.assertEqual(len(retrieved_dashboard.components), len(dashboard.components))
        self.manager.delete_dashboard(dashboard.id)
        dashboards = self.manager.list_dashboards()
        self.assertEqual(len(dashboards), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
    logger.info("Test Summary:")
    logger.info(f"  Ran {unittest.TestResult().testsRun} tests")
    logger.info(f"  Failures: {len(unittest.TestResult().failures)}")
    logger.info(f"  Errors: {len(unittest.TestResult().errors)}")
