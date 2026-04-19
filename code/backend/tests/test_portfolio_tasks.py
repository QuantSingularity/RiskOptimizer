"""
Unit tests for portfolio management tasks.
"""

import time
from datetime import datetime
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from src.tasks.celery_app import TaskValidationError
from src.tasks.portfolio_tasks import (
    _calculate_tracking_error,
    _check_constraints,
    _optimize_mean_variance,
    _optimize_minimum_variance,
    _optimize_risk_parity,
    analyze_portfolio_performance,
    optimize_portfolio,
    rebalance_portfolio,
    update_portfolio_data,
)


class TestPortfolioOptimization:
    """Test cases for portfolio optimization task."""

    def setup_method(self) -> None:
        """Set up test data."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, (252, 4))
        self.assets_data = {
            "returns": returns.tolist(),
            "asset_names": ["Stock_A", "Stock_B", "Stock_C", "Stock_D"],
        }
        self.optimization_params = {
            "method": "mean_variance",
            "target_return": 0.08,
            "max_weight_per_asset": 0.4,
            "min_weight_per_asset": 0.05,
        }

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_mean_variance_optimization_success(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test successful mean-variance optimization."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = optimize_portfolio(
            mock_self, self.assets_data, self.optimization_params
        )
        assert "optimization_method" in result
        assert "weights" in result
        assert "portfolio_metrics" in result
        assert "risk_contributions" in result
        assert "constraints_satisfied" in result
        assert result["optimization_method"] == "mean_variance"
        weights = list(result["weights"].values())
        assert abs(sum(weights) - 1.0) < 1e-6
        assert all(w >= 0 for w in weights)
        metrics = result["portfolio_metrics"]
        assert "expected_return" in metrics
        assert "volatility" in metrics
        assert "sharpe_ratio" in metrics

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_risk_parity_optimization_success(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test successful risk parity optimization."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        params = self.optimization_params.copy()
        params["method"] = "risk_parity"
        result = optimize_portfolio(mock_self, self.assets_data, params)
        assert result["optimization_method"] == "risk_parity"
        weights = list(result["weights"].values())
        assert abs(sum(weights) - 1.0) < 1e-6
        risk_contrib = list(result["risk_contributions"].values())
        risk_contrib_std = np.std(risk_contrib)
        assert risk_contrib_std < 0.1

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_minimum_variance_optimization_success(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test successful minimum variance optimization."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        params = self.optimization_params.copy()
        params["method"] = "minimum_variance"
        result = optimize_portfolio(mock_self, self.assets_data, params)
        assert result["optimization_method"] == "minimum_variance"
        weights = list(result["weights"].values())
        assert abs(sum(weights) - 1.0) < 1e-6

    def test_invalid_optimization_method(self) -> None:
        """Test validation error for invalid optimization method."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        params = self.optimization_params.copy()
        params["method"] = "invalid_method"
        with pytest.raises(TaskValidationError):
            optimize_portfolio(mock_self, self.assets_data, params)


class TestPortfolioRebalancing:
    """Test cases for portfolio rebalancing task."""

    def setup_method(self) -> None:
        """Set up test data."""
        self.current_portfolio = {
            "holdings": {
                "Stock_A": 10000,
                "Stock_B": 15000,
                "Stock_C": 20000,
                "Stock_D": 5000,
            }
        }
        self.target_weights = {
            "Stock_A": 0.25,
            "Stock_B": 0.25,
            "Stock_C": 0.25,
            "Stock_D": 0.25,
        }
        self.rebalancing_params = {
            "min_transaction_size": 100,
            "transaction_cost_rate": 0.001,
        }

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_rebalancing_analysis_success(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test successful rebalancing analysis."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = rebalance_portfolio(
            mock_self,
            self.current_portfolio,
            self.target_weights,
            self.rebalancing_params,
        )
        assert "current_portfolio" in result
        assert "target_portfolio" in result
        assert "rebalancing_analysis" in result
        assert "transactions" in result
        current = result["current_portfolio"]
        assert "total_value" in current
        assert "weights" in current
        assert current["total_value"] == 50000
        analysis = result["rebalancing_analysis"]
        assert "total_turnover" in analysis
        assert "turnover_rate" in analysis
        assert "number_of_transactions" in analysis
        assert "estimated_costs" in analysis
        assert "cost_percentage" in analysis
        transactions = result["transactions"]
        for asset, transaction in transactions.items():
            assert "current_value" in transaction
            assert "target_value" in transaction
            assert "transaction_amount" in transaction
            assert "transaction_type" in transaction

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_rebalancing_with_new_assets(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test rebalancing when adding new assets."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        target_weights = self.target_weights.copy()
        target_weights["Stock_E"] = 0.2
        for asset in ["Stock_A", "Stock_B", "Stock_C", "Stock_D"]:
            target_weights[asset] = 0.2
        result = rebalance_portfolio(
            mock_self, self.current_portfolio, target_weights, self.rebalancing_params
        )
        transactions = result["transactions"]
        assert "Stock_E" in transactions
        assert transactions["Stock_E"]["transaction_type"] == "buy"
        assert transactions["Stock_E"]["current_value"] == 0


class TestPortfolioPerformanceAnalysis:
    """Test cases for portfolio performance analysis task."""

    def setup_method(self) -> None:
        """Set up test data."""
        np.random.seed(42)
        n_periods = 252
        portfolio_returns = np.random.normal(0.0008, 0.015, n_periods)
        benchmark_returns = np.random.normal(0.0006, 0.012, n_periods)
        correlation = 0.7
        benchmark_returns = (
            correlation * portfolio_returns
            + np.sqrt(1 - correlation**2) * benchmark_returns
        )
        self.portfolio_data = {"returns": portfolio_returns.tolist()}
        self.benchmark_data = {"returns": benchmark_returns.tolist()}
        self.analysis_period = {"start_date": "2023-01-01", "end_date": "2023-12-31"}

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_performance_analysis_success(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test successful performance analysis."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = analyze_portfolio_performance(
            mock_self, self.portfolio_data, self.benchmark_data, self.analysis_period
        )
        assert "performance_summary" in result
        assert "benchmark_comparison" in result
        assert "risk_metrics" in result
        assert "metadata" in result
        perf_summary = result["performance_summary"]
        required_metrics = [
            "total_return",
            "annualized_return",
            "volatility",
            "sharpe_ratio",
            "max_drawdown",
            "max_drawdown_duration_days",
        ]
        for metric in required_metrics:
            assert metric in perf_summary
        benchmark_comp = result["benchmark_comparison"]
        required_benchmark_metrics = [
            "benchmark_total_return",
            "benchmark_annualized_return",
            "benchmark_volatility",
            "benchmark_sharpe",
            "excess_return",
            "tracking_error",
            "information_ratio",
            "beta",
            "alpha",
        ]
        for metric in required_benchmark_metrics:
            assert metric in benchmark_comp
        risk_metrics = result["risk_metrics"]
        assert "var_95" in risk_metrics
        assert "var_99" in risk_metrics
        assert "downside_deviation" in risk_metrics
        assert "sortino_ratio" in risk_metrics
        assert -1 <= perf_summary["max_drawdown"] <= 0
        assert benchmark_comp["beta"] > 0

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_performance_analysis_with_different_lengths(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test performance analysis with different return series lengths."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        portfolio_data = {"returns": self.portfolio_data["returns"][:200]}
        result = analyze_portfolio_performance(
            mock_self, portfolio_data, self.benchmark_data, self.analysis_period
        )
        assert "performance_summary" in result
        assert result["metadata"]["number_of_observations"] == 200


class TestPortfolioDataUpdate:
    """Test cases for portfolio data update task."""

    def test_update_portfolio_data_success(self) -> None:
        """Test successful portfolio data update (non-bound task)."""
        market_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "prices": {"Stock_A": 100.5, "Stock_B": 75.25, "Stock_C": 150.75},
        }
        result = update_portfolio_data(portfolio_id=1, market_data=market_data)
        assert "portfolio_id" in result
        assert "updated_at" in result
        assert "market_data_timestamp" in result
        assert "assets_updated" in result
        assert "status" in result
        assert result["portfolio_id"] == 1
        assert result["status"] == "success"
        assert result["assets_updated"] == 3


class TestOptimizationHelpers:
    """Test cases for optimization helper functions."""

    def setup_method(self) -> None:
        """Set up test data."""
        np.random.seed(42)
        self.mean_returns = np.array([0.08, 0.12, 0.1, 0.15])
        self.cov_matrix = np.array(
            [
                [0.04, 0.01, 0.02, 0.01],
                [0.01, 0.09, 0.01, 0.02],
                [0.02, 0.01, 0.06, 0.01],
                [0.01, 0.02, 0.01, 0.16],
            ]
        )

    def test_mean_variance_optimization(self) -> None:
        """Test mean-variance optimization helper."""
        params = {"target_return": 0.1}
        weights = _optimize_mean_variance(self.mean_returns, self.cov_matrix, params)
        assert abs(np.sum(weights) - 1.0) < 1e-6
        assert np.all(weights >= 0)

    def test_risk_parity_optimization(self) -> None:
        """Test risk parity optimization helper."""
        params = {}
        weights = _optimize_risk_parity(self.cov_matrix, params)
        assert abs(np.sum(weights) - 1.0) < 1e-6
        assert np.all(weights >= 0.001)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(self.cov_matrix, weights)))
        marginal_contrib = np.dot(self.cov_matrix, weights)
        risk_contrib = weights * marginal_contrib / portfolio_vol**2
        assert np.std(risk_contrib) < 0.1

    def test_minimum_variance_optimization(self) -> None:
        """Test minimum variance optimization helper."""
        params = {}
        weights = _optimize_minimum_variance(self.cov_matrix, params)
        assert abs(np.sum(weights) - 1.0) < 1e-6
        assert np.all(weights >= 0)
        equal_weights = np.array([0.25, 0.25, 0.25, 0.25])
        min_var_portfolio_var = np.dot(weights.T, np.dot(self.cov_matrix, weights))
        equal_weight_var = np.dot(
            equal_weights.T, np.dot(self.cov_matrix, equal_weights)
        )
        assert min_var_portfolio_var <= equal_weight_var

    def test_check_constraints(self) -> None:
        """Test constraint checking helper."""
        weights = np.array([0.25, 0.25, 0.25, 0.25])
        params = {"max_weight_per_asset": 0.3, "min_weight_per_asset": 0.2}
        constraints = _check_constraints(weights, params)
        assert (
            constraints["weights_sum_to_one"] == True
        )  # noqa: E712 - np.bool_ comparison
        assert constraints["no_negative_weights"] == True  # noqa: E712
        assert constraints["max_weight_constraint"] == True  # noqa: E712
        assert constraints["min_weight_constraint"] == True  # noqa: E712

    def test_calculate_tracking_error(self) -> None:
        """Test tracking error calculation helper."""
        current_weights = {"A": 0.3, "B": 0.4, "C": 0.3}
        target_weights = {"A": 0.25, "B": 0.5, "C": 0.25}
        tracking_error = _calculate_tracking_error(current_weights, target_weights)
        assert tracking_error > 0
        identical_te = _calculate_tracking_error(current_weights, current_weights)
        assert abs(identical_te) < 1e-10


class TestPortfolioTasksIntegration:
    """Integration tests for portfolio management tasks."""

    def setup_method(self) -> None:
        """Set up integration test data."""
        np.random.seed(42)
        n_assets = 5
        n_periods = 500
        correlation_matrix = np.random.uniform(0.1, 0.7, (n_assets, n_assets))
        correlation_matrix = (correlation_matrix + correlation_matrix.T) / 2
        np.fill_diagonal(correlation_matrix, 1.0)
        eigenvals, eigenvecs = np.linalg.eigh(correlation_matrix)
        eigenvals = np.maximum(eigenvals, 0.01)
        correlation_matrix = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
        volatilities = np.random.uniform(0.15, 0.35, n_assets)
        cov_matrix = np.outer(volatilities, volatilities) * correlation_matrix
        mean_returns = np.random.uniform(0.05, 0.15, n_assets)
        returns = np.random.multivariate_normal(
            mean_returns / 252, cov_matrix / 252, n_periods
        )
        self.assets_data = {
            "returns": returns.tolist(),
            "asset_names": [f"Asset_{i}" for i in range(n_assets)],
        }

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_full_optimization_workflow(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test complete optimization workflow."""
        mock_self = MagicMock()
        mock_self.request.id = "integration-test-id"
        methods = ["mean_variance", "risk_parity", "minimum_variance"]
        results = {}
        for method in methods:
            params = {
                "method": method,
                "target_return": 0.1 if method == "mean_variance" else None,
            }
            result = optimize_portfolio(mock_self, self.assets_data, params)
            results[method] = result
            assert result["optimization_method"] == method
            weights = list(result["weights"].values())
            assert abs(sum(weights) - 1.0) < 1e-6
            assert all(w >= 0 for w in weights)
        mv_sharpe = results["mean_variance"]["portfolio_metrics"]["sharpe_ratio"]
        rp_sharpe = results["risk_parity"]["portfolio_metrics"]["sharpe_ratio"]
        minvar_sharpe = results["minimum_variance"]["portfolio_metrics"]["sharpe_ratio"]
        assert mv_sharpe > 0
        assert rp_sharpe > 0
        assert minvar_sharpe > 0


class TestPortfolioTasksPerformance:
    """Performance tests for portfolio management tasks."""

    @pytest.mark.slow
    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.portfolio_tasks.task_result_manager")
    def test_optimization_performance_large_universe(
        self, mock_task_manager: "MagicMock", mock_celery_manager: "MagicMock"
    ) -> object:
        """Test optimization performance with large asset universe."""
        mock_self = MagicMock()
        mock_self.request.id = "performance-test-id"
        n_assets = 50
        n_periods = 252
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, (n_periods, n_assets))
        assets_data = {
            "returns": returns.tolist(),
            "asset_names": [f"Asset_{i}" for i in range(n_assets)],
        }
        params = {"method": "minimum_variance"}
        start_time = time.time()
        result = optimize_portfolio(mock_self, assets_data, params)
        end_time = time.time()
        execution_time = end_time - start_time
        assert execution_time < 30
        assert "weights" in result
        assert len(result["weights"]) == n_assets
