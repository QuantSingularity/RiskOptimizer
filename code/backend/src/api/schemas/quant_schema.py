import re
from typing import Any, Callable, Dict, List, Optional

from src.api.schemas.optimization_schema import (
    require_body,
    validate_integer,
    validate_number,
    validate_symbols,
)
from src.core.exceptions import ValidationError
from src.services.quant_ml_bridge import ensure_quant_ml

ensure_quant_ml()

from reporting import validate_recipients

COLUMN_PATTERN = re.compile(r"^[A-Za-z0-9._ -]{1,40}$")
COPULA_TYPES = ("gaussian", "t", "clayton", "gumbel")
ML_MODEL_TYPES = ("gbm", "rf", "nn")
RISK_MODELS = ("parametric", "historical", "evt")
RISK_MEASURES = ("volatility", "var", "es")
OPTIMIZATION_RISK_MODELS = ("markowitz", "cvar", "mad")
DEFAULT_CONFIDENCES = (0.95, 0.99)
MAX_RETURN_ROWS = 5000
MAX_RETURN_COLUMNS = 50
MAX_SCENARIO_DEFINITIONS = 20
REPORT_FORMATS = ("html", "pdf")


def choice(value: Any, field: str, allowed: tuple, default: str) -> str:
    if value is None:
        return default
    if value not in allowed:
        raise ValidationError(f"{field} must be one of {', '.join(allowed)}", field)
    return value


def choices(value: Any, field: str, allowed: tuple) -> Optional[List[str]]:
    if value is None:
        return None
    if (
        not isinstance(value, list)
        or not value
        or not all(item in allowed for item in value)
    ):
        raise ValidationError(
            f"{field} must be a non-empty list drawn from {', '.join(allowed)}", field
        )
    return list(dict.fromkeys(value))


def confidence_levels(body: Dict[str, Any]) -> List[float]:
    value = body.get("confidence_levels")
    if value is None:
        return list(DEFAULT_CONFIDENCES)
    if not isinstance(value, list) or not 1 <= len(value) <= 6:
        raise ValidationError(
            "confidence_levels must be a list of 1 to 6 numbers", "confidence_levels"
        )
    return [validate_number(item, "confidence_levels", 0.5, 0.9999) for item in value]


def seed(body: Dict[str, Any]) -> Optional[int]:
    value = body.get("seed")
    if value is None:
        return None
    return validate_integer(value, "seed", 0, 2**31 - 1, 0)


def data_source(body: Dict[str, Any], minimum_symbols: int = 1) -> Dict[str, Any]:
    symbols = body.get("symbols")
    returns = body.get("returns")
    if (symbols is None) == (returns is None):
        raise ValidationError("Provide exactly one of symbols or returns")
    if symbols is not None:
        return {"symbols": validate_symbols(symbols, minimum_symbols), "returns": None}
    if not isinstance(returns, dict) or not returns:
        raise ValidationError(
            "returns must be an object mapping asset names to lists", "returns"
        )
    if len(returns) > MAX_RETURN_COLUMNS:
        raise ValidationError(
            f"returns supports at most {MAX_RETURN_COLUMNS} assets", "returns"
        )
    lengths = set()
    for name, values in returns.items():
        if not isinstance(name, str) or not COLUMN_PATTERN.match(name):
            raise ValidationError(
                "Asset names may only contain letters, digits, spaces and . _ -",
                "returns",
            )
        if not isinstance(values, list) or not 30 <= len(values) <= MAX_RETURN_ROWS:
            raise ValidationError(
                f"Each returns list needs 30 to {MAX_RETURN_ROWS} values", "returns"
            )
        if not all(
            isinstance(v, (int, float)) and not isinstance(v, bool) for v in values
        ):
            raise ValidationError("returns must contain only numbers", "returns")
        lengths.add(len(values))
    if len(lengths) != 1:
        raise ValidationError("All returns lists must have the same length", "returns")
    return {"symbols": None, "returns": returns}


def weights_for(body: Dict[str, Any], source: Dict[str, Any]) -> Optional[Any]:
    value = body.get("weights")
    if value is None:
        return None
    if isinstance(value, list):
        if not value or len(value) > MAX_RETURN_COLUMNS:
            raise ValidationError("weights must be a non-empty list", "weights")
        cleaned: Any = [validate_number(v, "weights", 0.0, 1e9) for v in value]
        total = sum(cleaned)
    elif isinstance(value, dict) and value:
        cleaned = {}
        for key, weight in value.items():
            if not isinstance(key, str) or not COLUMN_PATTERN.match(key):
                raise ValidationError("Invalid weight key", "weights")
            label = key.strip().upper() if source["symbols"] is not None else key
            cleaned[label] = validate_number(weight, f"weights.{key}", 0.0, 1e9)
        total = sum(cleaned.values())
    else:
        raise ValidationError("weights must be a non-empty object or list", "weights")
    if total <= 0:
        raise ValidationError("weights must sum to a positive value", "weights")
    if isinstance(cleaned, list):
        return [w / total for w in cleaned]
    return {key: w / total for key, w in cleaned.items()}


def portfolio_request(body: Any) -> Dict[str, Any]:
    body = require_body(body)
    source = data_source(body)
    return {**source, "weights": weights_for(body, source), "_body": body}


def finish(request: Dict[str, Any]) -> Dict[str, Any]:
    request.pop("_body", None)
    return request


def evt(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["confidence_levels"] = confidence_levels(raw)
    request["threshold_quantile"] = validate_number(
        raw.get("threshold_quantile"), "threshold_quantile", 0.01, 0.3, 0.1
    )
    request["seed"] = seed(raw)
    return finish(request)


def ml(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["model_type"] = choice(
        raw.get("model_type"), "model_type", ML_MODEL_TYPES, "gbm"
    )
    request["confidence_levels"] = confidence_levels(raw)
    request["feature_window"] = validate_integer(
        raw.get("feature_window"), "feature_window", 5, 60, 10
    )
    request["horizon"] = validate_integer(raw.get("horizon"), "horizon", 1, 10, 1)
    return finish(request)


def copula(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["copula_type"] = choice(
        raw.get("copula_type"), "copula_type", COPULA_TYPES, "gaussian"
    )
    request["confidence_levels"] = confidence_levels(raw)
    request["n_scenarios"] = validate_integer(
        raw.get("n_scenarios"), "n_scenarios", 100, 200_000, 20_000
    )
    request["seed"] = seed(raw)
    return finish(request)


def hybrid(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["traditional_weight"] = validate_number(
        raw.get("traditional_weight"), "traditional_weight", 0.0, 1.0, 0.5
    )
    request["ml_model_type"] = choice(
        raw.get("ml_model_type"), "ml_model_type", ML_MODEL_TYPES, "gbm"
    )
    request["copula_type"] = choice(
        raw.get("copula_type"), "copula_type", COPULA_TYPES, "gaussian"
    )
    request["confidence_levels"] = confidence_levels(raw)
    request["seed"] = seed(raw)
    return finish(request)


def monte_carlo(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["copula_type"] = choice(
        raw.get("copula_type"), "copula_type", COPULA_TYPES, "t"
    )
    request["n_scenarios"] = validate_integer(
        raw.get("n_scenarios"), "n_scenarios", 100, 200_000, 50_000
    )
    request["confidence_levels"] = confidence_levels(raw)
    request["seed"] = seed(raw)
    return finish(request)


def batch(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["risk_models"] = choices(raw.get("risk_models"), "risk_models", RISK_MODELS)
    request["confidence_levels"] = confidence_levels(raw)
    return finish(request)


def scenarios_spec(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if (
        not isinstance(value, dict)
        or not value
        or len(value) > MAX_SCENARIO_DEFINITIONS
    ):
        raise ValidationError(
            f"scenarios must be an object with 1 to {MAX_SCENARIO_DEFINITIONS} entries",
            "scenarios",
        )
    cleaned = {}
    for name, spec in value.items():
        if (
            not isinstance(name, str)
            or not COLUMN_PATTERN.match(name)
            or not isinstance(spec, dict)
        ):
            raise ValidationError("Invalid scenario definition", "scenarios")
        shocks = spec.get("shocks")
        if not isinstance(shocks, dict) or not shocks:
            raise ValidationError(
                "Each scenario needs a non-empty shocks object", "scenarios"
            )
        cleaned[name] = {
            "description": str(spec.get("description", name))[:200],
            "shocks": {
                str(key): validate_number(shock, f"scenarios.{name}.{key}", -1.0, 1.0)
                for key, shock in shocks.items()
            },
        }
    return cleaned


def stress(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["scenarios"] = scenarios_spec(raw.get("scenarios"))
    request["n_custom_scenarios"] = validate_integer(
        raw.get("n_custom_scenarios"), "n_custom_scenarios", 1, 5000, 100
    )
    classes = raw.get("asset_classes")
    if classes is not None:
        if not isinstance(classes, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in classes.items()
        ):
            raise ValidationError(
                "asset_classes must map asset names to class names", "asset_classes"
            )
    request["asset_classes"] = classes
    request["seed"] = seed(raw)
    return finish(request)


def backtest(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["risk_models"] = choices(raw.get("risk_models"), "risk_models", RISK_MODELS)
    request["confidence_level"] = validate_number(
        raw.get("confidence_level"), "confidence_level", 0.5, 0.999, 0.95
    )
    request["window_size"] = validate_integer(
        raw.get("window_size"), "window_size", 30, 2000, 252
    )
    request["step_size"] = validate_integer(
        raw.get("step_size"), "step_size", 1, 250, 20
    )
    return finish(request)


def sensitivity(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    shock_range = raw.get("shock_range", [-0.1, 0.1])
    if not isinstance(shock_range, list) or len(shock_range) != 2:
        raise ValidationError(
            "shock_range must be a list of two numbers", "shock_range"
        )
    low = validate_number(shock_range[0], "shock_range", -1.0, 1.0)
    high = validate_number(shock_range[1], "shock_range", -1.0, 1.0)
    if low >= high:
        raise ValidationError("shock_range must be increasing", "shock_range")
    request["shock_range"] = [low, high]
    request["n_points"] = validate_integer(raw.get("n_points"), "n_points", 2, 50, 10)
    return finish(request)


def decomposition(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    request["risk_measure"] = choice(
        raw.get("risk_measure"), "risk_measure", RISK_MEASURES, "volatility"
    )
    request["confidence"] = validate_number(
        raw.get("confidence"), "confidence", 0.5, 0.9999, 0.95
    )
    return finish(request)


def analysis(body: Any) -> Dict[str, Any]:
    raw = require_body(body)
    request = data_source(raw)
    request["confidence"] = validate_number(
        raw.get("confidence"), "confidence", 0.5, 0.9999, 0.99
    )
    request["horizon"] = validate_integer(raw.get("horizon"), "horizon", 1, 60, 5)
    request["stress_multiplier"] = validate_number(
        raw.get("stress_multiplier"), "stress_multiplier", 0.1, 20.0, 4.0
    )
    request["n_simulations"] = validate_integer(
        raw.get("n_simulations"), "n_simulations", 100, 200_000, 10_000
    )
    request["seed"] = seed(raw)
    return request


def portfolio_search(body: Any) -> Dict[str, Any]:
    raw = require_body(body)
    request = data_source(raw, minimum_symbols=2)
    request["risk_model"] = choice(
        raw.get("risk_model"), "risk_model", OPTIMIZATION_RISK_MODELS, "markowitz"
    )
    request["n_portfolios"] = validate_integer(
        raw.get("n_portfolios"), "n_portfolios", 10, 100_000, 5000
    )
    for field, low, high in (("target_return", -1.0, 10.0), ("target_risk", 0.0, 10.0)):
        value = raw.get(field)
        request[field] = (
            None if value is None else validate_number(value, field, low, high)
        )
    request["seed"] = seed(raw)
    return request


def mean_variance(body: Any) -> Dict[str, Any]:
    raw = require_body(body)
    symbols = validate_symbols(raw.get("symbols"), 2)
    request: Dict[str, Any] = {"symbols": symbols}
    request["risk_free_rate"] = validate_number(
        raw.get("risk_free_rate"), "risk_free_rate", 0.0, 0.5, 0.02
    )
    request["max_weight"] = validate_number(
        raw.get("max_weight"), "max_weight", 0.01, 1.0, 1.0
    )
    value = raw.get("portfolio_value")
    request["portfolio_value"] = (
        None if value is None else validate_number(value, "portfolio_value", 1.0, 1e12)
    )
    return request


def report(body: Any) -> Dict[str, Any]:
    request = portfolio_request(body)
    raw = request["_body"]
    title = raw.get("title", "Portfolio Risk Report")
    if not isinstance(title, str) or not title.strip() or len(title) > 120:
        raise ValidationError(
            "title must be a non-empty string of at most 120 characters", "title"
        )
    request["title"] = title.strip()
    request["confidence_levels"] = confidence_levels(raw)
    request["report_format"] = choice(
        raw.get("format"), "format", REPORT_FORMATS, "html"
    )
    recipients = raw.get("recipients")
    if recipients is not None:
        try:
            recipients = validate_recipients(recipients)
        except ValueError as error:
            raise ValidationError(str(error), "recipients") from error
    request["recipients"] = recipients
    return finish(request)


VALIDATORS: Dict[str, Callable[[Any], Dict[str, Any]]] = {
    "evt": evt,
    "ml_risk": ml,
    "copula_risk": copula,
    "hybrid_risk": hybrid,
    "monte_carlo": monte_carlo,
    "batch_risk": batch,
    "stress_test": stress,
    "backtest": backtest,
    "sensitivity": sensitivity,
    "decomposition": decomposition,
    "analysis": analysis,
    "portfolio_search": portfolio_search,
    "mean_variance": mean_variance,
    "generate_report": report,
}
