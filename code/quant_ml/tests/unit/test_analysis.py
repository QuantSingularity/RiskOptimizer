import numpy as np
import pandas as pd
import pytest
from quant_ml.risk import analysis


@pytest.fixture(scope="module")
def log_returns():
    return analysis.load_returns(["AAPL", "MSFT", "BTC_USD"])


class TestLoading:
    def test_inner_join_without_fabricated_rows(self, log_returns):
        assert not log_returns.isna().any().any()
        assert not (log_returns[["AAPL", "MSFT"]] == 0).all(axis=1).any()

    def test_defaults_to_available_symbols(self):
        assert analysis.load_returns().shape[1] == 7

    def test_single_symbol_allowed(self):
        assert analysis.load_returns(["AAPL"]).shape[1] == 1


class TestVar:
    def test_historical_var_positive_and_scales_with_horizon(self, log_returns):
        one = analysis.historical_var(log_returns, 0.99, 1)
        ten = analysis.historical_var(log_returns, 0.99, 10)
        assert (one > 0).all()
        assert np.allclose(ten, one * np.sqrt(10))

    def test_monotone_in_confidence(self, log_returns):
        assert (
            analysis.historical_var(log_returns, 0.99)
            > analysis.historical_var(log_returns, 0.9)
        ).all()

    def test_monte_carlo_close_to_parametric(self, log_returns):
        from scipy import stats

        simulated = analysis.monte_carlo_var(log_returns, 0.95, 1, 200_000, seed=1)
        expected = -(log_returns.mean() - stats.norm.ppf(0.95) * log_returns.std())
        assert np.allclose(simulated, expected, rtol=0.03)

    def test_monte_carlo_reproducible(self, log_returns):
        assert analysis.monte_carlo_var(log_returns, seed=2).equals(
            analysis.monte_carlo_var(log_returns, seed=2)
        )

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"horizon": 0},
            {"horizon": 1000},
            {"horizon": True},
            {"confidence_level": 1.0},
        ],
    )
    def test_validation(self, log_returns, kwargs):
        with pytest.raises(ValueError):
            analysis.historical_var(log_returns, **kwargs)

    def test_simulation_count_validation(self, log_returns):
        with pytest.raises(ValueError):
            analysis.monte_carlo_var(log_returns, n_simulations=0)


class TestGarch:
    def test_horizon_does_not_inflate_volatility(self, log_returns):
        one = analysis.garch_volatility_forecast(log_returns, 1)
        five = analysis.garch_volatility_forecast(log_returns, 5)
        assert np.allclose(five / one, 1.0, atol=0.25)
        annual = log_returns.std() * np.sqrt(252)
        assert (five / annual).between(0.4, 2.5).all()

    def test_short_history_gives_nan(self):
        short = pd.DataFrame({"a": np.random.default_rng(0).normal(0, 0.01, 50)})
        assert analysis.garch_volatility_forecast(short, 5).isna().all()


class TestStressAndCorrelation:
    def test_stress_scales_linearly(self, log_returns):
        assert np.allclose(
            analysis.stress_test(log_returns, 4),
            2 * analysis.stress_test(log_returns, 2),
        )

    @pytest.mark.parametrize("value", [0, -1, 100, True])
    def test_stress_validation(self, log_returns, value):
        with pytest.raises(ValueError):
            analysis.stress_test(log_returns, value)

    def test_correlation_matrix(self, log_returns):
        corr = analysis.calculate_correlation_matrix(log_returns)
        assert np.allclose(corr, corr.T) and np.allclose(np.diag(corr), 1.0)
        assert corr.abs().max().max() <= 1.0 + 1e-12

    def test_run_risk_analysis(self, log_returns):
        result = analysis.run_risk_analysis(returns=log_returns, seed=1)
        assert set(result) == {
            "correlation_matrix",
            "historical_var",
            "monte_carlo_var",
            "garch_volatility",
            "stress_loss",
        }
