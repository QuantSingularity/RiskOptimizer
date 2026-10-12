import math
from typing import Any, Dict, Mapping

DEFAULT_MIN_TRANSACTION = 100.0
DEFAULT_COST_RATE = 0.001
WEIGHT_TOLERANCE = 1e-3


def clean_mapping(values: Mapping[str, Any], name: str) -> Dict[str, float]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError(f"{name} must be a non-empty mapping")
    cleaned: Dict[str, float] = {}
    for asset, value in values.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError(f"{name}[{asset!r}] must be a non-negative finite number")
        cleaned[str(asset)] = float(value)
    return cleaned


def plan_rebalance(
    holdings: Mapping[str, Any],
    target_weights: Mapping[str, Any],
    min_transaction_size: float = DEFAULT_MIN_TRANSACTION,
    transaction_cost_rate: float = DEFAULT_COST_RATE,
) -> Dict[str, Any]:
    current = clean_mapping(holdings, "holdings")
    targets = clean_mapping(target_weights, "target_weights")
    if min_transaction_size < 0 or not 0 <= transaction_cost_rate < 1:
        raise ValueError(
            "min_transaction_size must be non-negative and transaction_cost_rate within [0, 1)"
        )
    total_value = sum(current.values())
    if total_value <= 0:
        raise ValueError("Total portfolio value must be positive")
    if abs(sum(targets.values()) - 1.0) > WEIGHT_TOLERANCE:
        raise ValueError("target_weights must sum to 1")
    assets = sorted(set(current) | set(targets))
    current_weights = {a: current.get(a, 0.0) / total_value for a in assets}
    target_values = {a: targets.get(a, 0.0) * total_value for a in assets}
    transactions: Dict[str, Dict[str, Any]] = {}
    executed_values = dict(current)
    turnover = 0.0
    for asset in assets:
        difference = target_values[asset] - current.get(asset, 0.0)
        if abs(difference) > min_transaction_size:
            transactions[asset] = {
                "current_value": current.get(asset, 0.0),
                "target_value": target_values[asset],
                "transaction_amount": difference,
                "transaction_type": "buy" if difference > 0 else "sell",
            }
            executed_values[asset] = target_values[asset]
            turnover += abs(difference)
    target_vector = {a: targets.get(a, 0.0) for a in assets}
    after_weights = {a: executed_values.get(a, 0.0) / total_value for a in assets}

    def distance(weights: Mapping[str, float]) -> float:
        return math.sqrt(sum((weights[a] - target_vector[a]) ** 2 for a in assets))

    before, after = distance(current_weights), distance(after_weights)
    costs = turnover * transaction_cost_rate
    return {
        "current_portfolio": {"total_value": total_value, "weights": current_weights},
        "target_portfolio": {"weights": target_vector, "values": target_values},
        "rebalancing_analysis": {
            "total_turnover": turnover,
            "turnover_rate": turnover / total_value,
            "number_of_transactions": len(transactions),
            "estimated_costs": costs,
            "cost_percentage": costs / total_value,
            "tracking_error_before": before,
            "tracking_error_after": after,
            "tracking_error_reduction": before - after,
            "cash_residual": total_value - sum(executed_values.values()),
        },
        "transactions": transactions,
    }
