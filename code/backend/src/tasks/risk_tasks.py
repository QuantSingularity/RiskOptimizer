"""
Risk calculation tasks for asynchronous processing.
Handles Monte Carlo simulations, VaR calculations, and other heavy computations.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from src.tasks.celery_app import (
    TaskValidationError,
    celery_app,
    task_result_manager,
    task_with_progress,
)

logger = logging.getLogger(__name__)


@task_with_progress()
def monte_carlo_simulation(
    self, portfolio_data: Dict, num_simulations: int = 10000, time_horizon: int = 252
) -> Dict[str, Any]:
    """
    Perform Monte Carlo simulation for portfolio risk analysis.

    Args:
        portfolio_data: Portfolio allocation and historical data
        num_simulations: Number of simulation runs
        time_horizon: Time horizon in days

    Returns:
        Dict containing simulation results and statistics
    """
    try:
        # Validate inputs
        if num_simulations <= 0 or num_simulations > 100000:
            raise TaskValidationError(
                "Number of simulations must be between 1 and 100,000"
            )

        if time_horizon <= 0 or time_horizon > 1000:
            raise TaskValidationError("Time horizon must be between 1 and 1,000 days")

        # Update progress
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 10, "status": "Initializing simulation parameters"},
        )

        # Extract portfolio data
        weights = np.array(portfolio_data["weights"])
        returns = np.array(portfolio_data["historical_returns"])

        # Calculate portfolio statistics
        portfolio_returns = np.dot(returns, weights)
        mean_return = np.mean(portfolio_returns)
        volatility = np.std(portfolio_returns)

        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 30, "status": "Running Monte Carlo simulations"},
        )

        # Generate random scenarios
        np.random.seed(42)  # For reproducible results
        random_returns = np.random.normal(
            mean_return, volatility, (num_simulations, time_horizon)
        )

        # Calculate cumulative returns for each simulation
        cumulative_returns = np.cumprod(1 + random_returns, axis=1)
        final_values = cumulative_returns[:, -1]

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 70, "status": "Calculating risk metrics"}
        )

        # Calculate risk metrics
        var_95 = np.percentile(final_values, 5)
        var_99 = np.percentile(final_values, 1)
        cvar_95 = np.mean(final_values[final_values <= var_95])
        cvar_99 = np.mean(final_values[final_values <= var_99])

        # Calculate additional statistics
        max_drawdown = np.min(cumulative_returns, axis=1)
        probability_of_loss = np.sum(final_values < 1) / num_simulations

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 90, "status": "Finalizing results"}
        )

        # Prepare results
        results = {
            "simulation_parameters": {
                "num_simulations": num_simulations,
                "time_horizon": time_horizon,
                "portfolio_mean_return": float(mean_return),
                "portfolio_volatility": float(volatility),
            },
            "risk_metrics": {
                "var_95": float(var_95 - 1),
                "var_99": float(var_99 - 1),
                "cvar_95": float(cvar_95 - 1),
                "cvar_99": float(cvar_99 - 1),
                "probability_of_loss": float(probability_of_loss),
            },
            "statistics": {
                "mean_final_value": float(np.mean(final_values)),
                "median_final_value": float(np.median(final_values)),
                "std_final_value": float(np.std(final_values)),
                "min_final_value": float(np.min(final_values)),
                "max_final_value": float(np.max(final_values)),
                "mean_max_drawdown": float(np.mean(max_drawdown)),
            },
            "percentiles": {
                f"p{p}": float(np.percentile(final_values, p))
                for p in [1, 5, 10, 25, 50, 75, 90, 95, 99]
            },
            "simulation_data": {
                "final_values": final_values.tolist()[
                    :1000
                ],  # Limit to first 1000 for storage
                "max_drawdowns": max_drawdown.tolist()[:1000],
            },
            "metadata": {
                "completed_at": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
            },
        }

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 100, "status": "Completed successfully"}
        )

        logger.info(f"Monte Carlo simulation completed for task {self.request.id}")
        return results

    except Exception as e:
        logger.error(
            f"Monte Carlo simulation failed for task {self.request.id}: {str(e)}"
        )
        task_result_manager.store_task_progress(
            self.request.id, {"progress": 0, "status": f"Failed: {str(e)}"}
        )
        raise


@task_with_progress()
def calculate_var_cvar(
    self, portfolio_data: Dict, confidence_levels: List[float] = [0.95, 0.99]
) -> Dict[str, Any]:
    """
    Calculate Value at Risk (VaR) and Conditional Value at Risk (CVaR) for a portfolio.

    Args:
        portfolio_data: Portfolio allocation and historical data
        confidence_levels: List of confidence levels for VaR/CVaR calculation

    Returns:
        Dict containing VaR and CVaR values
    """
    try:
        # Validate inputs
        for level in confidence_levels:
            if not 0 < level < 1:
                raise TaskValidationError("Confidence levels must be between 0 and 1")

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 20, "status": "Calculating portfolio returns"}
        )

        # Extract portfolio data
        weights = np.array(portfolio_data["weights"])
        returns = np.array(portfolio_data["historical_returns"])

        # Calculate portfolio returns
        portfolio_returns = np.dot(returns, weights)

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 60, "status": "Calculating VaR and CVaR"}
        )

        results = {
            "var": {},
            "cvar": {},
            "statistics": {
                "mean_return": float(np.mean(portfolio_returns)),
                "volatility": float(np.std(portfolio_returns)),
                "skewness": float(pd.Series(portfolio_returns).skew()),
                "kurtosis": float(pd.Series(portfolio_returns).kurtosis()),
            },
        }

        # Calculate VaR and CVaR for each confidence level
        for level in confidence_levels:
            var_value = np.percentile(portfolio_returns, (1 - level) * 100)
            cvar_value = np.mean(portfolio_returns[portfolio_returns <= var_value])

            results["var"][f"{level:.0%}"] = float(var_value)
            results["cvar"][f"{level:.0%}"] = float(cvar_value)

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 100, "status": "Completed successfully"}
        )

        logger.info(f"VaR/CVaR calculation completed for task {self.request.id}")
        return results

    except Exception as e:
        logger.error(
            f"VaR/CVaR calculation failed for task {self.request.id}: {str(e)}"
        )
        raise


@task_with_progress()
def efficient_frontier_calculation(
    self, assets_data: Dict, num_portfolios: int = 10000
) -> Dict[str, Any]:
    """
    Calculate the efficient frontier for a set of assets.

    Args:
        assets_data: Historical returns data for assets
        num_portfolios: Number of random portfolios to generate

    Returns:
        Dict containing efficient frontier data
    """
    try:
        # Validate inputs
        if num_portfolios <= 0 or num_portfolios > 50000:
            raise TaskValidationError(
                "Number of portfolios must be between 1 and 50,000"
            )

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 10, "status": "Processing asset data"}
        )

        # Extract returns data
        returns_df = pd.DataFrame(assets_data["returns"])
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 30, "status": "Generating random portfolios"}
        )

        # Generate random portfolios
        num_assets = len(mean_returns)
        results_array = np.zeros((3, num_portfolios))
        weights_array = np.zeros((num_portfolios, num_assets))

        np.random.seed(42)

        for i in range(num_portfolios):
            # Generate random weights
            weights = np.random.random(num_assets)
            weights /= np.sum(weights)  # Normalize to sum to 1

            weights_array[i] = weights

            # Calculate portfolio return and volatility
            portfolio_return = np.sum(mean_returns * weights) * 252  # Annualized
            portfolio_volatility = np.sqrt(
                np.dot(weights.T, np.dot(cov_matrix, weights))
            ) * np.sqrt(252)

            # Calculate Sharpe ratio (assuming risk-free rate of 2%)
            risk_free_rate = 0.02
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility

            results_array[0, i] = portfolio_return
            results_array[1, i] = portfolio_volatility
            results_array[2, i] = sharpe_ratio

            # Update progress
            if i % (num_portfolios // 10) == 0:
                progress = 30 + (i / num_portfolios) * 50
                task_result_manager.store_task_progress(
                    self.request.id,
                    {
                        "progress": int(progress),
                        "status": f"Generated {i}/{num_portfolios} portfolios",
                    },
                )

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 90, "status": "Finding optimal portfolios"}
        )

        # Find optimal portfolios
        max_sharpe_idx = np.argmax(results_array[2])
        min_vol_idx = np.argmin(results_array[1])

        # Prepare results
        results = {
            "portfolios": {
                "returns": results_array[0].tolist(),
                "volatilities": results_array[1].tolist(),
                "sharpe_ratios": results_array[2].tolist(),
            },
            "optimal_portfolios": {
                "max_sharpe": {
                    "weights": weights_array[max_sharpe_idx].tolist(),
                    "return": float(results_array[0, max_sharpe_idx]),
                    "volatility": float(results_array[1, max_sharpe_idx]),
                    "sharpe_ratio": float(results_array[2, max_sharpe_idx]),
                },
                "min_volatility": {
                    "weights": weights_array[min_vol_idx].tolist(),
                    "return": float(results_array[0, min_vol_idx]),
                    "volatility": float(results_array[1, min_vol_idx]),
                    "sharpe_ratio": float(results_array[2, min_vol_idx]),
                },
            },
            "statistics": {
                "num_portfolios": num_portfolios,
                "mean_return": float(np.mean(results_array[0])),
                "mean_volatility": float(np.mean(results_array[1])),
                "mean_sharpe": float(np.mean(results_array[2])),
            },
            "metadata": {
                "completed_at": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
            },
        }

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 100, "status": "Completed successfully"}
        )

        logger.info(
            f"Efficient frontier calculation completed for task {self.request.id}"
        )
        return results

    except Exception as e:
        logger.error(
            f"Efficient frontier calculation failed for task {self.request.id}: {str(e)}"
        )
        raise


@task_with_progress()
def stress_test_portfolio(
    self, portfolio_data: Dict, stress_scenarios: List[Dict]
) -> Dict[str, Any]:
    """
    Perform stress testing on a portfolio using various market scenarios.

    Args:
        portfolio_data: Portfolio allocation and historical data
        stress_scenarios: List of stress scenarios to apply

    Returns:
        Dict containing stress test results
    """
    try:
        task_result_manager.store_task_progress(
            self.request.id, {"progress": 10, "status": "Initializing stress test"}
        )

        # Extract portfolio data
        weights = np.array(portfolio_data["weights"])
        returns = np.array(portfolio_data["historical_returns"])

        # Calculate baseline portfolio metrics
        portfolio_returns = np.dot(returns, weights)
        baseline_return = np.mean(portfolio_returns)
        baseline_volatility = np.std(portfolio_returns)

        results = {
            "baseline": {
                "return": float(baseline_return),
                "volatility": float(baseline_volatility),
            },
            "stress_results": [],
        }

        # Apply each stress scenario
        for i, scenario in enumerate(stress_scenarios):
            task_result_manager.store_task_progress(
                self.request.id,
                {
                    "progress": 10 + (i / len(stress_scenarios)) * 80,
                    "status": f"Applying stress scenario {i+1}/{len(stress_scenarios)}",
                },
            )

            # Apply stress scenario
            stressed_returns = returns.copy()

            # Apply shocks based on scenario type
            if scenario["type"] == "market_crash":
                shock = scenario.get("shock", -0.3)  # Default 30% crash
                stressed_returns = stressed_returns + shock
            elif scenario["type"] == "volatility_spike":
                vol_multiplier = scenario.get(
                    "multiplier", 2.0
                )  # Default 2x volatility
                stressed_returns = stressed_returns * vol_multiplier
            elif scenario["type"] == "correlation_breakdown":
                # Simulate correlation breakdown by adding random noise
                noise_level = scenario.get("noise_level", 0.1)
                noise = np.random.normal(0, noise_level, stressed_returns.shape)
                stressed_returns = stressed_returns + noise

            # Calculate stressed portfolio metrics
            stressed_portfolio_returns = np.dot(stressed_returns, weights)
            stressed_return = np.mean(stressed_portfolio_returns)
            stressed_volatility = np.std(stressed_portfolio_returns)

            # Calculate impact
            return_impact = stressed_return - baseline_return
            volatility_impact = stressed_volatility - baseline_volatility

            scenario_result = {
                "scenario": scenario,
                "stressed_return": float(stressed_return),
                "stressed_volatility": float(stressed_volatility),
                "return_impact": float(return_impact),
                "volatility_impact": float(volatility_impact),
                "relative_return_impact": (
                    float(return_impact / baseline_return)
                    if baseline_return != 0
                    else 0
                ),
                "relative_volatility_impact": (
                    float(volatility_impact / baseline_volatility)
                    if baseline_volatility != 0
                    else 0
                ),
            }

            results["stress_results"].append(scenario_result)

        task_result_manager.store_task_progress(
            self.request.id, {"progress": 100, "status": "Completed successfully"}
        )

        logger.info(f"Stress test completed for task {self.request.id}")
        return results

    except Exception as e:
        logger.error(f"Stress test failed for task {self.request.id}: {str(e)}")
        raise


@celery_app.task()
def calculate_portfolio_metrics(
    portfolio_id: int, metrics: List[str]
) -> Dict[str, Any]:
    """
    Calculate various portfolio metrics asynchronously.

    Args:
        portfolio_id: ID of the portfolio to analyze
        metrics: List of metrics to calculate

    Returns:
        Dict containing calculated metrics
    """
    try:
        # This would typically fetch portfolio data from database
        # For now, using placeholder logic

        available_metrics = [
            "sharpe_ratio",
            "sortino_ratio",
            "calmar_ratio",
            "max_drawdown",
            "beta",
            "alpha",
            "treynor_ratio",
            "information_ratio",
        ]

        results = {}

        for metric in metrics:
            if metric not in available_metrics:
                continue

            # Placeholder calculations - would be replaced with actual implementations
            if metric == "sharpe_ratio":
                results[metric] = 1.2
            elif metric == "sortino_ratio":
                results[metric] = 1.5
            elif metric == "max_drawdown":
                results[metric] = -0.15
            # Add other metric calculations...

        return {
            "portfolio_id": portfolio_id,
            "metrics": results,
            "calculated_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Portfolio metrics calculation failed: {str(e)}")
        raise
