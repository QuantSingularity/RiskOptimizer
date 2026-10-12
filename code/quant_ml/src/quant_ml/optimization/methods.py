import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np
import pandas as pd
from quant_ml.optimization.portfolio import (
    PortfolioOptimizerBase,
    validate_weight_bounds,
)
from quant_ml.risk.common import as_frame
from quant_ml.settings import RISK_FREE_RATE, TRADING_DAYS
from scipy.optimize import minimize
from sklearn.covariance import LedoitWolf

METHODS = ("mean_variance", "minimum_variance", "risk_parity", "black_litterman")
DEFAULT_RISK_AVERSION = 3.0
DEFAULT_TAU = 0.05
RISK_PARITY_FLOOR = 0.001


def annual_moments(
    returns: pd.DataFrame, periods: int = TRADING_DAYS, shrinkage: bool = True
) -> Tuple[np.ndarray, np.ndarray]:
    values = returns.to_numpy(dtype=float)
    mu = values.mean(axis=0) * periods
    if shrinkage and len(values) > 2:
        covariance = LedoitWolf().fit(values).covariance_
    else:
        covariance = np.atleast_2d(np.cov(values, rowvar=False))
    return mu, np.atleast_2d(covariance) * periods


def solve_slsqp(
    objective: Any,
    start: np.ndarray,
    lower: float,
    upper: float,
    extra: Optional[List[dict]] = None,
) -> np.ndarray:
    constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}] + (
        extra or []
    )
    result = minimize(
        objective,
        np.clip(start, lower, upper) / np.clip(start, lower, upper).sum(),
        method="SLSQP",
        bounds=[(lower, upper)] * len(start),
        constraints=constraints,
        options={"ftol": 1e-12, "maxiter": 1000},
    )
    if not result.success:
        raise ArithmeticError(f"Optimization did not converge: {result.message}")
    weights = np.clip(result.x, lower, upper)
    return weights / weights.sum()


def mean_variance_weights(
    mu: np.ndarray,
    covariance: np.ndarray,
    lower: float,
    upper: float,
    risk_aversion: float = DEFAULT_RISK_AVERSION,
    target_return: Optional[float] = None,
) -> np.ndarray:
    n = len(mu)
    start = np.full(n, 1.0 / n)
    if target_return is None:
        return PortfolioOptimizerBase().solve(
            mu, covariance, risk_aversion, lower, upper
        )
    best = solve_slsqp(lambda w: float(-(mu @ w)), start, lower, upper)
    if target_return > float(mu @ best) + 1e-9:
        raise ValueError(
            f"target_return {target_return:.4f} exceeds the maximum achievable {float(mu @ best):.4f}"
        )
    floor = solve_slsqp(lambda w: float(w @ covariance @ w), start, lower, upper)
    if target_return <= float(mu @ floor):
        return floor
    constraint = [{"type": "ineq", "fun": lambda w: float(mu @ w - target_return)}]
    return solve_slsqp(
        lambda w: float(w @ covariance @ w), start, lower, upper, constraint
    )


def minimum_variance_weights(
    covariance: np.ndarray, lower: float, upper: float
) -> np.ndarray:
    n = len(covariance)
    return solve_slsqp(
        lambda w: float(w @ covariance @ w), np.full(n, 1.0 / n), lower, upper
    )


def risk_contributions(weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    variance = float(weights @ covariance @ weights)
    if variance <= 0:
        return np.zeros_like(weights)
    return weights * (covariance @ weights) / variance


def risk_parity_weights(
    covariance: np.ndarray, lower: float, upper: float
) -> np.ndarray:
    n = len(covariance)
    floor = max(lower, RISK_PARITY_FLOOR)
    target = 1.0 / n

    def objective(weights: np.ndarray) -> float:
        return float(np.sum((risk_contributions(weights, covariance) - target) ** 2))

    return solve_slsqp(objective, np.full(n, 1.0 / n), floor, upper)


def parse_views(
    views: Sequence[Mapping[str, Any]], assets: List[str]
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    pick = np.zeros((len(views), len(assets)))
    expected = np.zeros(len(views))
    confidence = np.zeros(len(views))
    for row, view in enumerate(views):
        mapping = view.get("assets")
        if not isinstance(mapping, Mapping) or not mapping:
            raise ValueError("Each view needs a non-empty 'assets' mapping")
        for name, coefficient in mapping.items():
            if name not in assets:
                raise ValueError(f"View references unknown asset: {name}")
            pick[row, assets.index(name)] = float(coefficient)
        expected[row] = float(view["return"])
        confidence[row] = float(view.get("confidence", 0.5))
        if not 0.0 < confidence[row] < 1.0:
            raise ValueError("View confidence must be strictly between 0 and 1")
    return pick, expected, confidence


def black_litterman_posterior(
    covariance: np.ndarray,
    market_weights: np.ndarray,
    risk_aversion: float,
    tau: float,
    views: Sequence[Mapping[str, Any]],
    assets: List[str],
) -> Tuple[np.ndarray, np.ndarray]:
    prior = risk_aversion * covariance @ market_weights
    if not views:
        return prior, prior
    pick, expected, confidence = parse_views(views, assets)
    scaled = tau * covariance
    view_variance = np.diag(pick @ scaled @ pick.T) * (1.0 - confidence) / confidence
    omega = np.diag(view_variance)
    gain = scaled @ pick.T @ np.linalg.inv(pick @ scaled @ pick.T + omega)
    return prior, prior + gain @ (expected - pick @ prior)


def constraint_report(
    weights: np.ndarray, lower: float, upper: float, params: Mapping[str, Any]
) -> Dict[str, bool]:
    report = {
        "weights_sum_to_one": bool(abs(weights.sum() - 1.0) < 1e-6),
        "no_negative_weights": bool((weights >= -1e-9).all()),
        "within_bounds": bool(
            ((weights >= lower - 1e-6) & (weights <= upper + 1e-6)).all()
        ),
    }
    if params.get("max_weight_per_asset") is not None:
        report["max_weight_constraint"] = bool(
            (weights <= float(params["max_weight_per_asset"]) + 1e-6).all()
        )
    if params.get("min_weight_per_asset") is not None:
        report["min_weight_constraint"] = bool(
            (weights >= float(params["min_weight_per_asset"]) - 1e-6).all()
        )
    return report


def optimize_weights(
    returns: Any,
    method: str = "mean_variance",
    params: Optional[Mapping[str, Any]] = None,
    risk_free_rate: float = RISK_FREE_RATE,
    periods_per_year: int = TRADING_DAYS,
) -> Dict[str, Any]:
    if method not in METHODS:
        raise ValueError(f"Unsupported optimization method: {method}")
    options = dict(params or {})
    frame = as_frame(returns, min_rows=30)
    assets = list(frame.columns)
    if len(assets) < 2:
        raise ValueError("At least two assets are required")
    lower_request = options.get("min_weight_per_asset")
    upper_request = options.get("max_weight_per_asset")
    lower, upper = validate_weight_bounds(
        len(assets),
        0.0 if lower_request is None else float(lower_request),
        1.0 if upper_request is None else float(upper_request),
    )
    mu, covariance = annual_moments(
        frame, periods_per_year, bool(options.get("shrinkage", True))
    )
    risk_aversion = float(options.get("risk_aversion", DEFAULT_RISK_AVERSION))
    if not math.isfinite(risk_aversion) or risk_aversion <= 0:
        raise ValueError("risk_aversion must be positive")
    details: Dict[str, Any] = {}
    if method == "mean_variance":
        target = options.get("target_return")
        weights = mean_variance_weights(
            mu,
            covariance,
            lower,
            upper,
            risk_aversion,
            None if target is None else float(target),
        )
    elif method == "minimum_variance":
        weights = minimum_variance_weights(covariance, lower, upper)
    elif method == "risk_parity":
        weights = risk_parity_weights(covariance, lower, upper)
    else:
        market = options.get("market_weights")
        if market is None:
            market_weights = np.full(len(assets), 1.0 / len(assets))
        else:
            if not isinstance(market, Mapping):
                raise ValueError("market_weights must map asset names to weights")
            market_weights = np.array([float(market.get(a, 0.0)) for a in assets])
            if market_weights.sum() <= 0 or (market_weights < 0).any():
                raise ValueError(
                    "market_weights must be non-negative with a positive sum"
                )
            market_weights = market_weights / market_weights.sum()
        tau = float(options.get("tau", DEFAULT_TAU))
        if not 0.0 < tau <= 1.0:
            raise ValueError("tau must be between 0 and 1")
        prior, posterior = black_litterman_posterior(
            covariance,
            market_weights,
            risk_aversion,
            tau,
            options.get("views") or [],
            assets,
        )
        weights = PortfolioOptimizerBase().solve(
            posterior, covariance, risk_aversion, lower, upper
        )
        details = {
            "implied_equilibrium_returns": dict(
                zip(assets, prior.tolist(), strict=True)
            ),
            "posterior_returns": dict(zip(assets, posterior.tolist(), strict=True)),
            "market_weights": dict(zip(assets, market_weights.tolist(), strict=True)),
        }
    expected_return = float(mu @ weights)
    volatility = float(np.sqrt(max(weights @ covariance @ weights, 0.0)))
    contributions = risk_contributions(weights, covariance)
    return {
        "optimization_method": method,
        "weights": dict(zip(assets, weights.tolist(), strict=True)),
        "portfolio_metrics": {
            "expected_return": expected_return,
            "volatility": volatility,
            "sharpe_ratio": (
                (expected_return - risk_free_rate) / volatility
                if volatility > 0
                else 0.0
            ),
        },
        "risk_contributions": dict(zip(assets, contributions.tolist(), strict=True)),
        "constraints_satisfied": constraint_report(weights, lower, upper, options),
        "details": details,
    }
