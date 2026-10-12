import math
import re
from typing import Any, Dict, List, Optional

from src.core.exceptions import ValidationError

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,15}$")
OPTIMIZATION_METHODS = ("utility", "max_sharpe", "min_variance")
MAX_SYMBOLS = 50
MAX_FORECAST_PERIODS = 365
FORECAST_MODELS = ("auto", "naive", "drift", "ets", "prophet")


def require_body(data: Any) -> Dict[str, Any]:
    if not isinstance(data, dict) or not data:
        raise ValidationError("A JSON object request body is required")
    return data


def validate_number(
    value: Any,
    field: str,
    minimum: float,
    maximum: float,
    default: Optional[float] = None,
) -> float:
    if value is None:
        if default is None:
            raise ValidationError(f"{field} is required", field)
        return default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError(f"{field} must be a number", field)
    number = float(value)
    if not math.isfinite(number) or number < minimum or number > maximum:
        raise ValidationError(f"{field} must be between {minimum} and {maximum}", field)
    return number


def validate_integer(
    value: Any, field: str, minimum: int, maximum: int, default: int
) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError(f"{field} must be an integer", field)
    if value < minimum or value > maximum:
        raise ValidationError(f"{field} must be between {minimum} and {maximum}", field)
    return value


def validate_symbol(value: Any, field: str = "symbol") -> str:
    if not isinstance(value, str) or not SYMBOL_PATTERN.match(value.strip()):
        raise ValidationError(f"{field} is not a valid symbol", field)
    return value.strip().upper()


def validate_symbols(value: Any, minimum: int = 2) -> List[str]:
    if not isinstance(value, list):
        raise ValidationError("symbols must be a list", "symbols")
    cleaned: List[str] = []
    for item in value:
        symbol = validate_symbol(item, "symbols")
        if symbol not in cleaned:
            cleaned.append(symbol)
    if len(cleaned) < minimum:
        raise ValidationError(
            f"symbols must contain at least {minimum} distinct symbols", "symbols"
        )
    if len(cleaned) > MAX_SYMBOLS:
        raise ValidationError(
            f"symbols must contain at most {MAX_SYMBOLS} items", "symbols"
        )
    return cleaned


def validate_market_source(
    data: Dict[str, Any], symbols_required: bool = True
) -> Dict[str, Any]:
    market_data = data.get("market_data")
    symbols = data.get("symbols")
    if market_data is None and symbols is None:
        raise ValidationError("Provide either market_data or symbols")
    if market_data is not None and not isinstance(market_data, (dict, list)):
        raise ValidationError("market_data must be an object or a list", "market_data")
    if market_data is not None and not market_data:
        raise ValidationError("market_data must not be empty", "market_data")
    return {
        "market_data": market_data,
        "symbols": validate_symbols(symbols) if symbols is not None else None,
    }


def validate_bounds(data: Dict[str, Any]) -> Dict[str, float]:
    min_weight = validate_number(data.get("min_weight"), "min_weight", 0.0, 1.0, 0.0)
    max_weight = validate_number(data.get("max_weight"), "max_weight", 0.0, 1.0, 1.0)
    if min_weight > max_weight:
        raise ValidationError("min_weight must not exceed max_weight", "min_weight")
    return {"min_weight": min_weight, "max_weight": max_weight}


def validate_optimize_request(data: Any) -> Dict[str, Any]:
    data = require_body(data)
    result = validate_market_source(data)
    result["risk_tolerance"] = validate_number(
        data.get("risk_tolerance"), "risk_tolerance", 1.0, 10.0, 5.0
    )
    result.update(validate_bounds(data))
    method = data.get("method", "utility")
    if method not in OPTIMIZATION_METHODS:
        raise ValidationError(
            f"method must be one of {', '.join(OPTIMIZATION_METHODS)}", "method"
        )
    result["method"] = method
    return result


def validate_frontier_request(data: Any) -> Dict[str, Any]:
    data = require_body(data)
    result = validate_market_source(data)
    result["risk_tolerance"] = validate_number(
        data.get("risk_tolerance"), "risk_tolerance", 1.0, 10.0, 5.0
    )
    result.update(validate_bounds(data))
    result["points"] = validate_integer(data.get("points"), "points", 2, 100, 20)
    return result


def validate_simulation_request(data: Any) -> Dict[str, Any]:
    data = require_body(data)
    weights = data.get("weights")
    if not isinstance(weights, dict) or not weights:
        raise ValidationError("weights must be a non-empty object", "weights")
    cleaned: Dict[str, float] = {}
    for key, value in weights.items():
        symbol = validate_symbol(key, "weights")
        cleaned[symbol] = validate_number(value, f"weights.{key}", 0.0, 1.0)
    if sum(cleaned.values()) <= 0:
        raise ValidationError("weights must sum to a positive value", "weights")
    market_data = data.get("market_data")
    if market_data is not None and not isinstance(market_data, (dict, list)):
        raise ValidationError("market_data must be an object or a list", "market_data")
    seed = data.get("seed")
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValidationError("seed must be an integer", "seed")
    return {
        "weights": cleaned,
        "market_data": market_data,
        "symbols": (
            validate_symbols(data["symbols"], minimum=1)
            if data.get("symbols")
            else None
        ),
        "num_simulations": validate_integer(
            data.get("num_simulations"), "num_simulations", 1, 20000, 1000
        ),
        "time_horizon": validate_integer(
            data.get("time_horizon"), "time_horizon", 1, 2520, 252
        ),
        "initial_value": validate_number(
            data.get("initial_value"), "initial_value", 1.0, 1e12, 10000.0
        ),
        "seed": seed,
    }


def validate_forecast_args(
    ticker: str, periods: Any, model: Any = None
) -> Dict[str, Any]:
    if periods is None:
        periods = 30
    elif isinstance(periods, str):
        if not periods.strip().isdigit():
            raise ValidationError("periods must be an integer", "periods")
        periods = int(periods)
    if model is None:
        model = "auto"
    if model not in FORECAST_MODELS:
        raise ValidationError(
            f"model must be one of {', '.join(FORECAST_MODELS)}", "model"
        )
    return {
        "ticker": validate_symbol(ticker, "ticker"),
        "periods": validate_integer(periods, "periods", 1, MAX_FORECAST_PERIODS, 30),
        "model": model,
    }


def validate_sentiment_request(data: Any) -> Dict[str, Any]:
    data = require_body(data)
    texts = data.get("texts")
    if not isinstance(texts, list) or not texts:
        raise ValidationError("texts must be a non-empty list", "texts")
    return {"texts": texts}


def validate_training_request(data: Any) -> Dict[str, Any]:
    data = data if isinstance(data, dict) else {}
    symbols = data.get("symbols")
    return {
        "symbols": validate_symbols(symbols) if symbols else None,
        "risk_tolerance": validate_number(
            data.get("risk_tolerance"), "risk_tolerance", 1.0, 10.0, 5.0
        ),
    }
