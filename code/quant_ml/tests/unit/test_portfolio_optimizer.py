import joblib
import numpy as np
import pytest
from quant_ml.optimization.portfolio import (
    AdvancedPortfolioOptimizer,
    ClassicalPortfolioOptimizer,
)


@pytest.fixture(scope="module")
def trained(prices):
    optimizer = AdvancedPortfolioOptimizer(risk_tolerance=5)
    optimizer.train_return_prediction_model(prices)
    return optimizer


class TestOptimizer:
    def test_weights_sum_to_one_and_respect_bounds(self, trained, prices):
        weights, metrics = trained.optimize_portfolio(
            prices, min_weight=0.05, max_weight=0.4
        )
        assert abs(sum(weights.values()) - 1.0) < 1e-9
        assert all(0.05 - 1e-9 <= w <= 0.4 + 1e-9 for w in weights.values())
        assert metrics["volatility"] > 0

    def test_no_nan_target_with_trailing_row(self, prices):
        optimizer = AdvancedPortfolioOptimizer(5)
        weights, _ = optimizer.optimize_portfolio(prices)
        assert all(np.isfinite(list(weights.values())))

    def test_higher_tolerance_takes_more_risk(self, prices):
        low = ClassicalPortfolioOptimizer(1).optimize_portfolio(prices)[1]
        high = ClassicalPortfolioOptimizer(10).optimize_portfolio(prices)[1]
        assert high["volatility"] >= low["volatility"] - 1e-9

    def test_methods_are_consistent(self, prices):
        optimizer = ClassicalPortfolioOptimizer(5)
        sharpe = optimizer.optimize_portfolio(prices, method="max_sharpe")[1]
        minvar = optimizer.optimize_portfolio(prices, method="min_variance")[1]
        utility = optimizer.optimize_portfolio(prices, method="utility")[1]
        assert sharpe["sharpe_ratio"] >= utility["sharpe_ratio"] - 1e-6
        assert minvar["volatility"] <= utility["volatility"] + 1e-6

    def test_unknown_method_rejected(self, prices):
        with pytest.raises(ValueError):
            ClassicalPortfolioOptimizer().optimize_portfolio(prices, method="bogus")

    @pytest.mark.parametrize("value", [0, 11, -1, float("nan"), True, "5", None])
    def test_invalid_risk_tolerance_rejected(self, value):
        with pytest.raises(ValueError):
            AdvancedPortfolioOptimizer(value)

    def test_infeasible_bounds_rejected(self, prices):
        with pytest.raises(ValueError):
            ClassicalPortfolioOptimizer().optimize_portfolio(prices, max_weight=0.1)
        with pytest.raises(ValueError):
            ClassicalPortfolioOptimizer().optimize_portfolio(prices, min_weight=0.5)

    def test_single_asset_and_short_history_rejected(self, prices):
        with pytest.raises(ValueError):
            ClassicalPortfolioOptimizer().optimize_portfolio(prices[["AAA"]])
        with pytest.raises(ValueError):
            ClassicalPortfolioOptimizer().optimize_portfolio(prices.head(10))

    def test_negative_prices_rejected(self, prices):
        broken = prices.copy()
        broken.iloc[5, 0] = -1.0
        with pytest.raises(ValueError):
            ClassicalPortfolioOptimizer().optimize_portfolio(broken)

    def test_market_index_column_is_excluded_from_assets(self, trained, prices):
        data = prices.copy()
        data["market_index"] = prices.mean(axis=1)
        weights, _ = trained.optimize_portfolio(data)
        assert "market_index" not in weights

    def test_with_risk_tolerance_does_not_mutate_original(self, trained):
        clone = trained.with_risk_tolerance(9)
        assert clone.risk_tolerance == 9
        assert trained.risk_tolerance == 5
        assert clone.return_model is trained.return_model

    def test_efficient_frontier_is_ordered(self, trained, prices):
        frontier = trained.efficient_frontier(prices, points=8)
        vols = [p["volatility"] for p in frontier]
        assert len(frontier) >= 2
        assert vols == sorted(vols) or all(
            vols[i] <= vols[i + 1] + 1e-6 for i in range(len(vols) - 1)
        )
        for point in frontier:
            assert abs(sum(point["weights"].values()) - 1.0) < 1e-6

    def test_monte_carlo_is_reproducible_and_validated(self, trained, prices):
        weights, _ = trained.optimize_portfolio(prices)
        first, metrics = trained.monte_carlo_simulation(
            prices, weights, 200, 30, seed=3
        )
        second, _ = trained.monte_carlo_simulation(prices, weights, 200, 30, seed=3)
        assert first.shape == (30, 200)
        assert np.allclose(first.to_numpy(), second.to_numpy())
        assert metrics["var_99"] >= metrics["var_95"] >= 0
        assert 0 <= metrics["max_drawdown"] <= 1
        with pytest.raises(ValueError):
            trained.monte_carlo_simulation(prices, {"ZZZ": 1.0})
        with pytest.raises(ValueError):
            trained.monte_carlo_simulation(prices, {"AAA": -1.0})


class TestPersistence:
    def test_untrained_save_rejected(self, tmp_path):
        with pytest.raises(ValueError):
            AdvancedPortfolioOptimizer().save_model(str(tmp_path / "m.joblib"))

    def test_round_trip_preserves_predictions(self, trained, prices, tmp_path):
        path = str(tmp_path / "nested" / "m.joblib")
        trained.save_model(path)
        loaded = AdvancedPortfolioOptimizer.load_model(path)
        before = trained.optimize_portfolio(prices)[0]
        after = loaded.optimize_portfolio(prices)[0]
        assert before.keys() == after.keys()
        assert np.allclose(list(before.values()), list(after.values()))

    def test_missing_and_foreign_files_rejected(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            AdvancedPortfolioOptimizer.load_model(str(tmp_path / "none.joblib"))
        bad = tmp_path / "bad.joblib"
        joblib.dump({"model": 1}, bad)
        with pytest.raises(ValueError):
            AdvancedPortfolioOptimizer.load_model(str(bad))

    def test_evaluate_requires_training(self, prices):
        with pytest.raises(ValueError):
            AdvancedPortfolioOptimizer().evaluate(prices)
