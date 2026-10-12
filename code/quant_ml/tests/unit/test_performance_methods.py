import numpy as np
import pytest
from quant_ml.optimization.methods import (
    METHODS,
    black_litterman_posterior,
    optimize_weights,
    risk_contributions,
)
from quant_ml.risk.performance import drawdown_profile, performance_summary


class TestDrawdown:
    def test_known_series(self):
        depth, duration = drawdown_profile(np.array([0.1, -0.2, -0.1, 0.5, 0.0]))
        assert depth == pytest.approx((1.1 * 0.8 * 0.9) / 1.1 - 1.0)
        assert duration == 2

    def test_monotone_gains_have_no_drawdown(self):
        assert drawdown_profile(np.full(10, 0.01)) == (0.0, 0)


class TestPerformance:
    @pytest.fixture(scope="class")
    def series(self):
        rng = np.random.default_rng(2)
        benchmark = rng.normal(0.0004, 0.01, 750)
        portfolio = 1.3 * benchmark + rng.normal(0.0002, 0.004, 750)
        return portfolio, benchmark

    def test_summary_values(self, series):
        portfolio, benchmark = series
        result = performance_summary(portfolio, benchmark)
        summary, comparison = (
            result["performance_summary"],
            result["benchmark_comparison"],
        )
        assert summary["total_return"] == pytest.approx(np.prod(1 + portfolio) - 1)
        assert summary["volatility"] == pytest.approx(
            portfolio.std(ddof=1) * np.sqrt(252)
        )
        assert (
            summary["max_drawdown"] <= 0 and summary["max_drawdown_duration_days"] >= 1
        )
        assert comparison["beta"] == pytest.approx(1.3, abs=0.1)
        assert comparison["tracking_error"] > 0 and np.isfinite(
            comparison["information_ratio"]
        )
        assert result["risk_metrics"]["var_99"] >= result["risk_metrics"]["var_95"] > 0

    def test_sortino_and_calmar_are_computed(self, series):
        summary = performance_summary(series[0])["performance_summary"]
        assert summary["sortino_ratio"] != 0 and summary["calmar_ratio"] != 0

    def test_without_benchmark(self, series):
        assert "benchmark_comparison" not in performance_summary(series[0])

    def test_benchmark_is_aligned_on_the_overlap(self, series):
        portfolio, benchmark = series
        result = performance_summary(portfolio, benchmark[:300])
        assert result["benchmark_comparison"]["overlapping_observations"] == 300

    @pytest.mark.parametrize("bad", [[0.1] * 3, [0.1, -1.5, 0.2, 0.1, 0.1, 0.1]])
    def test_validation(self, bad):
        with pytest.raises(ValueError):
            performance_summary(bad)


class TestOptimizerMethods:
    @pytest.mark.parametrize("method", METHODS)
    def test_every_method_returns_a_valid_portfolio(self, method, returns_frame):
        result = optimize_weights(returns_frame, method)
        weights = np.array(list(result["weights"].values()))
        assert weights.sum() == pytest.approx(1.0) and (weights >= -1e-9).all()
        assert all(result["constraints_satisfied"].values())
        assert sum(result["risk_contributions"].values()) == pytest.approx(1.0)

    def test_risk_parity_equalises_risk_contributions(self, returns_frame):
        contributions = list(
            optimize_weights(returns_frame, "risk_parity")[
                "risk_contributions"
            ].values()
        )
        assert np.allclose(contributions, 1 / 3, atol=0.01)

    def test_minimum_variance_has_lowest_volatility(self, returns_frame):
        volatilities = {
            m: optimize_weights(returns_frame, m)["portfolio_metrics"]["volatility"]
            for m in METHODS
        }
        assert volatilities["minimum_variance"] == min(volatilities.values())

    def test_weight_bounds_are_enforced_not_just_reported(self, returns_frame):
        for method in METHODS:
            weights = np.array(
                list(
                    optimize_weights(
                        returns_frame, method, {"max_weight_per_asset": 0.4}
                    )["weights"].values()
                )
            )
            assert weights.max() <= 0.4 + 1e-6

    def test_min_weight_bound(self, returns_frame):
        weights = np.array(
            list(
                optimize_weights(
                    returns_frame, "mean_variance", {"min_weight_per_asset": 0.2}
                )["weights"].values()
            )
        )
        assert weights.min() >= 0.2 - 1e-6

    def test_risk_aversion_changes_mean_variance_weights(self, returns_frame):
        timid = optimize_weights(returns_frame, "mean_variance", {"risk_aversion": 20})[
            "portfolio_metrics"
        ]["volatility"]
        bold = optimize_weights(returns_frame, "mean_variance", {"risk_aversion": 0.5})[
            "portfolio_metrics"
        ]["volatility"]
        assert bold >= timid

    def test_target_return_is_met_or_rejected(self, returns_frame):
        achievable = optimize_weights(returns_frame, "mean_variance")[
            "portfolio_metrics"
        ]["expected_return"]
        floor = optimize_weights(returns_frame, "minimum_variance")[
            "portfolio_metrics"
        ]["expected_return"]
        target = (achievable + floor) / 2
        result = optimize_weights(
            returns_frame, "mean_variance", {"target_return": target}
        )
        assert result["portfolio_metrics"]["expected_return"] >= target - 1e-6
        with pytest.raises(ValueError, match="exceeds the maximum"):
            optimize_weights(returns_frame, "mean_variance", {"target_return": 10.0})

    def test_black_litterman_without_views_returns_the_market(self, returns_frame):
        result = optimize_weights(
            returns_frame,
            "black_litterman",
            {"market_weights": {"A0": 0.5, "A1": 0.3, "A2": 0.2}},
        )
        assert list(result["weights"].values()) == pytest.approx(
            [0.5, 0.3, 0.2], abs=1e-3
        )

    def test_black_litterman_views_tilt_the_portfolio(self, returns_frame):
        base = optimize_weights(returns_frame, "black_litterman")["weights"]["A0"]
        view = {"assets": {"A0": 1.0}, "return": 0.5, "confidence": 0.9}
        bullish = optimize_weights(returns_frame, "black_litterman", {"views": [view]})
        assert bullish["weights"]["A0"] > base
        assert (
            bullish["details"]["posterior_returns"]["A0"]
            > bullish["details"]["implied_equilibrium_returns"]["A0"]
        )

    def test_relative_views_and_confidence_scale(self):
        cov = np.array([[0.04, 0.01], [0.01, 0.09]])
        market = np.array([0.5, 0.5])

        def view(confidence):
            return [
                {
                    "assets": {"a": 1.0, "b": -1.0},
                    "return": 0.1,
                    "confidence": confidence,
                }
            ]

        _, low = black_litterman_posterior(
            cov, market, 3.0, 0.05, view(0.1), ["a", "b"]
        )
        prior, high = black_litterman_posterior(
            cov, market, 3.0, 0.05, view(0.9), ["a", "b"]
        )
        assert (high[0] - high[1]) > (low[0] - low[1]) > (prior[0] - prior[1])

    @pytest.mark.parametrize(
        "method,params",
        [
            ("bogus", {}),
            ("mean_variance", {"risk_aversion": -1}),
            ("mean_variance", {"max_weight_per_asset": 0.1}),
            ("black_litterman", {"tau": 0}),
            ("black_litterman", {"market_weights": [1, 2]}),
            ("black_litterman", {"market_weights": {"A0": -1}}),
            ("black_litterman", {"views": [{"assets": {"ZZ": 1}, "return": 0.1}]}),
            ("black_litterman", {"views": [{"assets": {}, "return": 0.1}]}),
            (
                "black_litterman",
                {"views": [{"assets": {"A0": 1}, "return": 0.1, "confidence": 1.5}]},
            ),
        ],
    )
    def test_validation(self, returns_frame, method, params):
        with pytest.raises(ValueError):
            optimize_weights(returns_frame, method, params)

    def test_single_asset_rejected(self, returns_frame):
        with pytest.raises(ValueError):
            optimize_weights(returns_frame.iloc[:, :1])

    def test_risk_contributions_helper(self):
        cov = np.array([[0.04, 0.0], [0.0, 0.04]])
        assert risk_contributions(np.array([0.5, 0.5]), cov) == pytest.approx(
            [0.5, 0.5]
        )
        assert risk_contributions(np.zeros(2), cov).sum() == 0
