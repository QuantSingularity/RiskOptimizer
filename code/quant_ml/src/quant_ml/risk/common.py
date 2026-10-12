import math
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

import numpy as np
import pandas as pd

ReturnsLike = Union[pd.DataFrame, pd.Series, np.ndarray, Sequence[float]]
WeightsLike = Union[Mapping[str, float], np.ndarray, Sequence[float]]


def validate_confidence(confidence: Any) -> float:
    if isinstance(confidence, bool) or not isinstance(
        confidence, (int, float, np.number)
    ):
        raise ValueError("confidence must be a number between 0 and 1")
    value = float(confidence)
    if not math.isfinite(value) or not 0.0 < value < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1")
    return value


def level_key(confidence: float) -> str:
    percent = round(float(confidence) * 100.0, 6)
    if float(percent).is_integer():
        return str(int(percent))
    return f"{percent:g}".replace(".", "_")


def as_frame(returns: ReturnsLike, min_rows: int = 2) -> pd.DataFrame:
    if isinstance(returns, pd.DataFrame):
        frame = returns.copy()
    elif isinstance(returns, pd.Series):
        frame = returns.to_frame(
            name=returns.name if returns.name is not None else "asset_0"
        )
    elif isinstance(returns, Mapping):
        try:
            frame = pd.DataFrame(returns)
        except ValueError as error:
            raise ValueError(f"returns columns are inconsistent: {error}") from error
    else:
        array = np.asarray(returns, dtype=float)
        if array.ndim == 1:
            array = array.reshape(-1, 1)
        if array.ndim != 2:
            raise ValueError("returns must be one or two dimensional")
        frame = pd.DataFrame(
            array, columns=[f"asset_{i}" for i in range(array.shape[1])]
        )
    frame = frame.apply(pd.to_numeric, errors="coerce")
    frame = frame.replace([np.inf, -np.inf], np.nan).dropna()
    if frame.shape[1] == 0:
        raise ValueError("returns contain no assets")
    if len(frame) < min_rows:
        raise ValueError(f"At least {min_rows} valid return observations are required")
    frame.columns = [str(column) for column in frame.columns]
    return frame


def as_vector(values: ReturnsLike, min_size: int = 2) -> np.ndarray:
    if isinstance(values, (pd.DataFrame, pd.Series)):
        array = values.to_numpy(dtype=float).reshape(-1)
    else:
        array = np.asarray(values, dtype=float).reshape(-1)
    array = array[np.isfinite(array)]
    if len(array) < min_size:
        raise ValueError(f"At least {min_size} finite observations are required")
    return array


def weight_vector(
    weights: Optional[WeightsLike],
    assets: Sequence[str],
    normalize: bool = False,
) -> np.ndarray:
    count = len(assets)
    if weights is None:
        return np.full(count, 1.0 / count)
    if isinstance(weights, Mapping):
        unknown = [name for name in weights if str(name) not in set(map(str, assets))]
        if unknown:
            raise ValueError(
                f"Weights reference unknown assets: {sorted(map(str, unknown))}"
            )
        vector = np.array([float(weights.get(asset, 0.0)) for asset in assets])
    else:
        vector = np.asarray(weights, dtype=float).reshape(-1)
        if len(vector) != count:
            raise ValueError(f"Expected {count} weights, got {len(vector)}")
    if not np.isfinite(vector).all():
        raise ValueError("Weights must be finite")
    total = float(vector.sum())
    if abs(total) < 1e-12:
        raise ValueError("Weights must not sum to zero")
    if normalize:
        vector = vector / total
    return vector


def portfolio_returns(
    returns: pd.DataFrame, weights: Optional[WeightsLike]
) -> pd.Series:
    vector = weight_vector(weights, list(returns.columns))
    return pd.Series(
        returns.to_numpy(dtype=float) @ vector, index=returns.index, name="portfolio"
    )


def historical_var_es(values: np.ndarray, confidence: float) -> Tuple[float, float]:
    confidence = validate_confidence(confidence)
    quantile = float(np.quantile(values, 1.0 - confidence))
    tail = values[values <= quantile]
    var = max(-quantile, 0.0)
    es = max(-float(tail.mean()), var) if len(tail) else var
    return var, es


def tail_metrics(
    values: np.ndarray, confidence_levels: Sequence[float]
) -> Dict[str, float]:
    metrics: Dict[str, float] = {}
    for confidence in confidence_levels:
        var, es = historical_var_es(values, confidence)
        key = level_key(confidence)
        metrics[f"var_{key}"] = var
        metrics[f"es_{key}"] = es
    return metrics


def spawn_seeds(seed: Optional[int], count: int) -> List[int]:
    sequence = np.random.SeedSequence(seed)
    return [int(child.generate_state(1)[0]) for child in sequence.spawn(count)]
