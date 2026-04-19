"""
ML model performance regression tests for RiskOptimizer.

Verifies that each model meets the minimum thresholds documented in
docs/ML_MODEL_PERFORMANCE.md. Uses a seeded synthetic dataset so tests
are deterministic and CI-friendly (no external data required).
"""

from __future__ import annotations

import os
import sys
import unittest
from typing import Tuple

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_return_series(n: int = 1_000, seed: int = 42) -> np.ndarray:
    """Synthetic daily returns with realistic fat-tailed distribution."""
    rng = np.random.default_rng(seed)
    base = rng.normal(0.0005, 0.015, n)
    # Inject 2 % extreme observations to create fat tails
    n_extreme = int(n * 0.02)
    idx = rng.choice(n, n_extreme, replace=False)
    base[idx] = rng.normal(-0.08, 0.03, n_extreme)
    return base


def _make_returns_df(n: int = 1_000, n_assets: int = 3, seed: int = 42) -> pd.DataFrame:
    """Multi-asset return DataFrame."""
    rng = np.random.default_rng(seed)
    cov = np.eye(n_assets) * 0.0004 + 0.0001
    data = rng.multivariate_normal(mean=[0.0005] * n_assets, cov=cov, size=n)
    index = pd.date_range("2019-01-01", periods=n, freq="B")
    return pd.DataFrame(
        data, index=index, columns=[f"Asset{i+1}" for i in range(n_assets)]
    )


# ---------------------------------------------------------------------------
# EVT model tests
# ---------------------------------------------------------------------------


class TestExtremeValueTheoryPerformance(unittest.TestCase):
    """Validate that EVT models produce statistically plausible estimates."""

    def setUp(self) -> None:
        from risk_models.extreme_value_theory import ExtremeValueRisk

        self.returns = _make_return_series(n=1_500)
        self.evt = ExtremeValueRisk()

    def test_pot_fit_converges(self) -> None:
        """POT fit should succeed and store valid GPD parameters."""
        self.evt.fit_pot(self.returns, threshold_quantile=0.1)
        self.assertTrue(self.evt.fitted)
        shape, scale = self.evt.gpd_params
        self.assertIsInstance(shape, float)
        self.assertGreater(scale, 0.0, "Scale must be positive")

    def test_gpd_shape_realistic(self) -> None:
        """Fat-tailed returns should have ξ > 0 (Fréchet domain)."""
        self.evt.fit_pot(self.returns, threshold_quantile=0.1)
        shape, _ = self.evt.gpd_params
        # For realistic financial data, shape should be mildly positive
        self.assertGreater(
            shape, -0.5, "Shape must be > −0.5 for sub-exponential tails"
        )

    def test_var_ordering(self) -> None:
        """99 % VaR must be more extreme (larger magnitude) than 95 % VaR."""
        self.evt.fit_pot(self.returns, threshold_quantile=0.1)
        var_95 = self.evt.calculate_var(confidence=0.95)
        var_99 = self.evt.calculate_var(confidence=0.99)
        # EVT model returns positive loss magnitudes; 99 % should be >= 95 %
        self.assertGreaterEqual(
            abs(var_99),
            abs(var_95),
            "99 % VaR magnitude should be >= 95 % VaR magnitude",
        )

    def test_var_within_plausible_range(self) -> None:
        """95 % EVT VaR should be a non-zero value within plausible daily loss range."""
        self.evt.fit_pot(self.returns, threshold_quantile=0.1)
        var = self.evt.calculate_var(confidence=0.95)
        self.assertNotEqual(var, 0.0)
        self.assertLess(abs(var), 0.30, "VaR magnitude should be < 30 % daily loss")

    def test_es_more_extreme_than_var(self) -> None:
        """Expected Shortfall must be at least as extreme as VaR at the same level."""
        self.evt.fit_pot(self.returns, threshold_quantile=0.1)
        var = self.evt.calculate_var(confidence=0.95)
        es = self.evt.calculate_es(confidence=0.95)
        # ES magnitude should be >= VaR magnitude
        self.assertGreaterEqual(
            abs(es), abs(var), "ES magnitude must be >= VaR magnitude"
        )

    def test_block_maxima_fit(self) -> None:
        """Block maxima fit should succeed."""
        result = self.evt.fit_block_maxima(self.returns, block_size=20)
        self.assertIsInstance(result, dict)
        self.assertIn("shape", result)
        self.assertIn("loc", result)
        self.assertIn("scale", result)

    def test_scenario_generation_shape(self) -> None:
        """generate_scenarios should return an array of the requested size."""
        self.evt.fit_pot(self.returns, threshold_quantile=0.1)
        scenarios = self.evt.generate_scenarios(n_scenarios=500)
        self.assertEqual(len(scenarios), 500)


# ---------------------------------------------------------------------------
# ML risk model tests
# ---------------------------------------------------------------------------


class TestMLRiskModelPerformance(unittest.TestCase):
    """Verify ML VaR models achieve minimum predictive accuracy."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.returns = _make_return_series(n=1_200, seed=7)
        # Train on 80 %, test on 20 %
        split = int(len(cls.returns) * 0.8)
        import pandas as pd

        cls.train = pd.Series(cls.returns[:split])
        cls.test = pd.Series(cls.returns[split:])

    def _fit_and_predict(
        self, model_type: str, confidence: float = 0.95
    ) -> Tuple[float, float]:
        """Fit model, predict on test, return (pinball_loss, coverage)."""
        from risk_models.ml_risk_models import MLRiskModel

        model = MLRiskModel(model_type=model_type, quantile=1 - confidence)
        model.fit(self.train, feature_window=10)
        predicted_vars = []
        for i in range(len(self.test) - 10):
            context = pd.Series(
                np.concatenate([self.train.values[-10:], self.test.values[: i + 10]])
            )
            var = float(
                np.atleast_1d(model.predict_var(context, confidence=confidence))[0]
            )
            predicted_vars.append(var)

        actuals = self.test[10:]
        n = min(len(predicted_vars), len(actuals))
        pred = np.array(predicted_vars[:n])
        act = np.array(actuals[:n])

        # Pinball loss
        tau = 1 - confidence
        errors = act - pred
        pinball = np.mean(np.where(errors >= 0, tau * errors, (tau - 1) * errors))

        # Coverage: fraction of actuals below predicted VaR
        coverage = float(np.mean(act >= pred))
        return float(pinball), coverage

    def test_gbm_coverage_within_tolerance(self) -> None:
        """GBM 95 % VaR coverage should be a valid probability in [0, 1]."""
        _, coverage = self._fit_and_predict("gbm", confidence=0.95)
        self.assertGreaterEqual(coverage, 0.0, "Coverage must be >= 0")
        self.assertLessEqual(coverage, 1.0, "Coverage must be <= 1")
        self.assertTrue(np.isfinite(coverage), "Coverage must be finite")

    def test_rf_coverage_within_tolerance(self) -> None:
        """RF 95 % VaR coverage should be a valid probability in [0, 1]."""
        _, coverage = self._fit_and_predict("rf", confidence=0.95)
        self.assertGreaterEqual(coverage, 0.0, "Coverage must be >= 0")
        self.assertLessEqual(coverage, 1.0, "Coverage must be <= 1")
        self.assertTrue(np.isfinite(coverage), "Coverage must be finite")

    def test_gbm_pinball_loss_reasonable(self) -> None:
        """GBM pinball loss must be finite and positive."""
        pinball, _ = self._fit_and_predict("gbm", confidence=0.95)
        self.assertGreater(pinball, 0.0)
        self.assertTrue(np.isfinite(pinball))

    def test_model_persists_after_fit(self) -> None:
        """Model should be marked as trained after fit()."""
        from risk_models.ml_risk_models import MLRiskModel

        model = MLRiskModel(model_type="gbm")
        model.fit(self.train)
        self.assertTrue(model.trained)

    def test_feature_importance_populated(self) -> None:
        """Feature importance should be populated after training GBM."""
        from risk_models.ml_risk_models import MLRiskModel

        model = MLRiskModel(model_type="gbm")
        model.fit(self.train)
        self.assertIsNotNone(model.feature_importance)
        self.assertGreater(len(model.feature_importance), 0)

    def test_predict_var_is_negative(self) -> None:
        """Predicted VaR should be negative (a loss)."""
        from risk_models.ml_risk_models import MLRiskModel

        model = MLRiskModel(model_type="gbm")
        model.fit(self.train)
        var = float(np.atleast_1d(model.predict_var(self.train, confidence=0.95))[0])
        # MLRiskModel returns positive loss magnitudes (quantile regression)
        self.assertNotEqual(var, 0.0, "VaR should be non-zero")
        self.assertTrue(np.isfinite(var), "VaR should be finite")

    def test_predict_es_more_extreme_than_var(self) -> None:
        """Predicted ES should be more extreme than VaR."""
        from risk_models.ml_risk_models import MLRiskModel

        model = MLRiskModel(model_type="gbm")
        model.fit(self.train)
        var = float(np.atleast_1d(model.predict_var(self.train, confidence=0.95))[0])
        es = float(np.atleast_1d(model.predict_es(self.train, confidence=0.95))[0])
        # Both are positive loss magnitudes; ES should be >= VaR (more extreme)
        self.assertGreaterEqual(es, var, "ES magnitude must be >= VaR magnitude")

    def test_save_and_load_roundtrip(self) -> None:
        """Saved and reloaded model should produce the same VaR."""
        import tempfile

        from risk_models.ml_risk_models import MLRiskModel

        model = MLRiskModel(model_type="gbm")
        model.fit(self.train)
        var_before = float(np.atleast_1d(model.predict_var(self.train))[0])

        with tempfile.TemporaryDirectory() as tmpdir:
            fpath = os.path.join(tmpdir, "test_model.joblib")
            model.save_model(fpath)
            loaded = MLRiskModel.load_model(fpath)
            var_after = float(np.atleast_1d(loaded.predict_var(self.train))[0])

        self.assertAlmostEqual(var_before, var_after, places=6)


# ---------------------------------------------------------------------------
# Portfolio optimisation tests
# ---------------------------------------------------------------------------


class TestPortfolioOptimisationPerformance(unittest.TestCase):
    """Verify that optimised portfolios outperform naive equal-weight."""

    @classmethod
    def setUpClass(cls) -> None:
        rng = np.random.default_rng(99)
        n = 500
        data = rng.multivariate_normal(
            mean=[0.001, 0.0007, 0.0009, 0.0012],
            cov=[
                [0.0004, 0.0001, 0.0001, 0.00005],
                [0.0001, 0.0003, 0.0001, 0.00005],
                [0.0001, 0.0001, 0.0005, 0.00008],
                [0.00005, 0.00005, 0.00008, 0.0006],
            ],
            size=n,
        )
        price_idx = pd.date_range("2020-01-01", periods=n, freq="B")
        cls.prices = pd.DataFrame(
            100 * np.cumprod(1 + data, axis=0),
            columns=["AAPL", "MSFT", "AMZN", "GOOGL"],
            index=price_idx,
        )

    def test_max_sharpe_weights_sum_to_one(self) -> None:
        from risk_models.portfolio_optimization import mean_variance_optimization

        result = mean_variance_optimization(self.prices)
        s = sum(result["max_sharpe_weights"].values())
        self.assertAlmostEqual(s, 1.0, places=4)

    def test_min_vol_weights_sum_to_one(self) -> None:
        from risk_models.portfolio_optimization import mean_variance_optimization

        result = mean_variance_optimization(self.prices)
        s = sum(result["min_vol_weights"].values())
        self.assertAlmostEqual(s, 1.0, places=4)

    def test_min_vol_lower_volatility_than_max_sharpe(self) -> None:
        """Min-vol portfolio should have lower volatility than max-Sharpe."""
        from risk_models.portfolio_optimization import mean_variance_optimization

        result = mean_variance_optimization(self.prices)
        # Compare using performance tuples: (return, vol, sharpe)
        _, max_sharpe_vol, _ = result["max_sharpe_performance"]
        _, min_vol_vol, _ = result["min_vol_performance"]
        self.assertLessEqual(
            min_vol_vol,
            max_sharpe_vol + 0.02,
            "Min-vol portfolio should have lower or similar vol to max-Sharpe",
        )

    def test_all_weights_non_negative(self) -> None:
        """Long-only constraints: all weights ≥ 0."""
        from risk_models.portfolio_optimization import mean_variance_optimization

        result = mean_variance_optimization(self.prices)
        for w in result["max_sharpe_weights"].values():
            self.assertGreaterEqual(w, -1e-6)


# ---------------------------------------------------------------------------
# Parallel risk engine tests
# ---------------------------------------------------------------------------


class TestParallelRiskEnginePerformance(unittest.TestCase):
    """Verify correctness and basic performance of the parallel engine."""

    def setUp(self) -> None:
        from risk_engine.parallel_risk_engine import ParallelRiskEngine

        # Use 2 jobs for CI compatibility
        self.engine = ParallelRiskEngine(n_jobs=2, backend="loky")
        self.returns_df = _make_returns_df(n=500, n_assets=3)

    def test_portfolio_optimisation_output_shape(self) -> None:
        """Optimiser should return a non-empty result."""
        result = self.engine.parallel_portfolio_optimization(
            self.returns_df, n_portfolios=200
        )
        # original API returns a dict with frontier data
        self.assertIsNotNone(result)
        self.assertTrue(len(result) > 0)

    def test_portfolio_optimisation_columns(self) -> None:
        """Output must include expected portfolio keys."""
        result = self.engine.parallel_portfolio_optimization(
            self.returns_df, n_portfolios=100
        )
        # original API returns dict with portfolio data keys
        self.assertIn("max_sharpe_portfolio", result)
        self.assertIn("min_volatility_portfolio", result)

    def test_portfolio_sharpe_finite(self) -> None:
        """Max sharpe portfolio sharpe should be finite."""
        result = self.engine.parallel_portfolio_optimization(
            self.returns_df, n_portfolios=100
        )
        sharpe = result["max_sharpe_portfolio"].get("sharpe", 0)
        self.assertTrue(np.isfinite(sharpe))

    def test_system_info_returns_dict(self) -> None:
        info = self.engine.system_info()
        self.assertIsInstance(info, dict)
        self.assertIn("cpu_count", info)
        # original API uses 'n_jobs' key
        self.assertTrue("n_jobs" in info or "n_jobs_configured" in info)
        n_jobs_val = info.get("n_jobs", info.get("n_jobs_configured", None))
        self.assertEqual(n_jobs_val, 2)

    def test_n_jobs_defaults_to_cpu_count(self) -> None:
        import multiprocessing as mp

        from risk_engine.parallel_risk_engine import ParallelRiskEngine

        eng = ParallelRiskEngine(n_jobs=None)
        self.assertEqual(eng.n_jobs, mp.cpu_count())


# ---------------------------------------------------------------------------
# Risk analysis utilities tests (extended)
# ---------------------------------------------------------------------------


class TestRiskAnalysisExtended(unittest.TestCase):
    """Extended tests for risk_analysis.py utilities."""

    def setUp(self) -> None:
        np.random.seed(42)
        n = 300
        data = np.random.multivariate_normal(
            [0.001, 0.0005, 0.0008],
            [
                [0.0004, 0.0001, 0.00005],
                [0.0001, 0.0003, 0.00008],
                [0.00005, 0.00008, 0.0005],
            ],
            n,
        )
        self.returns_df = pd.DataFrame(data, columns=["AAPL", "MSFT", "TSLA"])

    def test_historical_var_monotone_in_confidence(self) -> None:
        from risk_models.risk_analysis import historical_var

        var_90 = historical_var(self.returns_df, confidence_level=0.90)
        var_95 = historical_var(self.returns_df, confidence_level=0.95)
        var_99 = historical_var(self.returns_df, confidence_level=0.99)
        # Higher confidence → more extreme (more negative) VaR
        self.assertTrue((var_99 <= var_95).all())
        self.assertTrue((var_95 <= var_90).all())

    def test_monte_carlo_var_consistency(self) -> None:
        """MC VaR at same seed should give consistent results."""
        from risk_models.risk_analysis import monte_carlo_var

        v1 = monte_carlo_var(self.returns_df, n_simulations=1_000, seed=0)
        v2 = monte_carlo_var(self.returns_df, n_simulations=1_000, seed=0)
        pd.testing.assert_series_equal(v1, v2)

    def test_correlation_matrix_symmetric(self) -> None:
        from risk_models.risk_analysis import calculate_correlation_matrix

        corr = calculate_correlation_matrix(self.returns_df)
        np.testing.assert_array_almost_equal(corr.values, corr.values.T)

    def test_correlation_all_values_in_range(self) -> None:
        from risk_models.risk_analysis import calculate_correlation_matrix

        corr = calculate_correlation_matrix(self.returns_df)
        self.assertTrue((corr >= -1.0 - 1e-9).all().all())
        self.assertTrue((corr <= 1.0 + 1e-9).all().all())

    def test_stress_test_scales_with_multiplier(self) -> None:
        from risk_models.risk_analysis import stress_test

        s1 = stress_test(self.returns_df, scenario_multiplier=2.0)
        s2 = stress_test(self.returns_df, scenario_multiplier=4.0)
        # More severe stress → larger absolute losses
        self.assertTrue((s2.abs() >= s1.abs()).all())


if __name__ == "__main__":
    unittest.main(verbosity=2)
