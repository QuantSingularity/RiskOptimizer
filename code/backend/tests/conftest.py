"""
Test configuration and fixtures for the RiskOptimizer test suite.
"""

import tempfile
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

pytest_plugins = []


def pytest_configure(config: Any) -> Any:
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


@pytest.fixture(scope="session")
def test_data_dir() -> Any:
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def sample_returns_data() -> Any:
    """Generate sample returns data for testing."""
    np.random.seed(42)
    n_periods = 252
    correlation_matrix = np.array(
        [
            [1.0, 0.7, 0.3, 0.5, 0.2],
            [0.7, 1.0, 0.25, 0.45, 0.15],
            [0.3, 0.25, 1.0, 0.35, 0.4],
            [0.5, 0.45, 0.35, 1.0, 0.3],
            [0.2, 0.15, 0.4, 0.3, 1.0],
        ]
    )
    annual_returns = np.array([0.08, 0.1, 0.06, 0.12, 0.05])
    annual_volatilities = np.array([0.15, 0.2, 0.08, 0.25, 0.12])
    daily_returns = annual_returns / 252
    daily_volatilities = annual_volatilities / np.sqrt(252)
    cov_matrix = np.outer(daily_volatilities, daily_volatilities) * correlation_matrix
    returns = np.random.multivariate_normal(daily_returns, cov_matrix, n_periods)
    return {
        "returns": returns,
        "asset_names": ["Stock_A", "Stock_B", "Bond_A", "REIT_A", "Commodity_A"],
        "dates": pd.date_range("2023-01-01", periods=n_periods, freq="D"),
        "annual_returns": annual_returns,
        "annual_volatilities": annual_volatilities,
        "correlation_matrix": correlation_matrix,
    }


@pytest.fixture
def sample_portfolio_data(sample_returns_data: Any) -> Any:
    """Generate sample portfolio data for testing."""
    weights = np.array([0.3, 0.25, 0.2, 0.15, 0.1])
    portfolio_returns = np.dot(sample_returns_data["returns"], weights)
    return {
        "weights": weights.tolist(),
        "asset_names": sample_returns_data["asset_names"],
        "historical_returns": sample_returns_data["returns"].tolist(),
        "portfolio_returns": portfolio_returns.tolist(),
        "holdings": {
            "Stock_A": 300000,
            "Stock_B": 250000,
            "Bond_A": 200000,
            "REIT_A": 150000,
            "Commodity_A": 100000,
        },
        "total_value": 1000000,
        "portfolio_name": "Test Portfolio",
    }


@pytest.fixture
def sample_benchmark_data(sample_returns_data: Any) -> Any:
    """Generate sample benchmark data for testing."""
    benchmark_weights = np.array([0.4, 0.3, 0.15, 0.1, 0.05])
    benchmark_returns = np.dot(sample_returns_data["returns"], benchmark_weights)
    return {
        "returns": benchmark_returns.tolist(),
        "name": "Market Benchmark",
        "weights": benchmark_weights.tolist(),
    }


@pytest.fixture
def sample_stress_scenarios() -> Any:
    """Generate sample stress test scenarios."""
    return [
        {
            "name": "Market Crash",
            "type": "market_crash",
            "shock": -0.3,
            "description": "30% market decline",
        },
        {
            "name": "Volatility Spike",
            "type": "volatility_spike",
            "multiplier": 2.0,
            "description": "Volatility doubles",
        },
        {
            "name": "Correlation Breakdown",
            "type": "correlation_breakdown",
            "noise_level": 0.15,
            "description": "Asset correlations break down",
        },
        {
            "name": "Interest Rate Shock",
            "type": "interest_rate_shock",
            "rate_change": 0.02,
            "description": "200 basis point rate increase",
        },
    ]


@pytest.fixture
def mock_celery_task() -> Any:
    """Mock Celery task for testing."""
    mock_task = MagicMock()
    mock_task.request.id = "test-task-id-12345"
    mock_task.request.retries = 0
    mock_task.request.eta = None
    return mock_task


@pytest.fixture
def mock_redis_client() -> Any:
    """Mock Redis client for testing."""
    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.get.return_value = None
    mock_redis.set.return_value = True
    mock_redis.hgetall.return_value = {}
    mock_redis.hset.return_value = True
    mock_redis.expire.return_value = True
    mock_redis.keys.return_value = []
    return mock_redis


@pytest.fixture
def mock_task_result_manager() -> Any:
    """Mock task result manager for testing."""
    with patch("tasks.celery_app.task_result_manager") as mock_manager:
        mock_manager.store_task_progress.return_value = None
        mock_manager.get_task_progress.return_value = {}
        mock_manager.store_task_metadata.return_value = None
        mock_manager.get_task_metadata.return_value = {}
        yield mock_manager


@pytest.fixture
def optimization_test_cases() -> Any:
    """Generate test cases for portfolio optimization."""
    return [
        {
            "method": "mean_variance",
            "params": {
                "target_return": 0.08,
                "max_weight_per_asset": 0.4,
                "min_weight_per_asset": 0.05,
            },
            "expected_constraints": {
                "weights_sum_to_one": True,
                "no_negative_weights": True,
                "max_weight_constraint": True,
                "min_weight_constraint": True,
            },
        },
        {
            "method": "risk_parity",
            "params": {},
            "expected_constraints": {
                "weights_sum_to_one": True,
                "no_negative_weights": True,
            },
        },
        {
            "method": "minimum_variance",
            "params": {"max_weight_per_asset": 0.5},
            "expected_constraints": {
                "weights_sum_to_one": True,
                "no_negative_weights": True,
                "max_weight_constraint": True,
            },
        },
    ]


@pytest.fixture
def monte_carlo_test_cases() -> Any:
    """Generate test cases for Monte Carlo simulation."""
    return [
        {
            "num_simulations": 1000,
            "time_horizon": 252,
            "expected_metrics": [
                "var_95",
                "var_99",
                "cvar_95",
                "cvar_99",
                "probability_of_loss",
            ],
        },
        {
            "num_simulations": 5000,
            "time_horizon": 126,
            "expected_metrics": [
                "var_95",
                "var_99",
                "cvar_95",
                "cvar_99",
                "probability_of_loss",
            ],
        },
        {
            "num_simulations": 10000,
            "time_horizon": 63,
            "expected_metrics": [
                "var_95",
                "var_99",
                "cvar_95",
                "cvar_99",
                "probability_of_loss",
            ],
        },
    ]


@pytest.fixture
def performance_analysis_test_data() -> Any:
    """Generate test data for performance analysis."""
    np.random.seed(42)
    n_periods = 504
    market_returns = np.random.normal(0.0008, 0.015, n_periods)
    alpha = 0.0002
    beta = 1.2
    idiosyncratic_vol = 0.008
    portfolio_returns = (
        alpha
        + beta * market_returns
        + np.random.normal(0, idiosyncratic_vol, n_periods)
    )
    return {
        "portfolio_returns": portfolio_returns.tolist(),
        "benchmark_returns": market_returns.tolist(),
        "dates": pd.date_range("2022-01-01", periods=n_periods, freq="D"),
        "expected_beta": beta,
        "expected_alpha_annual": alpha * 252,
    }


@pytest.fixture
def report_generation_test_data(sample_portfolio_data: Any) -> Any:
    """Generate test data for report generation."""
    return {
        "portfolio_data": sample_portfolio_data,
        "performance_data": {
            "total_return": 0.15,
            "annualized_return": 0.12,
            "volatility": 0.18,
            "sharpe_ratio": 0.56,
            "max_drawdown": -0.08,
            "beta": 1.1,
            "alpha": 0.02,
        },
        "risk_metrics": {
            "var_95": -0.025,
            "var_99": -0.045,
            "cvar_95": -0.035,
            "cvar_99": -0.065,
        },
        "report_config": {
            "format": "pdf",
            "include_charts": True,
            "include_risk_analysis": True,
            "include_performance_attribution": True,
        },
    }


@pytest.fixture
def task_monitoring_test_data() -> Any:
    """Generate test data for task monitoring."""
    return {
        "active_tasks": [
            {
                "task_id": "task-1",
                "task_type": "monte_carlo_simulation",
                "status": "RUNNING",
                "progress": 45,
                "started_at": datetime.utcnow() - timedelta(minutes=2),
            },
            {
                "task_id": "task-2",
                "task_type": "portfolio_optimization",
                "status": "RUNNING",
                "progress": 80,
                "started_at": datetime.utcnow() - timedelta(minutes=1),
            },
        ],
        "completed_tasks": [
            {
                "task_id": "task-3",
                "task_type": "report_generation",
                "status": "SUCCESS",
                "completed_at": datetime.utcnow() - timedelta(minutes=5),
                "execution_time_seconds": 120,
            }
        ],
        "failed_tasks": [
            {
                "task_id": "task-4",
                "task_type": "efficient_frontier_calculation",
                "status": "FAILURE",
                "failed_at": datetime.utcnow() - timedelta(minutes=10),
                "error_message": "Optimization failed to converge",
            }
        ],
    }


def assert_portfolio_weights_valid(weights: Any, tolerance: Any = 1e-06) -> Any:
    """Assert that portfolio weights are valid."""
    if isinstance(weights, dict):
        weights = list(weights.values())
    assert (
        abs(sum(weights) - 1.0) < tolerance
    ), f"Weights sum to {sum(weights)}, not 1.0"
    assert all((w >= 0 for w in weights)), "Some weights are negative"


def assert_risk_metrics_reasonable(risk_metrics: Any) -> Any:
    """Assert that risk metrics are reasonable."""
    if "var_95" in risk_metrics:
        assert risk_metrics["var_95"] < 0, "VaR 95% should be negative"
    if "var_99" in risk_metrics:
        assert risk_metrics["var_99"] < 0, "VaR 99% should be negative"
        if "var_95" in risk_metrics:
            assert (
                risk_metrics["var_99"] <= risk_metrics["var_95"]
            ), "VaR 99% should be more extreme than VaR 95%"
    if "cvar_95" in risk_metrics and "var_95" in risk_metrics:
        assert (
            risk_metrics["cvar_95"] <= risk_metrics["var_95"]
        ), "CVaR 95% should be more extreme than VaR 95%"
    if "cvar_99" in risk_metrics and "var_99" in risk_metrics:
        assert (
            risk_metrics["cvar_99"] <= risk_metrics["var_99"]
        ), "CVaR 99% should be more extreme than VaR 99%"


def assert_performance_metrics_reasonable(performance_metrics: Any) -> Any:
    """Assert that performance metrics are reasonable."""
    if "total_return" in performance_metrics:
        assert (
            -1 <= performance_metrics["total_return"] <= 10
        ), "Total return outside reasonable range"
    if "annualized_return" in performance_metrics:
        assert (
            -1 <= performance_metrics["annualized_return"] <= 2
        ), "Annualized return outside reasonable range"
    if "volatility" in performance_metrics:
        assert (
            0 <= performance_metrics["volatility"] <= 2
        ), "Volatility outside reasonable range"
    if "sharpe_ratio" in performance_metrics:
        assert (
            -5 <= performance_metrics["sharpe_ratio"] <= 5
        ), "Sharpe ratio outside reasonable range"
    if "max_drawdown" in performance_metrics:
        assert (
            performance_metrics["max_drawdown"] <= 0
        ), "Max drawdown should be negative or zero"


def create_test_portfolio(n_assets: Any = 5, total_value: Any = 1000000) -> Any:
    """Create a test portfolio with specified number of assets."""
    np.random.seed(42)
    weights = np.random.dirichlet(np.ones(n_assets))
    asset_names = [f"Asset_{i}" for i in range(n_assets)]
    holdings = {
        name: weight * total_value for name, weight in zip(asset_names, weights)
    }
    return {
        "weights": weights.tolist(),
        "asset_names": asset_names,
        "holdings": holdings,
        "total_value": total_value,
    }


def create_test_returns(n_periods: Any = 252, n_assets: Any = 5, seed: Any = 42) -> Any:
    """Create test returns data with realistic characteristics."""
    np.random.seed(seed)
    mean_returns = np.random.uniform(0.0005, 0.0015, n_assets)
    volatilities = np.random.uniform(0.01, 0.03, n_assets)
    correlation = np.random.uniform(0.1, 0.7, (n_assets, n_assets))
    correlation = (correlation + correlation.T) / 2
    np.fill_diagonal(correlation, 1.0)
    eigenvals, eigenvecs = np.linalg.eigh(correlation)
    eigenvals = np.maximum(eigenvals, 0.01)
    correlation = eigenvecs @ np.diag(eigenvals) @ eigenvecs.T
    cov_matrix = np.outer(volatilities, volatilities) * correlation
    returns = np.random.multivariate_normal(mean_returns, cov_matrix, n_periods)
    return returns


def validate_monte_carlo_result(result: Any) -> Any:
    """Validate Monte Carlo simulation result structure."""
    required_keys = [
        "simulation_parameters",
        "risk_metrics",
        "statistics",
        "percentiles",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    risk_metrics = result["risk_metrics"]
    required_risk_metrics = [
        "var_95",
        "var_99",
        "cvar_95",
        "cvar_99",
        "probability_of_loss",
    ]
    for metric in required_risk_metrics:
        assert metric in risk_metrics, f"Missing risk metric: {metric}"
    assert_risk_metrics_reasonable(risk_metrics)


def validate_optimization_result(result: Any) -> Any:
    """Validate portfolio optimization result structure."""
    required_keys = [
        "optimization_method",
        "weights",
        "portfolio_metrics",
        "constraints_satisfied",
    ]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    assert_portfolio_weights_valid(result["weights"])
    metrics = result["portfolio_metrics"]
    required_metrics = ["expected_return", "volatility", "sharpe_ratio"]
    for metric in required_metrics:
        assert metric in metrics, f"Missing portfolio metric: {metric}"


def validate_performance_analysis_result(result: Any) -> Any:
    """Validate performance analysis result structure."""
    required_keys = ["performance_summary", "benchmark_comparison", "risk_metrics"]
    for key in required_keys:
        assert key in result, f"Missing key: {key}"
    assert_performance_metrics_reasonable(result["performance_summary"])
    benchmark_metrics = result["benchmark_comparison"]
    required_benchmark_metrics = [
        "beta",
        "alpha",
        "tracking_error",
        "information_ratio",
    ]
    for metric in required_benchmark_metrics:
        assert metric in benchmark_metrics, f"Missing benchmark metric: {metric}"
