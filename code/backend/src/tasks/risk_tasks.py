import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from risk import (
    ParallelRiskEngine,
    performance_summary,
    simulate_portfolio_paths,
    stress_portfolio,
)
from risk.common import historical_var_es, portfolio_returns
from risk.engine import model_metrics
from settings import RISK_FREE_RATE
from src.tasks.celery_app import (
    TaskValidationError,
    celery_app,
    task_result_manager,
    task_with_progress,
)
from src.tasks.quant_adapter import (
    load_portfolio_returns,
    portfolio_inputs,
    returns_frame,
    translate_errors,
)

logger = logging.getLogger(__name__)

MAX_SIMULATIONS = 100_000
MAX_HORIZON = 1000
MAX_PORTFOLIOS = 50_000
AVAILABLE_METRICS = (
    "sharpe_ratio",
    "sortino_ratio",
    "calmar_ratio",
    "max_drawdown",
    "beta",
    "alpha",
    "treynor_ratio",
    "information_ratio",
)
BENCHMARK_METRICS = ("beta", "alpha", "treynor_ratio", "information_ratio")


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


def check_range(value: Any, name: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, int)
        or not 1 <= value <= maximum
    ):
        raise TaskValidationError(f"{name} must be between 1 and {maximum:,}")
    return value


@task_with_progress()
def monte_carlo_simulation(
    self, portfolio_data: Dict, num_simulations: int = 10000, time_horizon: int = 252
) -> Dict[str, Any]:
    try:
        check_range(num_simulations, "Number of simulations", MAX_SIMULATIONS)
        check_range(time_horizon, "Time horizon", MAX_HORIZON)
        progress(self, 10, "Preparing portfolio inputs")
        with translate_errors():
            frame, weights = portfolio_inputs(portfolio_data)
            progress(self, 30, "Running Monte Carlo simulations")
            results = simulate_portfolio_paths(
                frame,
                weights,
                num_simulations,
                time_horizon,
                copula_type=portfolio_data.get("copula_type", "t"),
                seed=portfolio_data.get("seed", 42),
            )
        results["metadata"] = {"completed_at": now(), "task_id": self.request.id}
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Monte Carlo simulation", error)
        raise


@task_with_progress()
def calculate_var_cvar(
    self, portfolio_data: Dict, confidence_levels: Optional[List[float]] = None
) -> Dict[str, Any]:
    try:
        levels = [0.95, 0.99] if confidence_levels is None else confidence_levels
        if not isinstance(levels, list) or not levels:
            raise TaskValidationError("Confidence levels must be a non-empty list")
        for level in levels:
            if (
                isinstance(level, bool)
                or not isinstance(level, (int, float))
                or not 0 < level < 1
            ):
                raise TaskValidationError("Confidence levels must be between 0 and 1")
        progress(self, 20, "Calculating portfolio returns")
        with translate_errors():
            frame, weights = portfolio_inputs(portfolio_data)
            series = portfolio_returns(frame, weights).to_numpy()
            progress(self, 60, "Calculating VaR and CVaR")
            results: Dict[str, Any] = {
                "var": {},
                "cvar": {},
                "statistics": {
                    "mean_return": float(np.mean(series)),
                    "volatility": float(np.std(series)),
                    "skewness": float(pd.Series(series).skew()),
                    "kurtosis": float(pd.Series(series).kurtosis()),
                },
                "model_estimates": {},
            }
            for level in levels:
                var, es = historical_var_es(series, level)
                results["var"][f"{level:.0%}"] = var
                results["cvar"][f"{level:.0%}"] = es
            for model in ("parametric", "evt"):
                try:
                    estimates = model_metrics(series, model, levels)
                except ValueError as error:
                    results["model_estimates"][model] = {"error": str(error)}
                    continue
                results["model_estimates"][model] = {
                    key: (value if np.isfinite(value) else None)
                    for key, value in estimates.items()
                }
        results["metadata"] = {"completed_at": now(), "task_id": self.request.id}
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "VaR and CVaR calculation", error)
        raise


@task_with_progress()
def efficient_frontier_calculation(
    self, assets_data: Dict, num_portfolios: int = 10000
) -> Dict[str, Any]:
    try:
        check_range(num_portfolios, "Number of portfolios", MAX_PORTFOLIOS)
        progress(self, 10, "Preparing asset returns")
        with translate_errors():
            frame = returns_frame(assets_data, "returns")
            progress(self, 30, "Sampling portfolios")
            engine = ParallelRiskEngine(n_jobs=1, seed=assets_data.get("seed", 42))
            outcome = engine.parallel_portfolio_optimization(
                frame, "markowitz", num_portfolios
            )
        table = outcome["all_portfolios"]
        assets = list(frame.columns)

        def optimal(entry: Dict[str, Any]) -> Dict[str, Any]:
            return {
                "weights": [entry["weights"][a] for a in assets],
                "weights_by_asset": entry["weights"],
                "return": entry["return"],
                "volatility": entry["volatility"],
                "sharpe_ratio": entry["sharpe_ratio"],
            }

        frontier = outcome["efficient_frontier"]
        results = {
            "portfolios": {
                "returns": table["return"].tolist(),
                "volatilities": table["volatility"].tolist(),
                "sharpe_ratios": table["sharpe_ratio"].tolist(),
            },
            "optimal_portfolios": {
                "max_sharpe": optimal(outcome["max_sharpe_portfolio"]),
                "min_volatility": optimal(outcome["min_volatility_portfolio"]),
            },
            "efficient_frontier": {
                "returns": frontier["return"].tolist(),
                "volatilities": frontier["volatility"].tolist(),
            },
            "statistics": {
                "num_portfolios": int(len(table)),
                "mean_return": float(table["return"].mean()),
                "mean_volatility": float(table["volatility"].mean()),
                "mean_sharpe": float(table["sharpe_ratio"].mean()),
            },
            "asset_names": assets,
            "metadata": {"completed_at": now(), "task_id": self.request.id},
        }
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Efficient frontier calculation", error)
        raise


@task_with_progress()
def stress_test_portfolio(
    self, portfolio_data: Dict, stress_scenarios: List[Dict]
) -> Dict[str, Any]:
    try:
        progress(self, 10, "Preparing portfolio inputs")
        with translate_errors():
            frame, weights = portfolio_inputs(portfolio_data)
            progress(self, 40, f"Applying {len(stress_scenarios)} stress scenarios")
            results = stress_portfolio(
                frame, weights, stress_scenarios, seed=portfolio_data.get("seed", 42)
            )
        results["metadata"] = {"completed_at": now(), "task_id": self.request.id}
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Stress test", error)
        raise


@celery_app.task()
def calculate_portfolio_metrics(
    portfolio_id: int,
    metrics: List[str],
    returns: Optional[List[float]] = None,
    benchmark_returns: Optional[List[float]] = None,
) -> Dict[str, Any]:
    try:
        requested = [m for m in metrics if m in AVAILABLE_METRICS]
        with translate_errors():
            series = (
                np.asarray(returns, dtype=float)
                if returns is not None
                else load_portfolio_returns(portfolio_id).to_numpy()
            )
            summary = performance_summary(series, benchmark_returns, RISK_FREE_RATE)
        flat = dict(summary["performance_summary"])
        flat.update(summary.get("benchmark_comparison", {}))
        results: Dict[str, float] = {}
        unavailable: Dict[str, str] = {}
        for metric in requested:
            if metric in flat:
                results[metric] = flat[metric]
            else:
                unavailable[metric] = "benchmark_returns are required"
        return {
            "portfolio_id": portfolio_id,
            "metrics": results,
            "unavailable": unavailable,
            "observations": summary["observations"],
            "calculated_at": now(),
        }
    except Exception as error:
        logger.error("Portfolio metrics calculation failed: %s", error)
        raise
