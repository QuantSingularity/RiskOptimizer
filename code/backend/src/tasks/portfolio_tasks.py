import logging
from datetime import datetime, timezone
from typing import Any, Dict

import numpy as np
from quant_ml.optimization import METHODS, optimize_weights, plan_rebalance
from quant_ml.risk import performance_summary
from quant_ml.settings import RISK_FREE_RATE
from src.tasks.celery_app import (
    TaskValidationError,
    celery_app,
    task_result_manager,
    task_with_progress,
)
from src.tasks.quant_adapter import returns_frame, translate_errors

logger = logging.getLogger(__name__)


def now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def progress(task: Any, percent: int, status: str) -> None:
    task_result_manager.store_task_progress(
        task.request.id, {"progress": percent, "status": status}
    )


def fail(task: Any, label: str, error: Exception) -> None:
    logger.error("%s failed for task %s: %s", label, task.request.id, error)
    task_result_manager.store_task_progress(
        task.request.id, {"progress": 0, "status": f"Failed: {error}"}
    )


@task_with_progress()
def optimize_portfolio(
    self, assets_data: Dict, optimization_params: Dict
) -> Dict[str, Any]:
    try:
        method = optimization_params.get("method", "mean_variance")
        if method not in METHODS:
            raise TaskValidationError(f"Unsupported optimization method: {method}")
        progress(self, 10, "Preparing asset returns")
        with translate_errors():
            frame = returns_frame(assets_data, "returns")
            progress(self, 40, f"Running {method} optimization")
            results = optimize_weights(frame, method, optimization_params)
        results["metadata"] = {
            "completed_at": now(),
            "task_id": self.request.id,
            "observations": int(len(frame)),
        }
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Portfolio optimization", error)
        raise


@task_with_progress()
def rebalance_portfolio(
    self, current_portfolio: Dict, target_weights: Dict, rebalancing_params: Dict
) -> Dict[str, Any]:
    try:
        progress(self, 10, "Reading current holdings")
        if "holdings" not in current_portfolio:
            raise TaskValidationError("Missing required field: holdings")
        with translate_errors():
            plan = plan_rebalance(
                current_portfolio["holdings"],
                target_weights,
                rebalancing_params.get("min_transaction_size", 100),
                rebalancing_params.get("transaction_cost_rate", 0.001),
            )
        plan["metadata"] = {"completed_at": now(), "task_id": self.request.id}
        progress(self, 100, "Completed successfully")
        return plan
    except Exception as error:
        fail(self, "Portfolio rebalancing analysis", error)
        raise


@task_with_progress()
def analyze_portfolio_performance(
    self, portfolio_data: Dict, benchmark_data: Dict, analysis_period: Dict
) -> Dict[str, Any]:
    try:
        progress(self, 10, "Validating return series")
        for container, name in (
            (portfolio_data, "portfolio_data"),
            (benchmark_data, "benchmark_data"),
        ):
            if "returns" not in container:
                raise TaskValidationError(f"{name} must contain returns")
        with translate_errors():
            progress(self, 40, "Calculating performance metrics")
            results = performance_summary(
                np.asarray(portfolio_data["returns"], dtype=float),
                np.asarray(benchmark_data["returns"], dtype=float),
                analysis_period.get("risk_free_rate", RISK_FREE_RATE),
            )
        results["metadata"] = {
            "analysis_period": analysis_period,
            "number_of_observations": results.pop("observations"),
            "completed_at": now(),
            "task_id": self.request.id,
        }
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Portfolio performance analysis", error)
        raise


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
