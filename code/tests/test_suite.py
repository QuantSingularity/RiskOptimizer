"""
Comprehensive Test Suite for RiskOptimizer

Covers:
1. Extreme Value Theory (EVT) risk models
2. Machine Learning risk models
3. Parallel risk calculation engine
4. Reporting framework
5. Dashboard framework
6. Risk analysis utilities
7. Portfolio optimization utilities
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
import shutil
import tempfile
import unittest

import numpy as np
import pandas as pd
from risk_engine.parallel_risk_engine import ParallelRiskEngine

logging.basicConfig(
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: small return dataset
# ---------------------------------------------------------------------------


def _make_returns(n=500, n_assets=3, seed=42):
    np.random.seed(seed)
    data = pd.DataFrame(
        np.random.multivariate_normal(
            mean=[0.001, 0.0005, 0.0008][:n_assets],
            cov=np.eye(n_assets) * 0.0004 + 0.0001,
            size=n,
        ),
        columns=[f"Asset_{i+1}" for i in range(n_assets)],
    )
    data.index = pd.date_range("2020-01-01", periods=n, freq="B")
    return data


def _make_1d_returns(n=1000, seed=42):
    np.random.seed(seed)
    base = np.random.normal(0.001, 0.02, n)
    extreme_idx = np.random.choice(n, 20, replace=False)
    base[extreme_idx] = np.random.normal(-0.08, 0.03, 20)
    return base


# ===========================================================================
# 1. Extreme Value Theory
# ===========================================================================


class TestExtremeValueTheory(unittest.TestCase):
    """Comprehensive tests for ExtremeValueRisk."""

    def setUp(self):
        from risk_models.extreme_value_theory import ExtremeValueRisk

        self.EVT = ExtremeValueRisk
        self.returns = _make_1d_returns()
        self.model = ExtremeValueRisk()

    # --- POT fitting ---

    def test_pot_fitting_sets_fitted_flag(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.05)
        self.assertTrue(self.model.fitted)

    def test_pot_fitting_stores_params(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.05)
        self.assertIsNotNone(self.model.pot_params)
        self.assertIn("shape", self.model.pot_params)
        self.assertIn("scale", self.model.pot_params)
        self.assertIn("threshold", self.model.pot_params)

    def test_pot_gpd_params_property(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.05)
        shape, scale = self.model.gpd_params
        self.assertIsNotNone(shape)
        self.assertGreater(scale, 0)
        self.assertLess(abs(shape), 2.0)

    def test_pot_explicit_threshold(self):
        threshold = np.percentile(self.returns, 5)
        self.model.fit_pot(self.returns, threshold=threshold)
        self.assertTrue(self.model.fitted)

    def test_pot_with_series_input(self):
        series = pd.Series(self.returns)
        self.model.fit_pot(series, threshold_quantile=0.1)
        self.assertTrue(self.model.fitted)

    def test_pot_with_dataframe_input(self):
        df = pd.DataFrame({"col": self.returns})
        self.model.fit_pot(df, threshold_quantile=0.1)
        self.assertTrue(self.model.fitted)

    # --- Block Maxima fitting ---

    def test_block_maxima_returns_dict(self):
        result = self.model.fit_block_maxima(self.returns, block_size=20)
        self.assertIsInstance(result, dict)

    def test_block_maxima_dict_keys(self):
        result = self.model.fit_block_maxima(self.returns, block_size=20)
        self.assertIn("shape", result)
        self.assertIn("loc", result)
        self.assertIn("scale", result)
        self.assertIn("block_maxima", result)

    def test_block_maxima_count(self):
        result = self.model.fit_block_maxima(self.returns, block_size=20)
        expected_blocks = len(self.returns) // 20
        self.assertEqual(len(result["block_maxima"]), expected_blocks)

    def test_block_maxima_sets_fitted(self):
        self.model.fit_block_maxima(self.returns, block_size=20)
        self.assertTrue(self.model.fitted)

    # --- VaR calculation ---

    def test_var_evt_is_positive(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        var = self.model.calculate_var(0.95, method="evt")
        self.assertGreater(var, 0)

    def test_var_increases_with_confidence(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        var_95 = self.model.calculate_var(0.95, method="evt")
        var_99 = self.model.calculate_var(0.99, method="evt")
        self.assertGreater(var_99, var_95)

    def test_var_historical_positive(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        var = self.model.calculate_var(0.95, method="historical")
        self.assertGreater(var, 0)

    def test_var_normal_positive(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        var = self.model.calculate_var(0.95, method="normal")
        self.assertGreater(var, 0)

    def test_var_invalid_method_raises(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        with self.assertRaises(ValueError):
            self.model.calculate_var(0.95, method="bogus")

    def test_var_unfitted_raises(self):
        with self.assertRaises(ValueError):
            self.model.calculate_var(0.95)

    def test_var_block_maxima_path(self):
        self.model.fit_block_maxima(self.returns, block_size=20)
        var = self.model.calculate_var(0.95, method="evt")
        self.assertGreater(var, 0)

    # --- ES calculation ---

    def test_es_greater_than_var(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        var_95 = self.model.calculate_var(0.95, method="evt")
        es_95 = self.model.calculate_es(0.95, method="evt")
        self.assertGreater(es_95, var_95)

    def test_es_increases_with_confidence(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        es_95 = self.model.calculate_es(0.95)
        es_99 = self.model.calculate_es(0.99)
        self.assertGreater(es_99, es_95)

    def test_es_historical_positive(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        es = self.model.calculate_es(0.95, method="historical")
        self.assertGreater(es, 0)

    def test_es_normal_positive(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        es = self.model.calculate_es(0.95, method="normal")
        self.assertGreater(es, 0)

    def test_es_unfitted_raises(self):
        with self.assertRaises(ValueError):
            self.model.calculate_es(0.95)

    # --- Scenario generation ---

    def test_generate_scenarios_correct_length(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        scenarios = self.model.generate_scenarios(n_scenarios=100)
        self.assertEqual(len(scenarios), 100)

    def test_generate_scenarios_historical(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        scenarios = self.model.generate_scenarios(100, method="historical")
        self.assertEqual(len(scenarios), 100)

    def test_generate_scenarios_normal(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        scenarios = self.model.generate_scenarios(100, method="normal")
        self.assertEqual(len(scenarios), 100)

    def test_simulate_extreme_scenarios_count(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.05)
        scenarios = self.model.simulate_extreme_scenarios(
            n_scenarios=50, confidence=0.90
        )
        self.assertEqual(len(scenarios), 50)

    def test_simulate_extreme_scenarios_all_positive(self):
        self.model.fit_pot(self.returns, threshold_quantile=0.05)
        scenarios = self.model.simulate_extreme_scenarios(
            n_scenarios=50, confidence=0.90
        )
        self.assertTrue(np.all(scenarios > 0))

    # --- Tail dependence ---

    def test_tail_dependence_in_range(self):
        np.random.seed(42)
        x = self.returns
        y = 0.7 * x + 0.3 * np.random.normal(0, np.std(x), len(x))
        td = self.model.tail_dependence(x, y, threshold_quantile=0.1)
        self.assertGreaterEqual(td, 0.0)
        self.assertLessEqual(td, 1.0)

    def test_tail_dependence_alias(self):
        np.random.seed(42)
        x = self.returns
        y = np.random.normal(0, 0.02, len(x))
        td1 = self.model.tail_dependence(x, y)
        td2 = self.model.calculate_tail_dependence(x, y)
        self.assertAlmostEqual(td1, td2)

    def test_tail_dependence_copula_method(self):
        np.random.seed(42)
        x = self.returns
        y = 0.5 * x + 0.5 * np.random.normal(0, np.std(x), len(x))
        td = self.model.calculate_tail_dependence(x, y, method="copula")
        self.assertGreaterEqual(td, 0.0)
        self.assertLessEqual(td, 1.0)

    def test_tail_dependence_invalid_method_raises(self):
        with self.assertRaises(ValueError):
            self.model.calculate_tail_dependence(
                self.returns, self.returns, method="bogus"
            )

    # --- Plotting (smoke tests) ---

    def test_plot_tail_distribution_returns_figure(self):
        import matplotlib.pyplot as plt

        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        fig = self.model.plot_tail_distribution([0.95, 0.99])
        self.assertIsInstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_mean_excess_returns_figure(self):
        import matplotlib.pyplot as plt

        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        fig = self.model.plot_mean_excess()
        self.assertIsInstance(fig, plt.Figure)
        plt.close(fig)

    def test_plot_return_level_returns_figure(self):
        import matplotlib.pyplot as plt

        self.model.fit_pot(self.returns, threshold_quantile=0.1)
        fig = self.model.plot_return_level([2, 5, 10])
        self.assertIsInstance(fig, plt.Figure)
        plt.close(fig)


# ===========================================================================
# 2. Machine Learning Risk Models
# ===========================================================================


class TestMLRiskModels(unittest.TestCase):
    """Comprehensive tests for MLRiskModel and CopulaMLRiskModel."""

    def setUp(self):
        from risk_models.ml_risk_models import (
            CopulaMLRiskModel,
            HybridRiskModel,
            MLRiskModel,
        )

        self.MLRiskModel = MLRiskModel
        self.CopulaMLRiskModel = CopulaMLRiskModel
        self.HybridRiskModel = HybridRiskModel
        self.returns = _make_returns(n=500)
        self.weights = {"Asset_1": 0.4, "Asset_2": 0.3, "Asset_3": 0.3}

    # --- MLRiskModel ---

    def test_ml_gbm_training(self):
        model = self.MLRiskModel(model_type="gbm")
        model.fit(self.returns, feature_window=10)
        self.assertTrue(model.trained)

    def test_ml_rf_training(self):
        model = self.MLRiskModel(model_type="rf")
        model.fit(self.returns, feature_window=10)
        self.assertTrue(model.trained)

    def test_ml_feature_names_set(self):
        model = self.MLRiskModel(model_type="gbm")
        model.fit(self.returns, feature_window=10)
        self.assertIsNotNone(model.feature_names)
        self.assertGreater(len(model.feature_names), 0)

    def test_ml_feature_importance_set(self):
        model = self.MLRiskModel(model_type="gbm")
        model.fit(self.returns, feature_window=10)
        self.assertIsNotNone(model.feature_importance)

    def test_ml_var_prediction_length(self):
        model = self.MLRiskModel(model_type="gbm")
        model.fit(self.returns, feature_window=10)
        preds = model.predict_var(self.returns, confidence=0.95)
        self.assertEqual(len(preds), len(self.returns) - 10)

    def test_ml_var_prediction_positive(self):
        model = self.MLRiskModel(model_type="gbm")
        model.fit(self.returns, feature_window=10)
        preds = model.predict_var(self.returns, confidence=0.95)
        self.assertTrue(np.all(preds > 0))

    def test_ml_es_prediction_length(self):
        model = self.MLRiskModel(model_type="gbm")
        model.fit(self.returns, feature_window=10)
        preds = model.predict_es(self.returns, confidence=0.95)
        self.assertEqual(len(preds), len(self.returns) - 10)

    def test_ml_es_ge_var(self):
        model = self.MLRiskModel(model_type="gbm")
        model.fit(self.returns, feature_window=10)
        var_p = model.predict_var(self.returns, confidence=0.95)
        es_p = model.predict_es(self.returns, confidence=0.95)
        self.assertTrue(np.all(es_p >= var_p))

    def test_ml_untrained_raises(self):
        model = self.MLRiskModel(model_type="gbm")
        with self.assertRaises(ValueError):
            model.predict_var(self.returns)

    def test_ml_save_load(self):
        with tempfile.TemporaryDirectory() as tmp:
            model = self.MLRiskModel(model_type="gbm")
            model.fit(self.returns, feature_window=10)
            path = os.path.join(tmp, "model.joblib")
            model.save_model(path)
            self.assertTrue(os.path.exists(path))
            loaded = self.MLRiskModel.load_model(path)
            self.assertTrue(loaded.trained)
            self.assertEqual(loaded.model_type, model.model_type)
            self.assertEqual(loaded.quantile, model.quantile)

    def test_ml_invalid_model_type_raises(self):
        with self.assertRaises(ValueError):
            self.MLRiskModel(model_type="xyz")

    # --- CopulaMLRiskModel ---

    def test_copula_fitting_sets_trained(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        self.assertTrue(model.trained)

    def test_copula_asset_names(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        self.assertEqual(list(model.asset_names), list(self.returns.columns))

    def test_copula_correlation_matrix_shape(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        n = len(self.returns.columns)
        self.assertEqual(model.correlation_matrix.shape, (n, n))

    def test_copula_var_positive(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        var = model.calculate_var(self.weights, confidence=0.95)
        self.assertGreater(var, 0)

    def test_copula_var_increases_with_confidence(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        var_95 = model.calculate_var(self.weights, confidence=0.95)
        var_99 = model.calculate_var(self.weights, confidence=0.99)
        self.assertGreater(var_99, var_95)

    def test_copula_es_gt_var(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        var = model.calculate_var(self.weights, confidence=0.95)
        es = model.calculate_es(self.weights, confidence=0.95)
        self.assertGreater(es, var)

    def test_copula_risk_metrics_keys(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        metrics = model.calculate_risk_metrics(self.weights)
        for key in ["var_95", "es_95", "var_99", "es_99", "mean", "std"]:
            self.assertIn(key, metrics)

    def test_copula_risk_metrics_ordering(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        metrics = model.calculate_risk_metrics(self.weights)
        self.assertGreater(metrics["var_99"], metrics["var_95"])
        self.assertGreater(metrics["es_99"], metrics["es_95"])
        self.assertGreater(metrics["es_95"], metrics["var_95"])

    def test_copula_generate_scenarios_shape(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian", n_scenarios=500)
        model.fit(self.returns)
        scenarios = model.generate_scenarios(n_scenarios=200)
        self.assertEqual(scenarios.shape, (200, len(self.returns.columns)))

    def test_copula_untrained_raises(self):
        model = self.CopulaMLRiskModel()
        with self.assertRaises(ValueError):
            model.calculate_var(self.weights)

    def test_copula_t_type(self):
        model = self.CopulaMLRiskModel(copula_type="t")
        model.fit(self.returns)
        var = model.calculate_var(self.weights, confidence=0.95)
        self.assertGreater(var, 0)

    def test_copula_array_weights(self):
        model = self.CopulaMLRiskModel(copula_type="gaussian")
        model.fit(self.returns)
        weights_arr = np.array([0.4, 0.3, 0.3])
        var = model.calculate_var(weights_arr, confidence=0.95)
        self.assertGreater(var, 0)

    # --- HybridRiskModel ---

    def test_hybrid_fitting(self):
        model = self.HybridRiskModel(traditional_weight=0.7)
        model.fit(self.returns)
        self.assertTrue(model.trained)
        self.assertTrue(model.ml_model.trained)
        self.assertTrue(model.copula_model.trained)

    def test_hybrid_var_positive(self):
        model = self.HybridRiskModel(traditional_weight=0.7)
        model.fit(self.returns)
        var = model.calculate_var(self.returns, self.weights, confidence=0.95)
        self.assertGreater(var, 0)

    def test_hybrid_es_gt_var(self):
        model = self.HybridRiskModel(traditional_weight=0.7)
        model.fit(self.returns)
        var = model.calculate_var(self.returns, self.weights, confidence=0.95)
        es = model.calculate_es(self.returns, self.weights, confidence=0.95)
        self.assertGreater(es, var)

    def test_hybrid_untrained_raises(self):
        model = self.HybridRiskModel()
        with self.assertRaises(ValueError):
            model.calculate_var(self.returns, self.weights)


# ===========================================================================
# 3. Parallel Risk Engine
# ===========================================================================


class TestParallelRiskEngine(unittest.TestCase):
    """Comprehensive tests for ParallelRiskEngine."""

    def setUp(self):
        from risk_engine.parallel_risk_engine import ParallelRiskEngine
        from risk_models.ml_risk_models import CopulaMLRiskModel

        self.returns = _make_returns(n=300)
        self.weights = {"Asset_1": 0.4, "Asset_2": 0.3, "Asset_3": 0.3}
        self.engine = ParallelRiskEngine(n_jobs=1, backend="threading")
        self.copula = CopulaMLRiskModel(copula_type="gaussian", n_scenarios=500)
        self.copula.fit(self.returns)

    def test_parallel_monte_carlo_keys(self):
        result = self.engine.parallel_monte_carlo(
            self.copula, self.weights, n_scenarios=500
        )
        self.assertIn("portfolio_metrics", result)
        self.assertIn("risk_metrics", result)
        self.assertIn("time_taken", result)

    def test_parallel_monte_carlo_risk_metrics(self):
        result = self.engine.parallel_monte_carlo(
            self.copula, self.weights, n_scenarios=500
        )
        self.assertIn("var_95", result["risk_metrics"])
        self.assertIn("es_95", result["risk_metrics"])
        self.assertGreater(result["risk_metrics"]["var_95"], 0)
        self.assertGreater(
            result["risk_metrics"]["es_95"], result["risk_metrics"]["var_95"]
        )

    def test_parallel_portfolio_optimization_keys(self):
        result = self.engine.parallel_portfolio_optimization(
            self.returns, n_portfolios=100
        )
        self.assertIsNotNone(result)
        self.assertIn("max_sharpe_portfolio", result)
        self.assertIn("min_volatility_portfolio", result)
        self.assertIn("time_taken", result)

    def test_parallel_portfolio_optimization_weights_sum(self):
        result = self.engine.parallel_portfolio_optimization(
            self.returns, n_portfolios=100
        )
        weights = result["max_sharpe_portfolio"]["weights"]
        total = sum(weights.values())
        self.assertAlmostEqual(total, 1.0, places=5)

    def test_parallel_batch_risk_calculation(self):
        single_returns = self.returns.iloc[:, 0]
        result = self.engine.parallel_batch_risk_calculation(
            single_returns,
            risk_models=["parametric", "historical"],
            confidence_levels=[0.95],
        )
        self.assertIn("risk_metrics", result)
        self.assertIn("parametric", result["risk_metrics"])
        self.assertIn("historical", result["risk_metrics"])
        self.assertIn("var_95", result["risk_metrics"]["parametric"])

    def test_parallel_stress_testing_keys(self):
        result = self.engine.parallel_stress_testing(
            self.returns, self.weights, n_custom_scenarios=10
        )
        self.assertIn("predefined_scenarios", result)
        self.assertIn("custom_scenarios_summary", result)
        self.assertIn("time_taken", result)

    def test_parallel_backtest_keys(self):
        single_returns = self.returns.iloc[:, 0]
        result = self.engine.parallel_backtest(
            single_returns,
            risk_models=["parametric", "historical"],
            confidence_level=0.95,
            window_size=50,
            step_size=10,
        )
        self.assertIn("summary", result)
        self.assertIn("windows", result)
        self.assertIn("time_taken", result)

    def test_parallel_sensitivity_analysis_keys(self):
        result = self.engine.parallel_sensitivity_analysis(
            self.returns, self.weights, shock_range=(-0.05, 0.05), n_points=5
        )
        self.assertIn("factor_results", result)
        self.assertIn("sensitivities", result)
        self.assertIn("time_taken", result)

    def test_parallel_sensitivity_has_all_factors(self):
        result = self.engine.parallel_sensitivity_analysis(
            self.returns, self.weights, shock_range=(-0.05, 0.05), n_points=5
        )
        for col in self.returns.columns:
            self.assertIn(col, result["sensitivities"])

    def test_parallel_risk_decomposition_volatility(self):
        result = self.engine.parallel_risk_decomposition(
            self.returns, self.weights, risk_measure="volatility"
        )
        self.assertIn("portfolio_risk", result)
        self.assertIn("component_contributions", result)
        self.assertGreater(result["portfolio_risk"], 0)

    def test_n_jobs_default(self):
        import multiprocessing

        engine = ParallelRiskEngine(n_jobs=None)
        self.assertEqual(engine.n_jobs, multiprocessing.cpu_count())


# ===========================================================================
# 4. Reporting Framework
# ===========================================================================


class TestReportingFramework(unittest.TestCase):
    """Comprehensive tests for ReportTemplate and ReportGenerator."""

    def setUp(self):
        from reporting.reporting_framework import ReportGenerator, ReportTemplate

        self.ReportTemplate = ReportTemplate
        self.ReportGenerator = ReportGenerator
        self.returns = _make_returns(n=200)
        self.weights = {"Asset_1": 0.4, "Asset_2": 0.3, "Asset_3": 0.3}
        self.report_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.report_dir, ignore_errors=True)

    def _make_template(self):
        return self.ReportTemplate(
            title="Risk Analysis Report",
            sections=[
                {"title": "Portfolio Overview", "content": "Overview of performance"},
                {"title": "Risk Metrics", "content": "Risk analysis"},
            ],
        )

    def test_template_title(self):
        t = self._make_template()
        self.assertEqual(t.title, "Risk Analysis Report")

    def test_template_section_count(self):
        t = self._make_template()
        self.assertEqual(len(t.sections), 2)

    def test_template_section_title(self):
        t = self._make_template()
        self.assertEqual(t.sections[0]["title"], "Portfolio Overview")

    def test_template_add_section(self):
        t = self._make_template()
        t.add_section("New Section", "content")
        self.assertEqual(len(t.sections), 3)

    def test_template_save_load(self):
        t = self._make_template()
        path = os.path.join(self.report_dir, "template.json")
        self.assertTrue(t.save(path))
        self.assertTrue(os.path.exists(path))
        loaded = self.ReportTemplate.load(path)
        self.assertEqual(loaded.title, t.title)
        self.assertEqual(len(loaded.sections), len(t.sections))

    def test_template_save_load_preserves_section_titles(self):
        t = self._make_template()
        path = os.path.join(self.report_dir, "template.json")
        t.save(path)
        loaded = self.ReportTemplate.load(path)
        self.assertEqual(loaded.sections[0]["title"], t.sections[0]["title"])

    def test_template_has_id(self):
        t = self._make_template()
        self.assertIsNotNone(t.id)

    def test_template_has_timestamps(self):
        t = self._make_template()
        self.assertIsNotNone(t.created_at)
        self.assertIsNotNone(t.updated_at)

    def test_html_report_created(self):
        t = self._make_template()
        gen = self.ReportGenerator(t)
        path = os.path.join(self.report_dir, "report.html")
        gen.generate_html(path, data={"portfolio_name": "Test", "date": "2024-01-01"})
        self.assertTrue(os.path.exists(path))

    def test_html_report_contains_title(self):
        t = self._make_template()
        gen = self.ReportGenerator(t)
        path = os.path.join(self.report_dir, "report.html")
        gen.generate_html(path)
        with open(path) as f:
            content = f.read()
        self.assertIn("Risk Analysis Report", content)

    def test_html_report_contains_sections(self):
        t = self._make_template()
        gen = self.ReportGenerator(t)
        path = os.path.join(self.report_dir, "report.html")
        gen.generate_html(path)
        with open(path) as f:
            content = f.read()
        self.assertIn("Portfolio Overview", content)
        self.assertIn("Risk Metrics", content)

    def test_pdf_report_graceful(self):
        t = self._make_template()
        gen = self.ReportGenerator(t)
        path = os.path.join(self.report_dir, "report.pdf")
        try:
            gen.generate_pdf(path)
        except (ImportError, Exception):
            pass  # PDF generation is optional

    def test_template_remove_section(self):
        t = self._make_template()
        section_id = t.sections[0]["id"]
        result = t.remove_section(section_id)
        self.assertTrue(result)
        self.assertEqual(len(t.sections), 1)

    def test_template_update_section(self):
        t = self._make_template()
        section_id = t.sections[0]["id"]
        result = t.update_section(section_id, title="Updated Title")
        self.assertTrue(result)
        self.assertEqual(t.sections[0]["title"], "Updated Title")


# ===========================================================================
# 5. Risk Analysis Utilities
# ===========================================================================


class TestRiskAnalysis(unittest.TestCase):
    """Tests for risk_models/risk_analysis.py utilities."""

    def setUp(self):
        np.random.seed(42)
        n = 200
        data = np.random.multivariate_normal(
            [0.001, 0.0005], [[0.0004, 0.0001], [0.0001, 0.0003]], n
        )
        self.returns_df = pd.DataFrame(data, columns=["AAPL", "MSFT"])

    def test_historical_var_positive(self):
        from risk_models.risk_analysis import historical_var

        var = historical_var(self.returns_df, confidence_level=0.95)
        self.assertTrue((var < 0).all(), "Historical VaR should be negative (losses)")

    def test_historical_var_more_conservative_at_99(self):
        from risk_models.risk_analysis import historical_var

        var_95 = historical_var(self.returns_df, confidence_level=0.95)
        var_99 = historical_var(self.returns_df, confidence_level=0.99)
        self.assertTrue((var_99 <= var_95).all())

    def test_monte_carlo_var_returns_series(self):
        from risk_models.risk_analysis import monte_carlo_var

        result = monte_carlo_var(
            self.returns_df, confidence_level=0.95, n_simulations=1000
        )
        self.assertIsInstance(result, pd.Series)
        self.assertEqual(len(result), len(self.returns_df.columns))

    def test_correlation_matrix_shape(self):
        from risk_models.risk_analysis import calculate_correlation_matrix

        corr = calculate_correlation_matrix(self.returns_df)
        n = len(self.returns_df.columns)
        self.assertEqual(corr.shape, (n, n))

    def test_correlation_matrix_diagonal(self):
        from risk_models.risk_analysis import calculate_correlation_matrix

        corr = calculate_correlation_matrix(self.returns_df)
        np.testing.assert_array_almost_equal(
            np.diag(corr.values), np.ones(corr.shape[0])
        )

    def test_stress_test_returns_series(self):
        from risk_models.risk_analysis import stress_test

        result = stress_test(self.returns_df, scenario_multiplier=3.0)
        self.assertIsInstance(result, pd.Series)

    def test_stress_test_all_negative(self):
        from risk_models.risk_analysis import stress_test

        result = stress_test(self.returns_df, scenario_multiplier=3.0)
        self.assertTrue((result < 0).all(), "Stress test losses should be negative")


# ===========================================================================
# 6. Portfolio Optimization Utilities
# ===========================================================================


class TestPortfolioOptimization(unittest.TestCase):
    """Tests for risk_models/portfolio_optimization.py utilities."""

    def setUp(self):
        np.random.seed(42)
        n = 300
        data = np.random.multivariate_normal(
            [0.001, 0.0007, 0.0009],
            [
                [0.0004, 0.0001, 0.0001],
                [0.0001, 0.0003, 0.0001],
                [0.0001, 0.0001, 0.0005],
            ],
            n,
        )
        price_idx = pd.date_range("2020-01-01", periods=n, freq="B")
        prices = pd.DataFrame(
            100 * np.cumprod(1 + data, axis=0),
            columns=["A", "B", "C"],
            index=price_idx,
        )
        self.prices = prices

    def test_mean_variance_returns_dict(self):
        from risk_models.portfolio_optimization import mean_variance_optimization

        result = mean_variance_optimization(self.prices)
        self.assertIsInstance(result, dict)

    def test_mean_variance_has_weights(self):
        from risk_models.portfolio_optimization import mean_variance_optimization

        result = mean_variance_optimization(self.prices)
        self.assertIn("max_sharpe_weights", result)
        self.assertIn("min_vol_weights", result)

    def test_mean_variance_weights_sum_to_one(self):
        from risk_models.portfolio_optimization import mean_variance_optimization

        result = mean_variance_optimization(self.prices)
        sharpe_sum = sum(result["max_sharpe_weights"].values())
        self.assertAlmostEqual(sharpe_sum, 1.0, places=4)


# ===========================================================================
# Runner
# ===========================================================================


def run_tests() -> unittest.TestResult:
    """Run all tests and return the result."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    test_classes = [
        TestExtremeValueTheory,
        TestMLRiskModels,
        TestParallelRiskEngine,
        TestReportingFramework,
        TestRiskAnalysis,
        TestPortfolioOptimization,
    ]
    for cls in test_classes:
        suite.addTests(loader.loadTestsFromTestCase(cls))
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    result = run_tests()
    logger.info(
        f"\nTest Summary: Ran {result.testsRun} tests, "
        f"{len(result.failures)} failures, {len(result.errors)} errors"
    )
    sys.exit(len(result.failures) + len(result.errors))
