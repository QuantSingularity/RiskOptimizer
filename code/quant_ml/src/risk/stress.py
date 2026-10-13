from typing import Any, Dict, Optional

import numpy as np
from risk.common import as_frame, historical_var_es, weight_vector

SCENARIO_TYPES = ("market_crash", "volatility_spike", "correlation_breakdown")


def describe(series: np.ndarray) -> Dict[str, float]:
    var, es = historical_var_es(series, 0.95)
    return {
        "mean": float(series.mean()),
        "volatility": float(series.std()),
        "var_95": var,
        "es_95": es,
    }


def apply_scenario(
    values: np.ndarray,
    vector: np.ndarray,
    scenario: Dict[str, Any],
    seed: Optional[int],
) -> np.ndarray:
    kind = scenario.get("type")
    if kind == "market_crash":
        shock = float(scenario.get("shock", -0.3))
        if not -1.0 <= shock <= 1.0:
            raise ValueError("shock must be between -1 and 1")
        return values @ vector + shock * float(vector.sum())
    if kind == "volatility_spike":
        multiplier = float(scenario.get("multiplier", 2.0))
        if not 0.0 < multiplier <= 20.0:
            raise ValueError("multiplier must be between 0 and 20")
        centre = values.mean(axis=0)
        return (centre + multiplier * (values - centre)) @ vector
    if kind == "correlation_breakdown":
        intensity = float(scenario.get("intensity", scenario.get("noise_level", 0.5)))
        if not 0.0 <= intensity <= 1.0:
            raise ValueError("intensity must be between 0 and 1")
        rng = np.random.default_rng(seed)
        shuffled = np.column_stack(
            [rng.permutation(values[:, i]) for i in range(values.shape[1])]
        )
        return ((1.0 - intensity) * values + intensity * shuffled) @ vector
    raise ValueError(
        f"Unsupported scenario type: {kind!r}. Use one of {', '.join(SCENARIO_TYPES)}"
    )


def stress_portfolio(
    returns: Any, weights: Any, scenarios: Any, seed: Optional[int] = None
) -> Dict[str, Any]:
    if not isinstance(scenarios, list) or not scenarios:
        raise ValueError("scenarios must be a non-empty list")
    frame = as_frame(returns, min_rows=30)
    vector = weight_vector(weights, list(frame.columns))
    values = frame.to_numpy()
    baseline = describe(values @ vector)
    results = []
    for index, scenario in enumerate(scenarios):
        if not isinstance(scenario, dict):
            raise ValueError("Each scenario must be an object")
        stressed = describe(
            apply_scenario(
                values, vector, scenario, None if seed is None else seed + index
            )
        )
        return_impact = stressed["mean"] - baseline["mean"]
        volatility_impact = stressed["volatility"] - baseline["volatility"]
        results.append(
            {
                "scenario": scenario,
                "stressed_return": stressed["mean"],
                "stressed_volatility": stressed["volatility"],
                "stressed_var_95": stressed["var_95"],
                "stressed_es_95": stressed["es_95"],
                "return_impact": return_impact,
                "volatility_impact": volatility_impact,
                "relative_return_impact": (
                    return_impact / baseline["mean"] if baseline["mean"] else 0.0
                ),
                "relative_volatility_impact": (
                    volatility_impact / baseline["volatility"]
                    if baseline["volatility"]
                    else 0.0
                ),
            }
        )
    return {
        "baseline": {
            "return": baseline["mean"],
            "volatility": baseline["volatility"],
            "var_95": baseline["var_95"],
            "es_95": baseline["es_95"],
        },
        "stress_results": results,
    }
