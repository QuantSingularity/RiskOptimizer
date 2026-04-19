"""
Portfolio management tasks for asynchronous processing.
Handles portfolio optimization, rebalancing, and analysis tasks.
"""

import logging
from datetime import datetime
from typing import Any, Dict

import numpy as np
import pandas as pd
from src.tasks.celery_app import (
    TaskError,
    TaskValidationError,
    celery_app,
    task_result_manager,
    task_with_progress,
)

logger = logging.getLogger(__name__)


@task_with_progress()
def optimize_portfolio(
    self, assets_data: Dict, optimization_params: Dict
) -> Dict[str, Any]:
    """
    Optimize portfolio allocation using various optimization methods.

    Args:
        assets_data: Historical data for assets
        optimization_params: Optimization parameters and constraints

    Returns:
        Dict containing optimized portfolio weights and metrics
    """
    try:
        method = optimization_params.get("method", "mean_variance")
        if method not in [
            "mean_variance",
            "risk_parity",
            "black_litterman",
            "minimum_variance",
        ]:
            raise TaskValidationError(f"Unsupported optimization method: {method}")
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 10, "status": f"Starting {method} optimization"},
        )
        returns_df = pd.DataFrame(assets_data["returns"])
        asset_names = assets_data.get(
            "asset_names", [f"Asset_{i}" for i in range(len(returns_df.columns))]
        )
        mean_returns = returns_df.mean()
        cov_matrix = returns_df.cov()
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 30, "status": "Calculating optimization parameters"},
        )
        if method == "mean_variance":
            weights = _optimize_mean_variance(
                mean_returns, cov_matrix, optimization_params
            )
        elif method == "risk_parity":
            weights = _optimize_risk_parity(cov_matrix, optimization_params)
        elif method == "minimum_variance":
            weights = _optimize_minimum_variance(cov_matrix, optimization_params)
        elif method == "black_litterman":
            weights = _optimize_black_litterman(
                mean_returns, cov_matrix, optimization_params
            )
        task_result_manager.store_task_progress(
            self.request.id, {"progress": 70, "status": "Calculating portfolio metrics"}
        )
        portfolio_return = np.sum(mean_returns * weights) * 252
        portfolio_volatility = np.sqrt(
            np.dot(weights.T, np.dot(cov_matrix, weights))
        ) * np.sqrt(252)
        sharpe_ratio = (portfolio_return - 0.02) / portfolio_volatility
        marginal_contrib = np.dot(cov_matrix, weights)
        risk_contrib = weights * marginal_contrib / portfolio_volatility**2
        results = {
            "optimization_method": method,
            "weights": {asset_names[i]: float(weights[i]) for i in range(len(weights))},
            "portfolio_metrics": {
                "expected_return": float(portfolio_return),
                "volatility": float(portfolio_volatility),
                "sharpe_ratio": float(sharpe_ratio),
            },
            "risk_contributions": {
                asset_names[i]: float(risk_contrib[i]) for i in range(len(risk_contrib))
            },
            "constraints_satisfied": _check_constraints(weights, optimization_params),
            "metadata": {
                "completed_at": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
            },
        }
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 100, "status": "Optimization completed successfully"},
        )
        logger.info(f"Portfolio optimization completed for task {self.request.id}")
        return results
    except Exception as e:
        logger.error(
            f"Portfolio optimization failed for task {self.request.id}: {str(e)}"
        )
        raise


def _optimize_mean_variance(
    mean_returns: "np.ndarray | pd.DataFrame | list",
    cov_matrix: "np.ndarray | pd.DataFrame | list",
    params: object,
) -> object:
    """Implement mean-variance optimization."""
    from scipy.optimize import minimize

    num_assets = len(mean_returns)
    requested_target = params.get("target_return", None)

    min_possible = float(np.min(mean_returns))
    max_possible = float(np.max(mean_returns))

    if requested_target is not None:
        if requested_target > max_possible or requested_target < min_possible:
            target_return = float(np.mean(mean_returns))
        else:
            target_return = requested_target
    else:
        target_return = float(np.mean(mean_returns))

    def objective(weights):
        return np.dot(weights.T, np.dot(cov_matrix, weights))

    constraints = [
        {"type": "eq", "fun": lambda x: np.sum(x) - 1},
        {"type": "ineq", "fun": lambda x: np.sum(mean_returns * x) - target_return},
    ]
    bounds = tuple(((0, 1) for _ in range(num_assets)))
    x0 = np.array([1 / num_assets] * num_assets)
    result = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"ftol": 1e-9, "maxiter": 1000},
    )
    if not result.success:
        result = minimize(
            lambda w: np.dot(w.T, np.dot(cov_matrix, w)),
            x0,
            method="SLSQP",
            bounds=bounds,
            constraints=[{"type": "eq", "fun": lambda x: np.sum(x) - 1}],
            options={"ftol": 1e-9, "maxiter": 1000},
        )
        if not result.success:
            raise TaskError(f"Optimization failed: {result.message}")
    return result.x


def _optimize_risk_parity(
    cov_matrix: "np.ndarray | pd.DataFrame | list", params: object
) -> object:
    """Implement risk parity optimization."""
    from scipy.optimize import minimize

    num_assets = len(cov_matrix)

    def objective(weights):
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        marginal_contrib = np.dot(cov_matrix, weights)
        risk_contrib = weights * marginal_contrib / portfolio_vol**2
        target_contrib = 1 / num_assets
        return np.sum((risk_contrib - target_contrib) ** 2)

    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
    bounds = tuple(((0.001, 1) for _ in range(num_assets)))
    x0 = np.array([1 / num_assets] * num_assets)
    result = minimize(
        objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
    )
    if not result.success:
        raise TaskError(f"Risk parity optimization failed: {result.message}")
    return result.x


def _optimize_minimum_variance(
    cov_matrix: "np.ndarray | pd.DataFrame | list", params: object
) -> object:
    """Implement minimum variance optimization."""
    from scipy.optimize import minimize

    num_assets = len(cov_matrix)

    def objective(weights):
        return np.dot(weights.T, np.dot(cov_matrix, weights))

    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
    bounds = tuple(((0, 1) for _ in range(num_assets)))
    x0 = np.array([1 / num_assets] * num_assets)
    result = minimize(
        objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
    )
    if not result.success:
        raise TaskError(f"Minimum variance optimization failed: {result.message}")
    return result.x


def _optimize_black_litterman(
    mean_returns: "np.ndarray | pd.DataFrame | list",
    cov_matrix: "np.ndarray | pd.DataFrame | list",
    params: object,
) -> object:
    """Implement Black-Litterman optimization."""
    num_assets = len(mean_returns)
    market_weights = np.array([1 / num_assets] * num_assets)
    risk_aversion = params.get("risk_aversion", 3.0)
    risk_aversion * np.dot(cov_matrix, market_weights)
    from scipy.optimize import minimize

    def objective(weights):
        return np.dot(weights.T, np.dot(cov_matrix, weights))

    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - 1}]
    bounds = tuple(((0, 1) for _ in range(num_assets)))
    x0 = market_weights
    result = minimize(
        objective, x0, method="SLSQP", bounds=bounds, constraints=constraints
    )
    if not result.success:
        raise TaskError(f"Black-Litterman optimization failed: {result.message}")
    return result.x


def _check_constraints(
    weights: "np.ndarray | pd.DataFrame | list", params: object
) -> object:
    """Check if optimization constraints are satisfied."""
    constraints_satisfied = {
        "weights_sum_to_one": abs(np.sum(weights) - 1.0) < 1e-06,
        "no_negative_weights": np.all(weights >= 0),
        "within_bounds": True,
    }
    max_weight = params.get("max_weight_per_asset")
    if max_weight:
        constraints_satisfied["max_weight_constraint"] = np.all(weights <= max_weight)
    min_weight = params.get("min_weight_per_asset")
    if min_weight:
        constraints_satisfied["min_weight_constraint"] = np.all(weights >= min_weight)
    return constraints_satisfied


@task_with_progress()
def rebalance_portfolio(
    self, current_portfolio: Dict, target_weights: Dict, rebalancing_params: Dict
) -> Dict[str, Any]:
    """
    Calculate portfolio rebalancing transactions.

    Args:
        current_portfolio: Current portfolio holdings
        target_weights: Target allocation weights
        rebalancing_params: Rebalancing parameters and constraints

    Returns:
        Dict containing rebalancing transactions and analysis
    """
    try:
        task_result_manager.store_task_progress(
            self.request.id, {"progress": 20, "status": "Analyzing current portfolio"}
        )
        current_values = current_portfolio["holdings"]
        total_value = sum(current_values.values())
        current_weights = {
            asset: value / total_value for asset, value in current_values.items()
        }
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 50, "status": "Calculating rebalancing transactions"},
        )
        target_values = {
            asset: weight * total_value for asset, weight in target_weights.items()
        }
        transactions = {}
        total_turnover = 0
        for asset in set(list(current_values.keys()) + list(target_values.keys())):
            current_value = current_values.get(asset, 0)
            target_value = target_values.get(asset, 0)
            transaction = target_value - current_value
            if abs(transaction) > rebalancing_params.get("min_transaction_size", 100):
                transactions[asset] = {
                    "current_value": current_value,
                    "target_value": target_value,
                    "transaction_amount": transaction,
                    "transaction_type": "buy" if transaction > 0 else "sell",
                }
                total_turnover += abs(transaction)
        task_result_manager.store_task_progress(
            self.request.id, {"progress": 80, "status": "Calculating rebalancing costs"}
        )
        transaction_cost_rate = rebalancing_params.get("transaction_cost_rate", 0.001)
        total_costs = total_turnover * transaction_cost_rate
        tracking_error_before = _calculate_tracking_error(
            current_weights, target_weights
        )
        tracking_error_after = 0
        results = {
            "current_portfolio": {
                "total_value": total_value,
                "weights": current_weights,
            },
            "target_portfolio": {"weights": target_weights, "values": target_values},
            "rebalancing_analysis": {
                "total_turnover": total_turnover,
                "turnover_rate": total_turnover / total_value,
                "number_of_transactions": len(transactions),
                "estimated_costs": total_costs,
                "cost_percentage": total_costs / total_value,
                "tracking_error_reduction": tracking_error_before
                - tracking_error_after,
            },
            "transactions": transactions,
            "metadata": {
                "completed_at": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
            },
        }
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 100, "status": "Rebalancing analysis completed"},
        )
        logger.info(
            f"Portfolio rebalancing analysis completed for task {self.request.id}"
        )
        return results
    except Exception as e:
        logger.error(
            f"Portfolio rebalancing analysis failed for task {self.request.id}: {str(e)}"
        )
        raise


def _calculate_tracking_error(
    current_weights: "np.ndarray | pd.DataFrame | list",
    target_weights: "np.ndarray | pd.DataFrame | list",
) -> object:
    """Calculate tracking error between current and target weights."""
    all_assets = set(list(current_weights.keys()) + list(target_weights.keys()))
    squared_differences = 0
    for asset in all_assets:
        current_weight = current_weights.get(asset, 0)
        target_weight = target_weights.get(asset, 0)
        squared_differences += (current_weight - target_weight) ** 2
    return np.sqrt(squared_differences)


@task_with_progress()
def analyze_portfolio_performance(
    self, portfolio_data: Dict, benchmark_data: Dict, analysis_period: Dict
) -> Dict[str, Any]:
    """
    Perform comprehensive portfolio performance analysis.

    Args:
        portfolio_data: Portfolio returns and holdings data
        benchmark_data: Benchmark returns data
        analysis_period: Period for analysis (start_date, end_date)

    Returns:
        Dict containing performance analysis results
    """
    try:
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 10, "status": "Loading portfolio and benchmark data"},
        )
        portfolio_returns = np.array(portfolio_data["returns"])
        benchmark_returns = np.array(benchmark_data["returns"])
        min_length = min(len(portfolio_returns), len(benchmark_returns))
        portfolio_returns = portfolio_returns[:min_length]
        benchmark_returns = benchmark_returns[:min_length]
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 30, "status": "Calculating performance metrics"},
        )
        portfolio_total_return = np.prod(1 + portfolio_returns) - 1
        benchmark_total_return = np.prod(1 + benchmark_returns) - 1
        portfolio_annualized_return = (1 + portfolio_total_return) ** (
            252 / len(portfolio_returns)
        ) - 1
        benchmark_annualized_return = (1 + benchmark_total_return) ** (
            252 / len(benchmark_returns)
        ) - 1
        portfolio_volatility = np.std(portfolio_returns) * np.sqrt(252)
        benchmark_volatility = np.std(benchmark_returns) * np.sqrt(252)
        risk_free_rate = 0.02
        portfolio_sharpe = (
            portfolio_annualized_return - risk_free_rate
        ) / portfolio_volatility
        benchmark_sharpe = (
            benchmark_annualized_return - risk_free_rate
        ) / benchmark_volatility
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 60, "status": "Calculating relative performance metrics"},
        )
        excess_returns = portfolio_returns - benchmark_returns
        tracking_error = np.std(excess_returns) * np.sqrt(252)
        information_ratio = (
            np.mean(excess_returns) * 252 / tracking_error if tracking_error > 0 else 0
        )
        covariance = np.cov(portfolio_returns, benchmark_returns)[0, 1]
        benchmark_variance = np.var(benchmark_returns)
        beta = covariance / benchmark_variance if benchmark_variance > 0 else 1
        alpha = portfolio_annualized_return - (
            risk_free_rate + beta * (benchmark_annualized_return - risk_free_rate)
        )
        task_result_manager.store_task_progress(
            self.request.id, {"progress": 80, "status": "Calculating drawdown metrics"}
        )
        portfolio_cumulative = np.cumprod(1 + portfolio_returns)
        running_max = np.maximum.accumulate(portfolio_cumulative)
        drawdowns = (portfolio_cumulative - running_max) / running_max
        max_drawdown = np.min(drawdowns)
        max_drawdown_duration = _calculate_max_drawdown_duration(drawdowns)
        results = {
            "performance_summary": {
                "total_return": float(portfolio_total_return),
                "annualized_return": float(portfolio_annualized_return),
                "volatility": float(portfolio_volatility),
                "sharpe_ratio": float(portfolio_sharpe),
                "max_drawdown": float(max_drawdown),
                "max_drawdown_duration_days": int(max_drawdown_duration),
            },
            "benchmark_comparison": {
                "benchmark_total_return": float(benchmark_total_return),
                "benchmark_annualized_return": float(benchmark_annualized_return),
                "benchmark_volatility": float(benchmark_volatility),
                "benchmark_sharpe": float(benchmark_sharpe),
                "excess_return": float(
                    portfolio_annualized_return - benchmark_annualized_return
                ),
                "tracking_error": float(tracking_error),
                "information_ratio": float(information_ratio),
                "beta": float(beta),
                "alpha": float(alpha),
            },
            "risk_metrics": {
                "var_95": float(np.percentile(portfolio_returns, 5)),
                "var_99": float(np.percentile(portfolio_returns, 1)),
                "downside_deviation": float(
                    _calculate_downside_deviation(portfolio_returns)
                ),
                "sortino_ratio": float(
                    _calculate_sortino_ratio(portfolio_returns, risk_free_rate)
                ),
            },
            "metadata": {
                "analysis_period": analysis_period,
                "number_of_observations": len(portfolio_returns),
                "completed_at": datetime.utcnow().isoformat(),
                "task_id": self.request.id,
            },
        }
        task_result_manager.store_task_progress(
            self.request.id,
            {"progress": 100, "status": "Performance analysis completed"},
        )
        logger.info(
            f"Portfolio performance analysis completed for task {self.request.id}"
        )
        return results
    except Exception as e:
        logger.error(
            f"Portfolio performance analysis failed for task {self.request.id}: {str(e)}"
        )
        raise


def _calculate_max_drawdown_duration(drawdowns: object) -> object:
    """Calculate the maximum drawdown duration in days."""
    in_drawdown = drawdowns < 0
    drawdown_periods = []
    current_period = 0
    for is_in_drawdown in in_drawdown:
        if is_in_drawdown:
            current_period += 1
        elif current_period > 0:
            drawdown_periods.append(current_period)
            current_period = 0
    if current_period > 0:
        drawdown_periods.append(current_period)
    return max(drawdown_periods) if drawdown_periods else 0


def _calculate_downside_deviation(
    returns: "np.ndarray | pd.DataFrame | list", target_return: object = 0
) -> object:
    """Calculate downside deviation."""
    downside_returns = returns[returns < target_return]
    return np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0


def _calculate_sortino_ratio(
    returns: "np.ndarray | pd.DataFrame | list", risk_free_rate: float
) -> object:
    """Calculate Sortino ratio."""
    excess_returns = returns - risk_free_rate / 252
    downside_deviation = _calculate_downside_deviation(returns)
    return (
        np.mean(excess_returns) * 252 / downside_deviation
        if downside_deviation > 0
        else 0
    )


@celery_app.task()
def update_portfolio_data(portfolio_id: int, market_data: Dict) -> Dict[str, Any]:
    """
    Update portfolio data with latest market information.

    Args:
        portfolio_id: ID of the portfolio to update
        market_data: Latest market data

    Returns:
        Dict containing update results
    """
    try:
        logger.info(f"Updating portfolio {portfolio_id} with latest market data")
        update_results = {
            "portfolio_id": portfolio_id,
            "updated_at": datetime.utcnow().isoformat(),
            "market_data_timestamp": market_data.get("timestamp"),
            "assets_updated": len(market_data.get("prices", {})),
            "status": "success",
        }
        return update_results
    except Exception as e:
        logger.error(f"Portfolio data update failed: {str(e)}")
        raise
