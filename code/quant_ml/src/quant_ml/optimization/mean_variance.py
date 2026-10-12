import logging
from typing import Any, Dict, Optional, Sequence

import cvxpy
import pandas as pd
from pypfopt import expected_returns, risk_models
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt.efficient_frontier import EfficientFrontier
from quant_ml.data.loaders import available_symbols, load_close_prices
from quant_ml.settings import RISK_FREE_RATE

logger = logging.getLogger(__name__)

MIP_SOLVER_PREFERENCE = ("SCIPY", "ECOS_BB", "GLPK_MI", "CBC", "SCIP", "HIGHS")


def select_mip_solver() -> Optional[str]:
    installed = set(cvxpy.installed_solvers())
    for name in MIP_SOLVER_PREFERENCE:
        if name in installed:
            return name
    return None


def load_prices(
    tickers: Optional[Sequence[str]] = None, data_dir: Optional[str] = None
) -> pd.DataFrame:
    selected = list(tickers) if tickers else available_symbols(data_dir)
    return load_close_prices(selected, data_dir)


def performance_dict(values: Any) -> Dict[str, float]:
    expected_return, volatility, sharpe = values
    return {
        "expected_return": float(expected_return),
        "volatility": float(volatility),
        "sharpe_ratio": float(sharpe),
    }


def mean_variance_optimization(
    prices: pd.DataFrame,
    risk_free_rate: float = RISK_FREE_RATE,
    max_weight: float = 1.0,
) -> Dict[str, Any]:
    if prices.shape[1] < 2:
        raise ValueError("At least two assets are required")
    if not 1.0 / prices.shape[1] <= max_weight <= 1.0:
        raise ValueError(
            f"max_weight must be between {1.0 / prices.shape[1]:.4f} and 1"
        )
    mu = expected_returns.mean_historical_return(prices)
    covariance = risk_models.sample_cov(prices)
    bounds = (0, max_weight)
    max_sharpe = EfficientFrontier(mu, covariance, weight_bounds=bounds)
    try:
        max_sharpe.max_sharpe(risk_free_rate=risk_free_rate)
    except ValueError as error:
        raise ValueError(
            "No asset exceeds the risk free rate, so a maximum Sharpe portfolio does not exist"
        ) from error
    min_vol = EfficientFrontier(mu, covariance, weight_bounds=bounds)
    min_vol.min_volatility()
    return {
        "max_sharpe_weights": dict(max_sharpe.clean_weights()),
        "max_sharpe_performance": performance_dict(
            max_sharpe.portfolio_performance(risk_free_rate=risk_free_rate)
        ),
        "min_vol_weights": dict(min_vol.clean_weights()),
        "min_vol_performance": performance_dict(
            min_vol.portfolio_performance(risk_free_rate=risk_free_rate)
        ),
    }


def discrete_allocation_suggestion(
    prices: pd.DataFrame,
    weights: Dict[str, float],
    total_portfolio_value: float = 100_000.0,
) -> Dict[str, Any]:
    if total_portfolio_value <= 0:
        raise ValueError("total_portfolio_value must be positive")
    positive = {k: v for k, v in weights.items() if v > 0}
    if not positive:
        raise ValueError("weights must contain at least one positive entry")
    latest = get_latest_prices(prices[list(positive)])
    allocator = DiscreteAllocation(
        positive, latest, total_portfolio_value=total_portfolio_value
    )
    solver = select_mip_solver()
    method = "greedy"
    allocation, leftover = {}, total_portfolio_value
    if solver is not None:
        try:
            allocation, leftover = allocator.lp_portfolio(solver=solver)
            method = f"integer_program:{solver}"
        except Exception as error:
            logger.warning(
                "Integer allocation with %s failed (%s); using greedy allocation",
                solver,
                error,
            )
    if method == "greedy":
        allocation, leftover = allocator.greedy_portfolio()
    unaffordable = sorted(
        asset
        for asset in positive
        if asset not in allocation
        and latest[asset] > positive[asset] * total_portfolio_value
    )
    return {
        "allocation": {k: int(v) for k, v in allocation.items()},
        "leftover": float(leftover),
        "method": method,
        "unallocated_assets": unaffordable,
    }
