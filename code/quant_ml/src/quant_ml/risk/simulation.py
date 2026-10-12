from typing import Any, Dict, Optional, Sequence

import numpy as np
from quant_ml.risk.common import (
    as_frame,
    historical_var_es,
    level_key,
    spawn_seeds,
    validate_confidence,
    weight_vector,
)
from quant_ml.risk.copula import COPULA_TYPES, CopulaMLRiskModel

MAX_DRAWS = 5_000_000
MAX_PATHS = 200_000
MAX_HORIZON = 2520
CHUNK_ROWS = 200_000
PERCENTILES = (1, 5, 10, 25, 50, 75, 90, 95, 99)


def validate_count(value: Any, name: str, maximum: int) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, np.integer))
        or not 1 <= value <= maximum
    ):
        raise ValueError(f"{name} must be an integer between 1 and {maximum}")
    return int(value)


def simulate_daily_returns(
    model: CopulaMLRiskModel, weights: np.ndarray, total: int, seed: Optional[int]
) -> np.ndarray:
    chunks = []
    remaining = total
    sizes = []
    while remaining > 0:
        size = min(CHUNK_ROWS, remaining)
        sizes.append(size)
        remaining -= size
    for size, chunk_seed in zip(sizes, spawn_seeds(seed, len(sizes)), strict=True):
        chunks.append(
            model.generate_scenarios(size, seed=chunk_seed).to_numpy() @ weights
        )
    return np.concatenate(chunks)


def simulate_portfolio_paths(
    returns: Any,
    weights: Any = None,
    n_paths: int = 10_000,
    horizon: int = 252,
    copula_type: str = "t",
    seed: Optional[int] = None,
    confidence_levels: Sequence[float] = (0.95, 0.99),
    keep: int = 1000,
) -> Dict[str, Any]:
    n_paths = validate_count(n_paths, "n_paths", MAX_PATHS)
    horizon = validate_count(horizon, "horizon", MAX_HORIZON)
    if n_paths * horizon > MAX_DRAWS:
        raise ValueError(f"n_paths * horizon must not exceed {MAX_DRAWS}")
    if copula_type not in COPULA_TYPES:
        raise ValueError(f"copula_type must be one of {', '.join(COPULA_TYPES)}")
    levels = [validate_confidence(c) for c in confidence_levels]
    frame = as_frame(returns, min_rows=30)
    vector = weight_vector(weights, list(frame.columns))
    historical = frame.to_numpy() @ vector
    model = CopulaMLRiskModel(copula_type, seed=seed).fit(frame)
    daily = simulate_daily_returns(model, vector, n_paths * horizon, seed).reshape(
        n_paths, horizon
    )
    paths = np.cumprod(1.0 + np.clip(daily, -0.999, None), axis=1)
    final = paths[:, -1]
    running_peak = np.maximum.accumulate(np.maximum(paths, 1.0), axis=1)
    drawdowns = (paths / running_peak - 1.0).min(axis=1)
    terminal_returns = final - 1.0
    risk = {}
    for level in levels:
        var, es = historical_var_es(terminal_returns, level)
        risk[f"var_{level_key(level)}"] = var
        risk[f"cvar_{level_key(level)}"] = es
    risk["probability_of_loss"] = float(np.mean(final < 1.0))
    return {
        "simulation_parameters": {
            "num_simulations": n_paths,
            "time_horizon": horizon,
            "copula_type": copula_type,
            "historical_daily_mean": float(historical.mean()),
            "historical_daily_volatility": float(historical.std()),
        },
        "risk_metrics": risk,
        "statistics": {
            "mean_final_value": float(final.mean()),
            "median_final_value": float(np.median(final)),
            "std_final_value": float(final.std()),
            "min_final_value": float(final.min()),
            "max_final_value": float(final.max()),
        },
        "drawdown": {
            "mean_max_drawdown": float(drawdowns.mean()),
            "median_max_drawdown": float(np.median(drawdowns)),
            "p95_worst_max_drawdown": float(np.quantile(drawdowns, 0.05)),
            "worst_max_drawdown": float(drawdowns.min()),
        },
        "percentiles": {f"p{p}": float(np.percentile(final, p)) for p in PERCENTILES},
        "simulation_data": {
            "final_values": final[:keep].tolist(),
            "max_drawdowns": drawdowns[:keep].tolist(),
        },
    }
