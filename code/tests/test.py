"""
Test suite for RiskOptimizer enhancements

This module provides comprehensive tests for:
1. Extreme Value Theory risk models
2. Machine Learning risk models
3. Parallel risk calculation engine
4. Reporting framework
5. Dashboard framework

The tests validate functionality, integration, and performance of all new features.
"""

import os
import shutil
import sys
import tempfile
import unittest
from typing import Any

import numpy as np
import pandas as pd

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import logging

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


class TestExtremeValueTheory(unittest.TestCase):
    """Test cases for Extreme Value Theory risk models"""

    def setUp(self) -> Any:
        """Set up test data"""
        np.random.seed(42)
        self.normal_returns = np.random.normal(0.001, 0.02, 1000)
        self.returns_with_extremes = self.normal_returns.copy()
        extreme_indices = np.random.choice(1000, 20, replace=False)
        self.returns_with_extremes[extreme_indices] = np.random.normal(-0.08, 0.03, 20)
        self.evt_model = ExtremeValueRisk()

    def test_pot_fitting(self) -> Any:
        """Test Peaks Over Threshold fitting"""
        self.evt_model.fit_pot(self.returns_with_extremes, threshold_quantile=0.05)
        self.assertTrue(self.evt_model.fitted)
        shape, scale = self.evt_model.gpd_params
        self.assertIsNotNone(shape)
        self.assertIsNotNone(scale)
        self.assertLess(abs(shape), 1.0)
        self.assertGreater(scale, 0)

    def test_var_calculation(self) -> Any:
        """Test Value at Risk calculation"""
        self.evt_model.fit_pot(self.returns_with_extremes, threshold_quantile=0.05)
        var_95 = self.evt_model.calculate_var(0.95, method="evt")
        var_99 = self.evt_model.calculate_var(0.99, method="evt")
        self.assertGreater(var_99, var_95)
        normal_var_95 = -np.percentile(self.returns_with_extremes, 5)
        self.assertGreaterEqual(var_95, normal_var_95 * 0.8)

    def test_es_calculation(self) -> Any:
        """Test Expected Shortfall calculation"""
        self.evt_model.fit_pot(self.returns_with_extremes, threshold_quantile=0.05)
        es_95 = self.evt_model.calculate_es(0.95)
        es_99 = self.evt_model.calculate_es(0.99)
        self.assertGreater(es_99, es_95)
        var_95 = self.evt_model.calculate_var(0.95, method="evt")
        self.assertGreater(es_95, var_95)

    def test_block_maxima(self) -> Any:
        """Test Block Maxima method"""
        result = self.evt_model.fit_block_maxima(
            self.returns_with_extremes, block_size=20
        )
        self.assertIn("shape", result)
        self.assertIn("loc", result)
        self.assertIn("scale", result)
        self.assertIn("block_maxima", result)
        self.assertEqual(len(result["block_maxima"]), 1000 // 20)

    def test_stress_scenarios(self) -> Any:
        """Test extreme scenario generation"""
        self.evt_model.fit_pot(self.returns_with_extremes, threshold_quantile=0.05)
        scenarios = self.evt_model.simulate_extreme_scenarios(
            n_scenarios=100, confidence=0.95
        )
        self.assertEqual(len(scenarios), 100)
        var_95 = self.evt_model.calculate_var(0.95, method="evt")
        self.assertTrue(all((scenario > var_95 for scenario in scenarios)))

    def test_tail_dependence(self) -> Any:
        """Test tail dependence calculation"""
        np.random.seed(42)
        returns1 = self.returns_with_extremes
        returns2 = 0.7 * returns1 + 0.3 * np.random.normal(0.001, 0.02, 1000)
        tail_dep = self.evt_model.tail_dependence(
            returns1, returns2, threshold_quantile=0.05
        )
        self.assertGreaterEqual(tail_dep, 0)
        self.assertLessEqual(tail_dep, 1)
        self.assertGreater(tail_dep, 0.5)


class TestMLRiskModels(unittest.TestCase):
    """Test cases for Machine Learning risk models"""

    def setUp(self) -> Any:
        """Set up test data"""
        np.random.seed(42)
        n_days = 1000
        self.asset_returns = pd.DataFrame(
            np.random.multivariate_normal(
                mean=[0.001, 0.0005, 0.0008, 0.0012],
                cov=[
                    [0.0004, 0.0002, 0.0001, 0.0001],
                    [0.0002, 0.0005, 0.0001, 0.0002],
                    [0.0001, 0.0001, 0.0006, 0.0002],
                    [0.0001, 0.0002, 0.0002, 0.0004],
                ],
                size=n_days,
            ),
            columns=["Asset_1", "Asset_2", "Asset_3", "Asset_4"],
        )
        self.asset_returns.index = pd.date_range(
            start="2020-01-01", periods=n_days, freq="B"
        )
        self.ml_model = MLRiskModel(model_type="gbm", quantile=0.05)
        self.copula_model = CopulaMLRiskModel(copula_type="gaussian", n_scenarios=1000)

    def test_ml_model_training(self) -> Any:
        """Test ML model training"""
        self.ml_model.fit(
            self.asset_returns, feature_window=10, horizon=1, test_size=0.2
        )
        self.assertTrue(self.ml_model.trained)
        self.assertIsNotNone(self.ml_model.feature_names)
        self.assertGreater(len(self.ml_model.feature_names), 0)
        self.assertIsNotNone(self.ml_model.feature_importance)

    def test_ml_var_prediction(self) -> Any:
        """Test ML VaR prediction"""
        self.ml_model.fit(
            self.asset_returns, feature_window=10, horizon=1, test_size=0.2
        )
        var_pred = self.ml_model.predict_var(self.asset_returns, confidence=0.95)
        self.assertIsNotNone(var_pred)
        self.assertGreater(len(var_pred), 0)
        self.assertTrue(all(var_pred > 0))

    def test_ml_es_prediction(self) -> Any:
        """Test ML ES prediction"""
        self.ml_model.fit(
            self.asset_returns, feature_window=10, horizon=1, test_size=0.2
        )
        es_pred = self.ml_model.predict_es(self.asset_returns, confidence=0.95)
        self.assertIsNotNone(es_pred)
        self.assertGreater(len(es_pred), 0)
        var_pred = self.ml_model.predict_var(self.asset_returns, confidence=0.95)
        self.assertTrue(all(es_pred >= var_pred * 0.9))

    def test_ml_model_save_load(self) -> Any:
        """Test ML model saving and loading"""
        self.ml_model.fit(
            self.asset_returns, feature_window=10, horizon=1, test_size=0.2
        )
        temp_dir = tempfile.mkdtemp()
        model_path = os.path.join(temp_dir, "ml_model.joblib")
        self.ml_model.save_model(model_path)
        self.assertTrue(os.path.exists(model_path))
        loaded_model = MLRiskModel.load_model(model_path)
        self.assertTrue(loaded_model.trained)
        shutil.rmtree(temp_dir)

    def test_copula_fitting(self) -> Any:
        """Test copula model fitting"""
        self.copula_model.fit(self.asset_returns)
        self.assertTrue(self.copula_model.trained)
        self.assertEqual(
            self.copula_model.asset_names.tolist(), self.asset_returns.columns.tolist()
        )

    def test_scenario_generation(self) -> Any:
        """Test scenario generation with copula model"""
        self.copula_model.fit(self.asset_returns)
        n_scenarios = 500
        scenarios = self.copula_model.generate_scenarios(n_scenarios)
        self.assertEqual(len(scenarios), n_scenarios)
        self.assertEqual(scenarios.shape[1], self.asset_returns.shape[1])
        self.assertAlmostEqual(
            scenarios.mean().mean(), self.asset_returns.mean().mean(), delta=0.01
        )

    def test_copula_var_calculation(self) -> Any:
        """Test VaR calculation with copula model"""
        self.copula_model.fit(self.asset_returns)
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        var_95 = self.copula_model.calculate_var(weights, confidence=0.95)
        var_99 = self.copula_model.calculate_var(weights, confidence=0.99)
        self.assertGreater(var_99, var_95)
        self.assertGreater(var_95, 0)
        self.assertGreater(var_99, 0)

    def test_copula_es_calculation(self) -> Any:
        """Test ES calculation with copula model"""
        self.copula_model.fit(self.asset_returns)
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        es_95 = self.copula_model.calculate_es(weights, confidence=0.95)
        var_95 = self.copula_model.calculate_var(weights, confidence=0.95)
        self.assertGreater(es_95, var_95)

    def test_copula_risk_metrics(self) -> Any:
        """Test risk metrics calculation with copula model"""
        self.copula_model.fit(self.asset_returns)
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        metrics = self.copula_model.calculate_risk_metrics(
            weights, confidence_levels=[0.95, 0.99]
        )
        self.assertIn("mean", metrics)
        self.assertIn("std", metrics)
        self.assertIn("skewness", metrics)
        self.assertIn("kurtosis", metrics)
        self.assertIn("var_95", metrics)
        self.assertIn("es_95", metrics)
        self.assertIn("var_99", metrics)
        self.assertIn("es_99", metrics)
        self.assertGreater(metrics["var_99"], metrics["var_95"])
        self.assertGreater(metrics["es_99"], metrics["es_95"])
        self.assertGreater(metrics["es_95"], metrics["var_95"])
        self.assertGreater(metrics["es_99"], metrics["var_99"])


class TestParallelRiskEngine(unittest.TestCase):
    """Test cases for Parallel Risk Engine"""

    def setUp(self) -> Any:
        """Set up test data and engine"""
        np.random.seed(42)
        n_days = 1000
        self.asset_returns = pd.DataFrame(
            np.random.multivariate_normal(
                mean=[0.001, 0.0005, 0.0008, 0.0012],
                cov=[
                    [0.0004, 0.0002, 0.0001, 0.0001],
                    [0.0002, 0.0005, 0.0001, 0.0002],
                    [0.0001, 0.0001, 0.0006, 0.0002],
                    [0.0001, 0.0002, 0.0002, 0.0004],
                ],
                size=n_days,
            ),
            columns=["Asset_1", "Asset_2", "Asset_3", "Asset_4"],
        )
        self.asset_returns.index = pd.date_range(
            start="2020-01-01", periods=n_days, freq="B"
        )
        self.weights = {
            "Asset_1": 0.25,
            "Asset_2": 0.25,
            "Asset_3": 0.25,
            "Asset_4": 0.25,
        }
        self.evt_model = ExtremeValueRisk()
        self.evt_model.fit_pot(self.asset_returns.mean(axis=1), threshold_quantile=0.05)
        self.copula_model = CopulaMLRiskModel(copula_type="gaussian", n_scenarios=1000)
        self.copula_model.fit(self.asset_returns)
        self.engine = ParallelRiskEngine(n_jobs=2, backend="multiprocessing", verbose=0)

    def test_parallel_monte_carlo(self) -> Any:
        """Test parallel Monte Carlo simulation"""
        result = self.engine.parallel_monte_carlo(
            self.copula_model,
            self.weights,
            n_scenarios=1000,
            confidence_levels=[0.95, 0.99],
        )
        self.assertIn("portfolio_metrics", result)
        self.assertIn("risk_metrics", result)
        self.assertIn("expected_return", result["portfolio_metrics"])
        self.assertIn("volatility", result["portfolio_metrics"])
        self.assertIn("skewness", result["portfolio_metrics"])
        self.assertIn("kurtosis", result["portfolio_metrics"])
        self.assertIn("var_95", result["risk_metrics"])
        self.assertIn("es_95", result["risk_metrics"])
        self.assertIn("var_99", result["risk_metrics"])
        self.assertIn("es_99", result["risk_metrics"])
        self.assertGreater(
            result["risk_metrics"]["var_99"], result["risk_metrics"]["var_95"]
        )
        self.assertGreater(
            result["risk_metrics"]["es_95"], result["risk_metrics"]["var_95"]
        )
        self.assertGreater(
            result["risk_metrics"]["es_99"], result["risk_metrics"]["var_99"]
        )

    def test_parallel_portfolio_optimization(self) -> Any:
        """Test parallel portfolio optimization"""
        result = self.engine.parallel_portfolio_optimization(
            self.asset_returns, risk_model="markowitz", n_portfolios=500
        )
        self.assertIn("efficient_frontier", result)
        self.assertIn("max_sharpe_portfolio", result)
        self.assertIn("min_volatility_portfolio", result)
        self.assertGreater(len(result["efficient_frontier"]), 0)
        self.assertIn("weights", result["max_sharpe_portfolio"])
        self.assertIn("return", result["max_sharpe_portfolio"])
        self.assertIn("volatility", result["max_sharpe_portfolio"])
        self.assertIn("sharpe_ratio", result["max_sharpe_portfolio"])
        self.assertIn("weights", result["min_volatility_portfolio"])
        self.assertIn("return", result["min_volatility_portfolio"])
        self.assertIn("volatility", result["min_volatility_portfolio"])
        self.assertIn("sharpe_ratio", result["min_volatility_portfolio"])
        self.assertLessEqual(
            result["min_volatility_portfolio"]["volatility"],
            result["max_sharpe_portfolio"]["volatility"],
        )

    def test_parallel_batch_risk_calculation(self) -> Any:
        """Test parallel batch risk calculation"""
        result = self.engine.parallel_batch_risk_calculation(
            self.asset_returns.mean(axis=1),
            risk_models=["parametric", "historical", "evt"],
            confidence_levels=[0.95, 0.99],
        )
        self.assertIn("risk_metrics", result)
        self.assertIn("parametric", result["risk_metrics"])
        self.assertIn("historical", result["risk_metrics"])
        self.assertIn("evt", result["risk_metrics"])
        for model in ["parametric", "historical", "evt"]:
            self.assertIn("var_95", result["risk_metrics"][model])
            self.assertIn("es_95", result["risk_metrics"][model])
            self.assertIn("var_99", result["risk_metrics"][model])
            self.assertIn("es_99", result["risk_metrics"][model])
            self.assertGreater(
                result["risk_metrics"][model]["var_99"],
                result["risk_metrics"][model]["var_95"],
            )
            self.assertGreater(
                result["risk_metrics"][model]["es_95"],
                result["risk_metrics"][model]["var_95"],
            )
            self.assertGreater(
                result["risk_metrics"][model]["es_99"],
                result["risk_metrics"][model]["var_99"],
            )

    def test_parallel_stress_testing(self) -> Any:
        """Test parallel stress testing"""
        result = self.engine.parallel_stress_testing(
            self.asset_returns, self.weights, n_custom_scenarios=100
        )
        self.assertIn("predefined_scenarios", result)
        self.assertIn("custom_scenarios_summary", result)
        self.assertIn("worst_case_scenarios", result)
        self.assertGreater(len(result["predefined_scenarios"]), 0)
        self.assertIn("count", result["custom_scenarios_summary"])
        self.assertIn("avg_return", result["custom_scenarios_summary"])
        self.assertIn("min_return", result["custom_scenarios_summary"])
        self.assertIn("max_return", result["custom_scenarios_summary"])
        self.assertIn("avg_var_95", result["custom_scenarios_summary"])
        self.assertIn("max_var_95", result["custom_scenarios_summary"])
        self.assertIn("worst_return", result["worst_case_scenarios"])
        self.assertIn("worst_var", result["worst_case_scenarios"])

    def test_parallel_backtest(self) -> Any:
        """Test parallel backtesting"""
        result = self.engine.parallel_backtest(
            self.asset_returns,
            risk_models=["parametric", "historical", "evt"],
            confidence_level=0.95,
            window_size=252,
            step_size=20,
        )
        self.assertIn("summary", result)
        self.assertIn("windows", result)
        for model in ["parametric", "historical", "evt"]:
            self.assertIn(model, result["summary"])
            self.assertIn("breaches", result["summary"][model])
            self.assertIn("total", result["summary"][model])
            self.assertIn("breach_rate", result["summary"][model])
            self.assertIn("expected_breach_rate", result["summary"][model])
            self.assertIn("breach_ratio", result["summary"][model])
        self.assertGreater(len(result["windows"]), 0)

    def test_parallel_sensitivity_analysis(self) -> Any:
        """Test parallel sensitivity analysis"""
        result = self.engine.parallel_sensitivity_analysis(
            self.asset_returns, self.weights, shock_range=(-0.05, 0.05), n_points=5
        )
        self.assertIn("factor_results", result)
        self.assertIn("sensitivities", result)
        for factor in self.asset_returns.columns:
            self.assertIn(factor, result["factor_results"])
            self.assertIn("shocks", result["factor_results"][factor])
            self.assertIn("portfolio_returns", result["factor_results"][factor])
            self.assertIn("portfolio_volatilities", result["factor_results"][factor])
            self.assertIn("var_95", result["factor_results"][factor])
            self.assertIn("es_95", result["factor_results"][factor])
        for factor in self.asset_returns.columns:
            self.assertIn(factor, result["sensitivities"])
            self.assertIn("return_sensitivity", result["sensitivities"][factor])
            self.assertIn("var_sensitivity", result["sensitivities"][factor])

    def test_parallel_risk_decomposition(self) -> Any:
        """Test parallel risk decomposition"""
        result = self.engine.parallel_risk_decomposition(
            self.asset_returns, self.weights, risk_measure="volatility"
        )
        self.assertIn("risk_measure", result)
        self.assertIn("total_risk", result)
        self.assertIn("contributions", result)
        self.assertEqual(result["risk_measure"], "volatility")
        self.assertEqual(len(result["contributions"]), len(self.weights))
        total_contribution = sum(
            (c["percentage_contribution"] for c in result["contributions"])
        )
        self.assertAlmostEqual(total_contribution, 1.0, delta=0.01)

    def test_system_info(self) -> Any:
        """Test system info retrieval"""
        info = self.engine.system_info()
        self.assertIn("cpu_count", info)
        self.assertIn("cpu_percent", info)
        self.assertIn("memory", info)
        self.assertIn("backend", info)
        self.assertIn("n_jobs", info)
        self.assertGreaterEqual(info["cpu_count"], 1)
        self.assertEqual(info["backend"], "multiprocessing")
        self.assertEqual(info["n_jobs"], 2)


class TestReportingFramework(unittest.TestCase):
    """Test cases for Reporting Framework"""

    def setUp(self) -> Any:
        """Set up test data and framework"""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = ReportGenerator(
            template_dir=os.path.join(self.temp_dir, "templates"),
            output_dir=os.path.join(self.temp_dir, "reports"),
        )
        self.data = {
            "risk_metrics": {
                "var_95": 0.0325,
                "es_95": 0.0487,
                "volatility": 0.18,
                "sharpe_ratio": 0.75,
                "diversification_ratio": 0.65,
                "max_drawdown": 0.28,
            },
            "risk_decomposition": pd.DataFrame(
                {
                    "asset": ["Equity", "Fixed Income", "Commodities", "Real Estate"],
                    "weight": [0.5, 0.3, 0.1, 0.1],
                    "contribution": [0.6, 0.2, 0.15, 0.05],
                    "marginal_contribution": [0.12, 0.067, 0.15, 0.05],
                }
            ),
            "historical_var": pd.DataFrame(
                {
                    "date": pd.date_range(start="2024-01-01", periods=100, freq="B"),
                    "var_95": np.random.normal(0.03, 0.005, 100),
                    "var_99": np.random.normal(0.045, 0.008, 100),
                }
            ).set_index("date"),
        }

    def tearDown(self) -> Any:
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir)

    def test_report_template_creation(self) -> Any:
        """Test report template creation"""
        template = ReportTemplate(
            name="Test Template", description="Test template description"
        )
        template.add_section(
            ReportSection(
                title="Text Section",
                section_type="text",
                content={"text": "This is a test section"},
            )
        )
        template.add_section(
            ReportSection(
                title="Table Section",
                section_type="table",
                data_source={"type": "direct", "path": "risk_decomposition"},
            )
        )
        template.add_section(
            ReportSection(
                title="Chart Section",
                section_type="chart",
                data_source={"type": "direct", "path": "historical_var"},
                parameters={"chart_type": "line"},
            )
        )
        self.assertEqual(template.name, "Test Template")
        self.assertEqual(template.description, "Test template description")
        self.assertEqual(len(template.sections), 3)
        self.assertEqual(template.sections[0].section_type, "text")
        self.assertEqual(template.sections[1].section_type, "table")
        self.assertEqual(template.sections[2].section_type, "chart")

    def test_report_template_save_load(self) -> Any:
        """Test saving and loading report templates"""
        template = ReportTemplate(
            name="Test Template", description="Test template description"
        )
        template.add_section(
            ReportSection(
                title="Test Section",
                section_type="text",
                content={"text": "This is a test section"},
            )
        )
        template_path = os.path.join(self.temp_dir, "test_template.json")
        template.save(template_path)
        self.assertTrue(os.path.exists(template_path))
        loaded_template = ReportTemplate.load(template_path)
        self.assertEqual(loaded_template.name, "Test Template")
        self.assertEqual(loaded_template.description, "Test template description")
        self.assertEqual(len(loaded_template.sections), 1)
        self.assertEqual(loaded_template.sections[0].title, "Test Section")

    def test_html_report_generation(self) -> Any:
        """Test HTML report generation"""
        template = ReportTemplate(
            name="Test Report", description="Test report description"
        )
        template.add_section(
            ReportSection(
                title="Risk Metrics",
                section_type="risk_metrics",
                data_source={"type": "direct", "path": "risk_metrics"},
            )
        )
        template.add_section(
            ReportSection(
                title="Risk Decomposition",
                section_type="table",
                data_source={"type": "direct", "path": "risk_decomposition"},
            )
        )
        output_path = os.path.join(self.temp_dir, "test_report.html")
        html_content = self.generator.generate_html(template, self.data, output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertIsNotNone(html_content)
        self.assertGreater(len(html_content), 0)
        self.assertIn("Risk Metrics", html_content)
        self.assertIn("Risk Decomposition", html_content)
        self.assertIn("0.0325", html_content)
        self.assertIn("Equity", html_content)

    def test_section_processing(self) -> Any:
        """Test section processing"""
        text_section = ReportSection(
            title="Text Section",
            section_type="text",
            content={
                "text": "This is a test section with value {{ data.risk_metrics.var_95 }}"
            },
            parameters={"render_template": True},
        )
        table_section = ReportSection(
            title="Table Section",
            section_type="table",
            data_source={"type": "direct", "path": "risk_decomposition"},
            parameters={"show_index": False},
        )
        chart_section = ReportSection(
            title="Chart Section",
            section_type="chart",
            data_source={"type": "direct", "path": "historical_var"},
            parameters={"chart_type": "line", "width": 8, "height": 5},
        )
        processed_text = self.generator._process_section(text_section, self.data)
        processed_table = self.generator._process_section(table_section, self.data)
        processed_chart = self.generator._process_section(chart_section, self.data)
        self.assertIn("rendered_content", processed_text)
        self.assertIn("rendered_content", processed_table)
        self.assertIn("rendered_content", processed_chart)
        self.assertIn("0.0325", processed_text["rendered_content"])
        self.assertIn("<table", processed_table["rendered_content"])
        self.assertIn("Equity", processed_table["rendered_content"])
        self.assertIn("<img", processed_chart["rendered_content"])


class TestDashboardFramework(unittest.TestCase):
    """Test cases for Dashboard Framework"""

    def setUp(self) -> Any:
        """Set up test data and framework"""
        self.temp_dir = tempfile.mkdtemp()
        self.manager = DashboardManager(
            dashboard_dir=os.path.join(self.temp_dir, "dashboards")
        )
        self.template_dir = os.path.join(self.temp_dir, "templates")
        os.makedirs(self.template_dir, exist_ok=True)
        with open(os.path.join(self.template_dir, "dashboard_template.html"), "w") as f:
            f.write(
                '\n            <!DOCTYPE html>\n            <html>\n            <head>\n                <title>{{ dashboard.title }}</title>\n            </head>\n            <body>\n                <h1>{{ dashboard.title }}</h1>\n                <p>{{ dashboard.description }}</p>\n\n                {% for component in components %}\n                <div class="component">\n                    <h2>{{ component.title }}</h2>\n                    {{ component.rendered_content|safe }}\n                </div>\n                {% endfor %}\n            </body>\n            </html>\n            '
            )
        self.renderer = DashboardRenderer(template_dir=self.template_dir)
        self.data = {
            "risk_metrics": {
                "current": {
                    "var_95": 0.0325,
                    "es_95": 0.0487,
                    "volatility": 0.18,
                    "sharpe_ratio": 0.75,
                },
                "var_history": pd.DataFrame(
                    {
                        "date": pd.date_range(
                            start="2024-01-01", periods=100, freq="B"
                        ),
                        "var_95": np.random.normal(0.03, 0.005, 100),
                        "var_99": np.random.normal(0.045, 0.008, 100),
                    }
                ).set_index("date"),
                "decomposition": pd.DataFrame(
                    {
                        "asset": [
                            "Equity",
                            "Fixed Income",
                            "Commodities",
                            "Real Estate",
                        ],
                        "weight": [0.5, 0.3, 0.1, 0.1],
                        "contribution": [0.6, 0.2, 0.15, 0.05],
                        "marginal_contribution": [0.12, 0.067, 0.15, 0.05],
                    }
                ),
            }
        }

    def tearDown(self) -> Any:
        """Clean up temporary files"""
        shutil.rmtree(self.temp_dir)

    def test_dashboard_creation(self) -> Any:
        """Test dashboard creation"""
        dashboard = Dashboard(
            title="Test Dashboard", description="Test dashboard description"
        )
        chart = ChartComponent(title="VaR Chart", chart_type="line")
        chart.set_data_source({"type": "direct", "path": "risk_metrics.var_history"})
        chart.set_position(0, 0, 8, 4)
        dashboard.add_component(chart)
        self.assertEqual(dashboard.title, "Test Dashboard")
        self.assertEqual(dashboard.description, "Test dashboard description")
        self.assertEqual(len(dashboard.components), 1)
        self.assertEqual(dashboard.components[0].title, "VaR Chart")
        self.assertEqual(dashboard.components[0].component_type, "chart")
        self.assertEqual(dashboard.components[0].position["x"], 0)
        self.assertEqual(dashboard.components[0].position["y"], 0)
        self.assertEqual(dashboard.components[0].position["w"], 8)
        self.assertEqual(dashboard.components[0].position["h"], 4)

    def test_dashboard_save_load(self) -> Any:
        """Test saving and loading dashboards"""
        dashboard = Dashboard(
            title="Test Dashboard", description="Test dashboard description"
        )
        dashboard.add_component(ChartComponent(title="Test Chart", chart_type="line"))
        dashboard_path = os.path.join(self.temp_dir, "test_dashboard.json")
        dashboard.save(dashboard_path)
        self.assertTrue(os.path.exists(dashboard_path))
        loaded_dashboard = Dashboard.load(dashboard_path)
        self.assertEqual(loaded_dashboard.title, "Test Dashboard")
        self.assertEqual(loaded_dashboard.description, "Test dashboard description")
        self.assertEqual(len(loaded_dashboard.components), 1)
        self.assertEqual(loaded_dashboard.components[0].title, "Test Chart")

    def test_dashboard_manager(self) -> Any:
        """Test dashboard manager"""
        dashboard = self.manager.create_dashboard(
            title="Test Dashboard", description="Test dashboard description"
        )
        self.assertIsNotNone(dashboard)
        self.assertEqual(dashboard.title, "Test Dashboard")
        retrieved_dashboard = self.manager.get_dashboard(dashboard.id)
        self.assertIsNotNone(retrieved_dashboard)
        self.assertEqual(retrieved_dashboard.id, dashboard.id)
        self.assertEqual(retrieved_dashboard.title, "Test Dashboard")
        dashboard_list = self.manager.list_dashboards()
        self.assertEqual(len(dashboard_list), 1)
        self.assertEqual(dashboard_list[0]["id"], dashboard.id)
        self.assertEqual(dashboard_list[0]["title"], "Test Dashboard")
        dashboard.title = "Updated Dashboard"
        self.manager.update_dashboard(dashboard)
        updated_dashboard = self.manager.get_dashboard(dashboard.id)
        self.assertEqual(updated_dashboard.title, "Updated Dashboard")
        self.manager.delete_dashboard(dashboard.id)
        self.assertIsNone(self.manager.get_dashboard(dashboard.id))
        self.assertEqual(len(self.manager.list_dashboards()), 0)

    def test_dashboard_rendering(self) -> Any:
        """Test dashboard rendering"""
        dashboard = Dashboard(
            title="Test Dashboard", description="Test dashboard description"
        )
        chart = ChartComponent(title="VaR Chart", chart_type="line")
        chart.set_data_source({"type": "direct", "path": "risk_metrics.var_history"})
        chart.set_position(0, 0, 8, 4)
        dashboard.add_component(chart)
        output_path = os.path.join(self.temp_dir, "test_dashboard.html")
        html_content = self.renderer.render_dashboard(dashboard, self.data, output_path)
        self.assertTrue(os.path.exists(output_path))
        self.assertIsNotNone(html_content)
        self.assertGreater(len(html_content), 0)
        self.assertIn("Test Dashboard", html_content)
        self.assertIn("VaR Chart", html_content)


def run_tests() -> Any:
    """Run all tests"""
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestExtremeValueTheory))
    suite.addTest(unittest.makeSuite(TestMLRiskModels))
    suite.addTest(unittest.makeSuite(TestParallelRiskEngine))
    suite.addTest(unittest.makeSuite(TestReportingFramework))
    suite.addTest(unittest.makeSuite(TestDashboardFramework))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    return result


if __name__ == "__main__":
    result = run_tests()
    logger.info("\nTest Summary:")
    logger.info(f"  Ran {result.testsRun} tests")
    logger.info(f"  Failures: {len(result.failures)}")
    logger.info(f"  Errors: {len(result.errors)}")
    sys.exit(len(result.failures) + len(result.errors))
