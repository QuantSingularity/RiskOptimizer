import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import Blueprint, Response, jsonify, request
from src.api.middleware.auth_middleware import admin_required, jwt_required
from src.api.schemas.optimization_schema import (
    FORECAST_MODELS,
    MAX_FORECAST_PERIODS,
    MAX_SYMBOLS,
    OPTIMIZATION_METHODS,
    validate_forecast_args,
    validate_frontier_request,
    validate_optimize_request,
    validate_sentiment_request,
    validate_simulation_request,
    validate_training_request,
)
from src.core.exceptions import (
    CalculationError,
    ModelError,
    RiskOptimizerException,
    ValidationError,
)
from src.services.ai_optimization import get_ai_service

logger = logging.getLogger(__name__)

optimization_bp = Blueprint("optimization", __name__, url_prefix="/api/v1/optimization")

STATUS_BY_ERROR = (
    (ValidationError, 400),
    (CalculationError, 422),
    (ModelError, 503),
)


def success(data: Any, message: Optional[str] = None) -> Response:
    body: Dict[str, Any] = {"status": "success", "data": data}
    if message:
        body["message"] = message
    return jsonify(body)


def failure(error: RiskOptimizerException, status: int) -> Any:
    return jsonify({"status": "error", "error": error.to_dict()}), status


def handle_errors(operation: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except RiskOptimizerException as error:
                for error_type, status in STATUS_BY_ERROR:
                    if isinstance(error, error_type):
                        logger.warning("%s rejected: %s", operation, error)
                        return failure(error, status)
                logger.error("%s failed: %s", operation, error, exc_info=True)
                return failure(error, 500)
            except Exception as error:
                logger.error(
                    "%s failed unexpectedly: %s", operation, error, exc_info=True
                )
                return failure(
                    RiskOptimizerException(f"{operation} failed", "INTERNAL_ERROR"), 500
                )

        return wrapper

    return decorator


@optimization_bp.route("/optimize", methods=["POST"])
@jwt_required()
@handle_errors("Portfolio optimization")
def optimize_portfolio() -> Any:
    params = validate_optimize_request(request.get_json(silent=True))
    result = get_ai_service().optimize_portfolio(
        market_data=params["market_data"],
        risk_tolerance=params["risk_tolerance"],
        min_weight=params["min_weight"],
        max_weight=params["max_weight"],
        symbols=params["symbols"],
        method=params["method"],
    )
    return success(result, "Portfolio optimized successfully")


@optimization_bp.route("/efficient-frontier", methods=["POST"])
@jwt_required()
@handle_errors("Efficient frontier")
def efficient_frontier() -> Any:
    params = validate_frontier_request(request.get_json(silent=True))
    result = get_ai_service().efficient_frontier(
        market_data=params["market_data"],
        risk_tolerance=params["risk_tolerance"],
        points=params["points"],
        min_weight=params["min_weight"],
        max_weight=params["max_weight"],
        symbols=params["symbols"],
    )
    return success(result)


@optimization_bp.route("/simulate", methods=["POST"])
@jwt_required()
@handle_errors("Risk simulation")
def simulate() -> Any:
    params = validate_simulation_request(request.get_json(silent=True))
    result = get_ai_service().run_risk_simulation(
        market_data=params["market_data"],
        weights=params["weights"],
        num_simulations=params["num_simulations"],
        time_horizon=params["time_horizon"],
        symbols=params["symbols"],
        initial_value=params["initial_value"],
        seed=params["seed"],
    )
    return success(result)


@optimization_bp.route("/forecast/<ticker>", methods=["GET"])
@jwt_required()
@handle_errors("Price forecast")
def forecast(ticker: str) -> Any:
    params = validate_forecast_args(
        ticker, request.args.get("periods"), request.args.get("model")
    )
    return success(
        get_ai_service().forecast(params["ticker"], params["periods"], params["model"])
    )


@optimization_bp.route("/sentiment", methods=["POST"])
@jwt_required()
@handle_errors("Sentiment analysis")
def sentiment() -> Any:
    params = validate_sentiment_request(request.get_json(silent=True))
    return success(get_ai_service().analyze_sentiment(params["texts"]))


@optimization_bp.route("/symbols", methods=["GET"])
@jwt_required()
@handle_errors("Symbol listing")
def symbols() -> Any:
    return success({"symbols": get_ai_service().get_model_info()["available_symbols"]})


@optimization_bp.route("/constraints", methods=["GET"])
@jwt_required()
@handle_errors("Constraint listing")
def constraints() -> Any:
    return success(
        {
            "risk_tolerance": {"min": 1, "max": 10, "default": 5},
            "weights": {"min": 0.0, "max": 1.0},
            "methods": list(OPTIMIZATION_METHODS),
            "max_symbols": MAX_SYMBOLS,
            "max_forecast_periods": MAX_FORECAST_PERIODS,
            "forecast_models": list(FORECAST_MODELS),
            "long_only": True,
        }
    )


@optimization_bp.route("/model", methods=["GET"])
@jwt_required()
@handle_errors("Model info")
def model_info() -> Any:
    return success(get_ai_service().get_model_info())


@optimization_bp.route("/model/train", methods=["POST"])
@admin_required
@handle_errors("Model training")
def train_model() -> Any:
    params = validate_training_request(request.get_json(silent=True))
    result = get_ai_service().retrain(params["symbols"], params["risk_tolerance"])
    return success(result, "Model trained successfully")
