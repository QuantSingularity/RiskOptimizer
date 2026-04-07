"""
Unit tests for risk calculation tasks.
"""

from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
from src.tasks.celery_app import TaskValidationError
from src.tasks.risk_tasks import (
    calculate_portfolio_metrics,
    calculate_var_cvar,
    efficient_frontier_calculation,
    monte_carlo_simulation,
    stress_test_portfolio,
)


class TestMonteCarloSimulation:
    """Test cases for Monte Carlo simulation task."""

    def setup_method(self) -> Any:
        """Set up test data."""
        self.portfolio_data = {
            "weights": [0.4, 0.3, 0.3],
            "historical_returns": np.random.normal(0.001, 0.02, (252, 3)).tolist(),
        }

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_monte_carlo_simulation_success(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test successful Monte Carlo simulation."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = monte_carlo_simulation(
            mock_self, self.portfolio_data, num_simulations=1000, time_horizon=252
        )
        assert "simulation_parameters" in result
        assert "risk_metrics" in result
        assert "statistics" in result
        assert "percentiles" in result
        assert result["simulation_parameters"]["num_simulations"] == 1000
        assert result["simulation_parameters"]["time_horizon"] == 252
        assert mock_task_manager.store_task_progress.called

    def test_monte_carlo_validation_errors(self) -> Any:
        """Test validation errors in Monte Carlo simulation."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        with pytest.raises(TaskValidationError):
            monte_carlo_simulation(
                mock_self, self.portfolio_data, num_simulations=0, time_horizon=252
            )
        with pytest.raises(TaskValidationError):
            monte_carlo_simulation(
                mock_self, self.portfolio_data, num_simulations=1000, time_horizon=0
            )

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_monte_carlo_risk_metrics(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test that risk metrics are calculated correctly."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = monte_carlo_simulation(
            mock_self, self.portfolio_data, num_simulations=1000, time_horizon=252
        )
        risk_metrics = result["risk_metrics"]
        assert "var_95" in risk_metrics
        assert "var_99" in risk_metrics
        assert "cvar_95" in risk_metrics
        assert "cvar_99" in risk_metrics
        assert "probability_of_loss" in risk_metrics
        assert risk_metrics["var_99"] <= risk_metrics["var_95"]


class TestVarCvarCalculation:
    """Test cases for VaR/CVaR calculation task."""

    def setup_method(self) -> Any:
        """Set up test data."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, (252, 3))
        self.portfolio_data = {
            "weights": [0.4, 0.3, 0.3],
            "historical_returns": returns.tolist(),
        }

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_var_cvar_calculation_success(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test successful VaR/CVaR calculation."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = calculate_var_cvar(
            mock_self, self.portfolio_data, confidence_levels=[0.95, 0.99]
        )
        assert "var" in result
        assert "cvar" in result
        assert "statistics" in result
        assert "95%" in result["var"]
        assert "99%" in result["var"]
        assert "95%" in result["cvar"]
        assert "99%" in result["cvar"]
        assert result["cvar"]["95%"] <= result["var"]["95%"]
        assert result["cvar"]["99%"] <= result["var"]["99%"]

    def test_var_cvar_validation_errors(self) -> Any:
        """Test validation errors in VaR/CVaR calculation."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        with pytest.raises(TaskValidationError):
            calculate_var_cvar(
                mock_self, self.portfolio_data, confidence_levels=[0.0, 1.0, 1.5]
            )


class TestEfficientFrontierCalculation:
    """Test cases for efficient frontier calculation task."""

    def setup_method(self) -> Any:
        """Set up test data."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, (252, 4))
        self.assets_data = {
            "returns": returns.tolist(),
            "asset_names": ["Asset_A", "Asset_B", "Asset_C", "Asset_D"],
        }

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_efficient_frontier_calculation_success(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test successful efficient frontier calculation."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = efficient_frontier_calculation(
            mock_self, self.assets_data, num_portfolios=1000
        )
        assert "portfolios" in result
        assert "optimal_portfolios" in result
        assert "statistics" in result
        portfolios = result["portfolios"]
        assert len(portfolios["returns"]) == 1000
        assert len(portfolios["volatilities"]) == 1000
        assert len(portfolios["sharpe_ratios"]) == 1000
        optimal = result["optimal_portfolios"]
        assert "max_sharpe" in optimal
        assert "min_volatility" in optimal
        max_sharpe_weights = optimal["max_sharpe"]["weights"]
        min_vol_weights = optimal["min_volatility"]["weights"]
        assert abs(sum(max_sharpe_weights) - 1.0) < 1e-06
        assert abs(sum(min_vol_weights) - 1.0) < 1e-06

    def test_efficient_frontier_validation_errors(self) -> Any:
        """Test validation errors in efficient frontier calculation."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        with pytest.raises(TaskValidationError):
            efficient_frontier_calculation(
                mock_self, self.assets_data, num_portfolios=0
            )


class TestStressTestPortfolio:
    """Test cases for portfolio stress testing task."""

    def setup_method(self) -> Any:
        """Set up test data."""
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, (252, 3))
        self.portfolio_data = {
            "weights": [0.4, 0.3, 0.3],
            "historical_returns": returns.tolist(),
        }
        self.stress_scenarios = [
            {"type": "market_crash", "shock": -0.3},
            {"type": "volatility_spike", "multiplier": 2.0},
            {"type": "correlation_breakdown", "noise_level": 0.1},
        ]

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_stress_test_success(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test successful stress testing."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = stress_test_portfolio(
            mock_self, self.portfolio_data, self.stress_scenarios
        )
        assert "baseline" in result
        assert "stress_results" in result
        assert len(result["stress_results"]) == len(self.stress_scenarios)
        baseline = result["baseline"]
        assert "return" in baseline
        assert "volatility" in baseline
        for i, stress_result in enumerate(result["stress_results"]):
            assert "scenario" in stress_result
            assert "stressed_return" in stress_result
            assert "stressed_volatility" in stress_result
            assert "return_impact" in stress_result
            assert "volatility_impact" in stress_result
            assert stress_result["scenario"]["type"] == self.stress_scenarios[i]["type"]


class TestCalculatePortfolioMetrics:
    """Test cases for portfolio metrics calculation task."""

    def test_calculate_portfolio_metrics_success(self) -> Any:
        """Test successful portfolio metrics calculation."""
        mock_self = MagicMock()
        mock_self.request.id = "test-task-id"
        result = calculate_portfolio_metrics(
            portfolio_id=1,
            metrics=["sharpe_ratio", "sortino_ratio", "max_drawdown"],
        )
        assert "portfolio_id" in result
        assert "metrics" in result
        assert "calculated_at" in result
        assert result["portfolio_id"] == 1
        metrics = result["metrics"]
        assert "sharpe_ratio" in metrics
        assert "sortino_ratio" in metrics
        assert "max_drawdown" in metrics


class TestRiskTasksIntegration:
    """Integration tests for risk calculation tasks."""

    def setup_method(self) -> Any:
        """Set up integration test data."""
        np.random.seed(42)
        dates = pd.date_range("2020-01-01", "2023-12-31", freq="D")
        returns = np.random.multivariate_normal(
            mean=[0.0005, 0.0003, 0.0007],
            cov=[
                [0.0004, 0.0001, 0.0002],
                [0.0001, 0.0003, 0.0001],
                [0.0002, 0.0001, 0.0005],
            ],
            size=len(dates),
        )
        self.portfolio_data = {
            "weights": [0.5, 0.3, 0.2],
            "historical_returns": returns.tolist(),
        }
        self.assets_data = {
            "returns": returns.tolist(),
            "asset_names": ["Stock_A", "Stock_B", "Stock_C"],
        }

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_monte_carlo_with_realistic_data(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test Monte Carlo simulation with realistic market data."""
        mock_self = MagicMock()
        mock_self.request.id = "integration-test-id"
        result = monte_carlo_simulation(
            mock_self, self.portfolio_data, num_simulations=5000, time_horizon=252
        )
        risk_metrics = result["risk_metrics"]
        assert risk_metrics["var_95"] < 0
        assert risk_metrics["var_99"] < 0
        assert risk_metrics["cvar_95"] <= risk_metrics["var_95"]
        assert risk_metrics["cvar_99"] <= risk_metrics["var_99"]
        assert 0 <= risk_metrics["probability_of_loss"] <= 1

    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_efficient_frontier_with_realistic_data(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test efficient frontier calculation with realistic market data."""
        mock_self = MagicMock()
        mock_self.request.id = "integration-test-id"
        result = efficient_frontier_calculation(
            mock_self, self.assets_data, num_portfolios=2000
        )
        max_sharpe = result["optimal_portfolios"]["max_sharpe"]
        min_vol = result["optimal_portfolios"]["min_volatility"]
        assert max_sharpe["sharpe_ratio"] >= min_vol["sharpe_ratio"]
        assert min_vol["volatility"] <= max_sharpe["volatility"]
        for weights in [max_sharpe["weights"], min_vol["weights"]]:
            assert all((w >= 0 for w in weights))
            assert abs(sum(weights) - 1.0) < 1e-06


@pytest.fixture
def sample_portfolio_data() -> Any:
    """Fixture providing sample portfolio data."""
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, (252, 3))
    return {"weights": [0.4, 0.3, 0.3], "historical_returns": returns.tolist()}


@pytest.fixture
def sample_assets_data() -> Any:
    """Fixture providing sample assets data."""
    np.random.seed(42)
    returns = np.random.normal(0.001, 0.02, (252, 4))
    return {
        "returns": returns.tolist(),
        "asset_names": ["Asset_A", "Asset_B", "Asset_C", "Asset_D"],
    }


class TestRiskTasksPerformance:
    """Performance tests for risk calculation tasks."""

    @pytest.mark.slow
    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_monte_carlo_performance(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test Monte Carlo simulation performance with large datasets."""
        mock_self = MagicMock()
        mock_self.request.id = "performance-test-id"
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, (1000, 10))
        portfolio_data = {"weights": [0.1] * 10, "historical_returns": returns.tolist()}
        import time

        start_time = time.time()
        result = monte_carlo_simulation(
            mock_self, portfolio_data, num_simulations=10000, time_horizon=252
        )
        end_time = time.time()
        execution_time = end_time - start_time
        assert execution_time < 30
        assert "risk_metrics" in result

    @pytest.mark.slow
    @patch("src.tasks.celery_app.task_result_manager")
    @patch("src.tasks.risk_tasks.task_result_manager")
    def test_efficient_frontier_performance(
        self, mock_task_manager: Any, mock_celery_manager: Any
    ) -> Any:
        """Test efficient frontier calculation performance with many assets."""
        mock_self = MagicMock()
        mock_self.request.id = "performance-test-id"
        np.random.seed(42)
        returns = np.random.normal(0.001, 0.02, (500, 20))
        assets_data = {
            "returns": returns.tolist(),
            "asset_names": [f"Asset_{i}" for i in range(20)],
        }
        import time

        start_time = time.time()
        result = efficient_frontier_calculation(
            mock_self, assets_data, num_portfolios=5000
        )
        end_time = time.time()
        execution_time = end_time - start_time
        assert execution_time < 60
        assert "optimal_portfolios" in result
