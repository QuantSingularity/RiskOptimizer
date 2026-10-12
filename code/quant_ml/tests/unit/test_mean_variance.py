import pytest
from quant_ml.optimization import mean_variance
from quant_ml.optimization.mean_variance import (
    discrete_allocation_suggestion,
    load_prices,
    mean_variance_optimization,
    select_mip_solver,
)


@pytest.fixture(scope="module")
def prices():
    return load_prices(["AAPL", "MSFT", "GOOGL", "BTC_USD"])


@pytest.fixture(scope="module")
def result(prices):
    return mean_variance_optimization(prices)


class TestMeanVariance:
    def test_weights_valid(self, result):
        for key in ("max_sharpe_weights", "min_vol_weights"):
            assert sum(result[key].values()) == pytest.approx(1.0, abs=1e-3)
            assert all(w >= 0 for w in result[key].values())

    def test_performance_is_structured(self, result):
        assert set(result["max_sharpe_performance"]) == {
            "expected_return",
            "volatility",
            "sharpe_ratio",
        }

    def test_min_vol_has_lower_volatility_and_max_sharpe_higher_sharpe(self, result):
        assert (
            result["min_vol_performance"]["volatility"]
            <= result["max_sharpe_performance"]["volatility"] + 1e-9
        )
        assert (
            result["max_sharpe_performance"]["sharpe_ratio"]
            >= result["min_vol_performance"]["sharpe_ratio"] - 1e-9
        )

    def test_weight_cap(self, prices):
        capped = mean_variance_optimization(prices, max_weight=0.4)
        assert max(capped["max_sharpe_weights"].values()) <= 0.4 + 1e-6

    @pytest.mark.parametrize("cap", [0.1, 1.5])
    def test_infeasible_cap(self, prices, cap):
        with pytest.raises(ValueError):
            mean_variance_optimization(prices, max_weight=cap)

    def test_single_asset_rejected(self, prices):
        with pytest.raises(ValueError):
            mean_variance_optimization(prices.iloc[:, :1])

    def test_no_asset_beats_risk_free_rate(self, prices):
        with pytest.raises(ValueError):
            mean_variance_optimization(prices, risk_free_rate=5.0)


class TestDiscreteAllocation:
    def test_allocation_respects_budget(self, prices, result):
        allocation = discrete_allocation_suggestion(
            prices, result["max_sharpe_weights"], 100_000
        )
        latest = prices.iloc[-1]
        spent = sum(
            latest[symbol] * shares
            for symbol, shares in allocation["allocation"].items()
        )
        assert spent + allocation["leftover"] == pytest.approx(100_000, rel=1e-6)
        assert all(shares > 0 for shares in allocation["allocation"].values())

    def test_validation(self, prices):
        with pytest.raises(ValueError):
            discrete_allocation_suggestion(prices, {"AAPL": 1.0}, 0)
        with pytest.raises(ValueError):
            discrete_allocation_suggestion(prices, {"AAPL": 0.0}, 1000)

    def test_integer_program_is_used_and_beats_greedy(self, prices, result):
        from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices

        weights = {k: v for k, v in result["max_sharpe_weights"].items() if v > 0}
        exact = discrete_allocation_suggestion(prices, weights, 200_000)
        assert exact["method"].startswith("integer_program:")
        latest = get_latest_prices(prices[list(weights)])
        _, greedy_leftover = DiscreteAllocation(
            weights, latest, total_portfolio_value=200_000
        ).greedy_portfolio()
        assert exact["leftover"] <= greedy_leftover

    def test_unaffordable_assets_are_reported(self, prices):
        outcome = discrete_allocation_suggestion(
            prices, {"AAPL": 0.5, "BTC_USD": 0.5}, 20_000
        )
        assert (
            outcome["unallocated_assets"] == ["BTC_USD"]
            and "AAPL" in outcome["allocation"]
        )

    def test_falls_back_to_greedy_without_a_solver(self, prices, result, monkeypatch):
        monkeypatch.setattr(mean_variance, "select_mip_solver", lambda: None)
        outcome = discrete_allocation_suggestion(
            prices, result["max_sharpe_weights"], 50_000
        )
        assert outcome["method"] == "greedy" and outcome["allocation"]

    def test_falls_back_to_greedy_when_the_solver_fails(
        self, prices, result, monkeypatch
    ):
        from pypfopt.discrete_allocation import DiscreteAllocation

        def broken(self, *args, **kwargs):
            raise RuntimeError("solver crashed")

        monkeypatch.setattr(DiscreteAllocation, "lp_portfolio", broken)
        assert (
            discrete_allocation_suggestion(
                prices, result["max_sharpe_weights"], 50_000
            )["method"]
            == "greedy"
        )

    def test_solver_selection_prefers_an_installed_mip_solver(self):
        import cvxpy

        assert select_mip_solver() in cvxpy.installed_solvers()
