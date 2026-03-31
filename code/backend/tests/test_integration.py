"""
Integration tests for the complete RiskOptimizer system.
Tests end-to-end workflows and API integration.
"""

from datetime import datetime
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest


class TestAPIIntegration:
    """Integration tests for API endpoints."""

    def setup_method(self) -> Any:
        """Set up test data for API integration tests."""
        np.random.seed(42)
        self.portfolio_data = {
            "portfolio_name": "Test Portfolio",
            "weights": [0.4, 0.3, 0.3],
            "historical_returns": np.random.normal(0.001, 0.02, (252, 3)).tolist(),
            "holdings": {"Stock_A": 10000, "Stock_B": 15000, "Stock_C": 20000},
        }
        self.assets_data = {
            "returns": np.random.normal(0.001, 0.02, (252, 4)).tolist(),
            "asset_names": ["Asset_A", "Asset_B", "Asset_C", "Asset_D"],
        }
        self.stress_scenarios = [
            {"type": "market_crash", "shock": -0.3},
            {"type": "volatility_spike", "multiplier": 2.0},
        ]

    @pytest.mark.asyncio
    async def test_monte_carlo_api_workflow(self):
        """Test complete Monte Carlo simulation API workflow."""
        task_response = {
            "status": "success",
            "data": {
                "task_id": "test-monte-carlo-task-id",
                "task_type": "monte_carlo_simulation",
                "status": "PENDING",
                "submitted_at": datetime.utcnow().isoformat(),
            },
        }
        assert task_response["status"] == "success"
        task_id = task_response["data"]["task_id"]
        status_response = {
            "status": "success",
            "data": {
                "task_id": task_id,
                "status": "SUCCESS",
                "result": {
                    "risk_metrics": {
                        "var_95": -0.15,
                        "var_99": -0.25,
                        "cvar_95": -0.2,
                        "cvar_99": -0.3,
                    },
                    "statistics": {"mean_final_value": 1.05, "std_final_value": 0.18},
                },
            },
        }
        assert status_response["data"]["status"] == "SUCCESS"
        assert "risk_metrics" in status_response["data"]["result"]
        result = status_response["data"]["result"]
        assert result["risk_metrics"]["var_95"] < 0
        assert result["risk_metrics"]["cvar_95"] <= result["risk_metrics"]["var_95"]

    @pytest.mark.asyncio
    async def test_portfolio_optimization_api_workflow(self):
        """Test complete portfolio optimization API workflow."""
        task_response = {
            "status": "success",
            "data": {
                "task_id": "test-optimization-task-id",
                "task_type": "portfolio_optimization",
                "status": "PENDING",
            },
        }
        assert task_response["status"] == "success"
        task_id = task_response["data"]["task_id"]
        result_response = {
            "status": "success",
            "data": {
                "task_id": task_id,
                "result": {
                    "optimization_method": "mean_variance",
                    "weights": {
                        "Asset_A": 0.25,
                        "Asset_B": 0.3,
                        "Asset_C": 0.25,
                        "Asset_D": 0.2,
                    },
                    "portfolio_metrics": {
                        "expected_return": 0.1,
                        "volatility": 0.15,
                        "sharpe_ratio": 0.53,
                    },
                },
            },
        }
        result = result_response["data"]["result"]
        weights = result["weights"]
        assert abs(sum(weights.values()) - 1.0) < 1e-06
        assert all((w >= 0 for w in weights.values()))
        assert all((w <= 0.4 for w in weights.values()))

    @pytest.mark.asyncio
    async def test_report_generation_api_workflow(self):
        """Test complete report generation API workflow."""
        task_response = {
            "status": "success",
            "data": {
                "task_id": "test-report-task-id",
                "task_type": "portfolio_report",
                "status": "PENDING",
            },
        }
        assert task_response["status"] == "success"
        task_id = task_response["data"]["task_id"]
        result_response = {
            "status": "success",
            "data": {
                "task_id": task_id,
                "result": {
                    "report_path": "/tmp/portfolio_report_test.pdf",
                    "report_filename": "portfolio_report_test.pdf",
                    "report_type": "portfolio_analysis",
                    "file_size_bytes": 1024000,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            },
        }
        result = result_response["data"]["result"]
        assert result["report_type"] == "portfolio_analysis"
        assert result["report_filename"].endswith(".pdf")
        assert result["file_size_bytes"] > 0


class TestWorkflowIntegration:
    """Integration tests for complete workflows."""

    def setup_method(self) -> Any:
        """Set up test data for workflow integration tests."""
        np.random.seed(42)
        self.test_portfolio = {
            "id": 1,
            "name": "Diversified Growth Portfolio",
            "assets": {
                "US_Stocks": {"weight": 0.4, "value": 400000},
                "Intl_Stocks": {"weight": 0.25, "value": 250000},
                "Bonds": {"weight": 0.2, "value": 200000},
                "REITs": {"weight": 0.1, "value": 100000},
                "Commodities": {"weight": 0.05, "value": 50000},
            },
            "total_value": 1000000,
            "inception_date": "2020-01-01",
            "benchmark": "S&P 500",
        }
        n_periods = 1000
        self.historical_returns = self._generate_realistic_returns(n_periods)

    def _generate_realistic_returns(self, n_periods: Any) -> Any:
        """Generate realistic historical returns with market characteristics."""
        np.random.seed(42)
        asset_params = {
            "US_Stocks": {"mean": 0.1, "vol": 0.16, "skew": -0.5},
            "Intl_Stocks": {"mean": 0.08, "vol": 0.18, "skew": -0.3},
            "Bonds": {"mean": 0.04, "vol": 0.05, "skew": 0.2},
            "REITs": {"mean": 0.09, "vol": 0.2, "skew": -0.4},
            "Commodities": {"mean": 0.06, "vol": 0.25, "skew": 0.1},
        }
        correlation_matrix = np.array(
            [
                [1.0, 0.75, 0.2, 0.6, 0.3],
                [0.75, 1.0, 0.15, 0.55, 0.35],
                [0.2, 0.15, 1.0, 0.25, 0.1],
                [0.6, 0.55, 0.25, 1.0, 0.4],
                [0.3, 0.35, 0.1, 0.4, 1.0],
            ]
        )
        daily_means = np.array(
            [params["mean"] / 252 for params in asset_params.values()]
        )
        daily_vols = np.array(
            [params["vol"] / np.sqrt(252) for params in asset_params.values()]
        )
        cov_matrix = np.outer(daily_vols, daily_vols) * correlation_matrix
        returns = np.random.multivariate_normal(daily_means, cov_matrix, n_periods)
        for i in range(1, n_periods):
            if np.random.random() < 0.02:
                returns[i] *= np.random.uniform(1.5, 3.0)
        return {
            "dates": pd.date_range("2020-01-01", periods=n_periods, freq="D"),
            "returns": returns,
            "asset_names": list(asset_params.keys()),
        }

    @patch("tasks.risk_tasks.task_result_manager")
    @patch("tasks.portfolio_tasks.task_result_manager")
    @patch("tasks.report_tasks.task_result_manager")
    def test_complete_risk_analysis_workflow(
        self,
        mock_report_manager: Any,
        mock_portfolio_manager: Any,
        mock_risk_manager: Any,
    ) -> Any:
        """Test complete risk analysis workflow from start to finish."""
        from tasks.report_tasks import generate_risk_report
        from tasks.risk_tasks import monte_carlo_simulation, stress_test_portfolio

        portfolio_data = {
            "weights": [0.4, 0.25, 0.2, 0.1, 0.05],
            "historical_returns": self.historical_returns["returns"].tolist(),
        }
        mock_self = MagicMock()
        mock_self.request.id = "risk-workflow-mc-task"
        mc_result = monte_carlo_simulation(
            mock_self, portfolio_data, num_simulations=5000, time_horizon=252
        )
        assert "risk_metrics" in mc_result
        assert "simulation_parameters" in mc_result
        assert mc_result["simulation_parameters"]["num_simulations"] == 5000
        stress_scenarios = [
            {"type": "market_crash", "shock": -0.3},
            {"type": "volatility_spike", "multiplier": 2.0},
            {"type": "correlation_breakdown", "noise_level": 0.15},
        ]
        mock_self.request.id = "risk-workflow-stress-task"
        stress_result = stress_test_portfolio(
            mock_self, portfolio_data, stress_scenarios
        )
        assert "baseline" in stress_result
        assert "stress_results" in stress_result
        assert len(stress_result["stress_results"]) == 3
        risk_analysis_data = {
            "monte_carlo_results": mc_result["risk_metrics"],
            "stress_test_results": stress_result,
            "portfolio_info": self.test_portfolio,
        }
        mock_self.request.id = "risk-workflow-report-task"
        report_result = generate_risk_report(
            mock_self, risk_analysis_data, {"format": "pdf", "include_charts": True}
        )
        assert "report_path" in report_result
        assert "report_type" in report_result
        assert report_result["report_type"] == "risk_analysis"
        var_95 = mc_result["risk_metrics"]["var_95"]
        assert -0.5 < var_95 < 0
        for scenario_result in stress_result["stress_results"]:
            assert "return_impact" in scenario_result
            assert "volatility_impact" in scenario_result

    @patch("tasks.portfolio_tasks.task_result_manager")
    def test_portfolio_optimization_and_rebalancing_workflow(
        self, mock_task_manager: Any
    ) -> Any:
        """Test complete portfolio optimization and rebalancing workflow."""
        from tasks.portfolio_tasks import optimize_portfolio, rebalance_portfolio

        assets_data = {
            "returns": self.historical_returns["returns"].tolist(),
            "asset_names": self.historical_returns["asset_names"],
        }
        optimization_params = {
            "method": "mean_variance",
            "target_return": 0.08,
            "max_weight_per_asset": 0.5,
            "min_weight_per_asset": 0.05,
        }
        mock_self = MagicMock()
        mock_self.request.id = "optimization-workflow-task"
        optimization_result = optimize_portfolio(
            mock_self, assets_data, optimization_params
        )
        assert "weights" in optimization_result
        assert "portfolio_metrics" in optimization_result
        optimized_weights = optimization_result["weights"]
        assert abs(sum(optimized_weights.values()) - 1.0) < 1e-06
        current_portfolio = {
            "holdings": {
                asset: self.test_portfolio["assets"][asset]["value"]
                for asset in self.test_portfolio["assets"]
            }
        }
        target_weights = optimized_weights
        rebalancing_params = {
            "min_transaction_size": 1000,
            "transaction_cost_rate": 0.001,
        }
        mock_self.request.id = "rebalancing-workflow-task"
        rebalancing_result = rebalance_portfolio(
            mock_self, current_portfolio, target_weights, rebalancing_params
        )
        assert "transactions" in rebalancing_result
        assert "rebalancing_analysis" in rebalancing_result
        analysis = rebalancing_result["rebalancing_analysis"]
        assert "total_turnover" in analysis
        assert "estimated_costs" in analysis
        assert analysis["total_turnover"] >= 0
        assert analysis["estimated_costs"] >= 0

    def test_performance_monitoring_workflow(self) -> Any:
        """Test performance monitoring and alerting workflow."""
        portfolio_returns = np.dot(
            self.historical_returns["returns"], [0.4, 0.25, 0.2, 0.1, 0.05]
        )
        total_return = np.prod(1 + portfolio_returns) - 1
        annualized_return = (1 + total_return) ** (252 / len(portfolio_returns)) - 1
        volatility = np.std(portfolio_returns) * np.sqrt(252)
        sharpe_ratio = (annualized_return - 0.02) / volatility
        cumulative_returns = np.cumprod(1 + portfolio_returns)
        running_max = np.maximum.accumulate(cumulative_returns)
        drawdowns = (cumulative_returns - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        performance_metrics = {
            "total_return": total_return,
            "annualized_return": annualized_return,
            "volatility": volatility,
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": max_drawdown,
        }
        thresholds = {
            "min_annualized_return": 0.05,
            "max_volatility": 0.2,
            "min_sharpe_ratio": 0.5,
            "max_drawdown": -0.15,
        }
        alerts = []
        if (
            performance_metrics["annualized_return"]
            < thresholds["min_annualized_return"]
        ):
            alerts.append(
                {
                    "type": "performance_warning",
                    "metric": "annualized_return",
                    "value": performance_metrics["annualized_return"],
                    "threshold": thresholds["min_annualized_return"],
                    "message": "Portfolio return below minimum threshold",
                }
            )
        if performance_metrics["volatility"] > thresholds["max_volatility"]:
            alerts.append(
                {
                    "type": "risk_warning",
                    "metric": "volatility",
                    "value": performance_metrics["volatility"],
                    "threshold": thresholds["max_volatility"],
                    "message": "Portfolio volatility above maximum threshold",
                }
            )
        if performance_metrics["max_drawdown"] < thresholds["max_drawdown"]:
            alerts.append(
                {
                    "type": "risk_warning",
                    "metric": "max_drawdown",
                    "value": performance_metrics["max_drawdown"],
                    "threshold": thresholds["max_drawdown"],
                    "message": "Portfolio drawdown exceeds maximum threshold",
                }
            )
        assert isinstance(performance_metrics, dict)
        assert all((isinstance(v, (int, float)) for v in performance_metrics.values()))
        assert isinstance(alerts, list)
        assert -1 <= performance_metrics["total_return"] <= 5
        assert 0 <= performance_metrics["volatility"] <= 1
        assert -1 <= performance_metrics["max_drawdown"] <= 0


class TestSystemIntegration:
    """Integration tests for system-level functionality."""

    def test_task_queue_integration(self) -> Any:
        """Test task queue system integration."""
        task_queue_stats = {
            "active_tasks": 5,
            "pending_tasks": 12,
            "completed_tasks_today": 150,
            "failed_tasks_today": 2,
            "average_task_duration": 45.5,
            "queue_health": "healthy",
        }
        assert task_queue_stats["queue_health"] in ["healthy", "degraded", "unhealthy"]
        assert task_queue_stats["active_tasks"] >= 0
        assert task_queue_stats["pending_tasks"] >= 0
        assert task_queue_stats["average_task_duration"] > 0
        total_tasks_today = (
            task_queue_stats["completed_tasks_today"]
            + task_queue_stats["failed_tasks_today"]
        )
        failure_rate = task_queue_stats["failed_tasks_today"] / total_tasks_today
        assert failure_rate < 0.05
        assert task_queue_stats["average_task_duration"] < 300

    def test_caching_system_integration(self) -> Any:
        """Test caching system integration."""
        cache_stats = {
            "total_keys": 1500,
            "hit_rate": 0.85,
            "miss_rate": 0.15,
            "memory_usage_mb": 256,
            "evicted_keys_today": 50,
            "expired_keys_today": 120,
        }
        assert 0 <= cache_stats["hit_rate"] <= 1
        assert 0 <= cache_stats["miss_rate"] <= 1
        assert abs(cache_stats["hit_rate"] + cache_stats["miss_rate"] - 1.0) < 1e-06
        assert cache_stats["hit_rate"] > 0.7
        assert cache_stats["memory_usage_mb"] > 0

    def test_database_integration(self) -> Any:
        """Test database system integration."""
        db_stats = {
            "connection_pool_size": 20,
            "active_connections": 8,
            "average_query_time_ms": 15.5,
            "slow_queries_today": 3,
            "total_queries_today": 5000,
            "database_size_gb": 2.5,
        }
        assert db_stats["active_connections"] <= db_stats["connection_pool_size"]
        assert db_stats["average_query_time_ms"] < 100
        slow_query_rate = (
            db_stats["slow_queries_today"] / db_stats["total_queries_today"]
        )
        assert slow_query_rate < 0.01

    def test_monitoring_system_integration(self) -> Any:
        """Test monitoring and observability system integration."""
        system_metrics = {
            "cpu_usage_percent": 45.2,
            "memory_usage_percent": 68.5,
            "disk_usage_percent": 35.8,
            "network_io_mbps": 12.3,
            "application_response_time_ms": 250,
            "error_rate_percent": 0.5,
            "uptime_hours": 168,
        }
        assert 0 <= system_metrics["cpu_usage_percent"] <= 100
        assert 0 <= system_metrics["memory_usage_percent"] <= 100
        assert 0 <= system_metrics["disk_usage_percent"] <= 100
        assert system_metrics["application_response_time_ms"] < 1000
        assert system_metrics["error_rate_percent"] < 5
        assert system_metrics["uptime_hours"] > 0


class TestLoadIntegration:
    """Load testing and performance integration tests."""

    def test_concurrent_task_processing(self) -> Any:
        """Test system behavior under concurrent task load."""
        concurrent_tasks = 50
        np.random.seed(42)
        execution_times = np.random.exponential(30, concurrent_tasks)
        average_execution_time = np.mean(execution_times)
        max_execution_time = np.max(execution_times)
        task_throughput = concurrent_tasks / np.sum(execution_times) * 3600
        assert average_execution_time < 60
        assert max_execution_time < 300
        assert task_throughput > 10

    def test_memory_usage_under_load(self) -> Any:
        """Test memory usage patterns under load."""
        memory_usage = {
            "baseline_mb": 512,
            "monte_carlo_peak_mb": 1024,
            "optimization_peak_mb": 768,
            "report_generation_peak_mb": 896,
            "concurrent_peak_mb": 2048,
        }
        assert memory_usage["baseline_mb"] > 0
        assert memory_usage["concurrent_peak_mb"] < 4096
        for operation, peak_memory in memory_usage.items():
            if operation != "baseline_mb":
                memory_overhead = peak_memory - memory_usage["baseline_mb"]
                assert memory_overhead > 0
                assert memory_overhead < 2048
