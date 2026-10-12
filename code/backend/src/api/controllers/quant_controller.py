from typing import Any, Callable

from flask import Blueprint, request
from src.api.controllers.optimization_controller import handle_errors, success
from src.api.middleware.auth_middleware import jwt_required
from src.api.schemas.quant_schema import VALIDATORS
from src.core.exceptions import ValidationError
from src.services.quant_risk_service import get_quant_service

quant_bp = Blueprint("quant", __name__, url_prefix="/api/v1/quant")

OPERATIONS = [
    ("/risk/evt", "evt"),
    ("/risk/ml", "ml_risk"),
    ("/risk/copula", "copula_risk"),
    ("/risk/hybrid", "hybrid_risk"),
    ("/risk/monte-carlo", "monte_carlo"),
    ("/risk/batch", "batch_risk"),
    ("/risk/stress-test", "stress_test"),
    ("/risk/backtest", "backtest"),
    ("/risk/sensitivity", "sensitivity"),
    ("/risk/decomposition", "decomposition"),
    ("/risk/analysis", "analysis"),
    ("/portfolio/search", "portfolio_search"),
    ("/portfolio/mean-variance", "mean_variance"),
    ("/reports/risk", "generate_report"),
]


def register(path: str, operation: str) -> None:
    validator: Callable[[Any], dict] = VALIDATORS[operation]

    @jwt_required()
    @handle_errors(operation.replace("_", " ").capitalize())
    def view() -> Any:
        params = validator(request.get_json(silent=True))
        return success(getattr(get_quant_service(), operation)(**params))

    quant_bp.add_url_rule(path, f"quant_{operation}", view, methods=["POST"])


for _path, _operation in OPERATIONS:
    register(_path, _operation)


@quant_bp.route("/info", methods=["GET"])
@jwt_required()
@handle_errors("Quant info")
def info() -> Any:
    return success(get_quant_service().info())


@quant_bp.route("/reports", methods=["GET"])
@jwt_required()
@handle_errors("Report listing")
def list_reports() -> Any:
    raw = request.args.get("limit", "20")
    if not raw.isdigit() or not 1 <= int(raw) <= 100:
        raise ValidationError("limit must be an integer between 1 and 100", "limit")
    return success(get_quant_service().list_reports(int(raw)))


@quant_bp.route("/reports/<report_id>", methods=["GET"])
@jwt_required()
@handle_errors("Report retrieval")
def get_report(report_id: str) -> Any:
    return success(get_quant_service().get_report(report_id))
