import logging
from typing import Any

from flask import Blueprint, g, jsonify
from src.api.controllers.optimization_controller import handle_errors, success
from src.api.middleware.auth_middleware import jwt_required
from src.core.exceptions import NotFoundError
from src.domain.services.portfolio_service import portfolio_service

logger = logging.getLogger(__name__)

my_portfolio_bp = Blueprint("my_portfolios", __name__, url_prefix="/api/v1/portfolios")

DEFAULT_CURRENCY = "USD"


@my_portfolio_bp.route("", methods=["GET"])
@jwt_required()
@handle_errors("Portfolio listing")
def list_my_portfolios() -> Any:
    portfolios = portfolio_service.get_user_portfolios(g.user["id"])
    return success(
        {
            "portfolios": [
                {
                    "id": item["id"],
                    "name": item["name"],
                    "description": item.get("description"),
                    "total_value": float(item.get("total_value") or 0),
                    "currency": DEFAULT_CURRENCY,
                    "risk_score": None,
                    "created_at": item.get("created_at"),
                    "updated_at": item.get("updated_at"),
                }
                for item in portfolios
            ]
        }
    )


@my_portfolio_bp.route("/<int:portfolio_id>", methods=["GET"])
@jwt_required()
@handle_errors("Portfolio details")
def get_my_portfolio(portfolio_id: int) -> Any:
    try:
        details = portfolio_service.get_portfolio_details(portfolio_id, g.user["id"])
    except NotFoundError as error:
        return jsonify({"status": "error", "error": error.to_dict()}), 404
    return success(details)
