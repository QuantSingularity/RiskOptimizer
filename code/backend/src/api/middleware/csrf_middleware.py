import secrets
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from flask import Response, current_app, g, jsonify, request
from src.core.config import config
from src.core.exceptions import RiskOptimizerException, SecurityError
from src.core.logging import get_logger

logger = get_logger(__name__)


def create_error_response(error: RiskOptimizerException) -> Dict[str, Any]:
    """
    Create standardized error response.

    Args:
        error: Exception instance

    Returns:
        Standardized error response dictionary
    """
    return {"status": "error", "error": error.to_dict()}


def generate_csrf_token() -> str:
    """
    Generate a CSRF token.

    Returns:
        CSRF token
    """
    return secrets.token_urlsafe(32)


def csrf_protect(exempt_methods: Optional[List[str]] = None) -> Callable:
    """
    Decorator to apply CSRF protection to API endpoints.

    Args:
        exempt_methods: List of HTTP methods exempt from CSRF protection (default: GET, HEAD, OPTIONS)

    Returns:
        Decorated function
    """
    if exempt_methods is None:
        exempt_methods = ["GET", "HEAD", "OPTIONS"]

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs) -> object:
            if request.method in exempt_methods:
                return func(*args, **kwargs)
            if current_app.testing and config.environment == "testing":
                return func(*args, **kwargs)
            csrf_token = request.headers.get("X-CSRF-Token")
            session_token = getattr(g, "csrf_token", None)
            if not csrf_token or not session_token or csrf_token != session_token:
                logger.warning(
                    f"CSRF token validation failed for {request.endpoint}. Provided: {csrf_token}, Expected: {session_token}"
                )
                error = SecurityError("CSRF token validation failed")
                response = jsonify(create_error_response(error))
                return (response, 403)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def apply_csrf_protection(app: object) -> None:
    """
    Apply CSRF protection to all API endpoints.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request() -> None:
        """
        Generate CSRF token for each request.
        The token is stored in the `g` object and added to response headers.
        """
        if request.path.startswith("/api") and request.method not in [
            "GET",
            "HEAD",
            "OPTIONS",
        ]:
            if not hasattr(g, "csrf_token") or g.csrf_token is None:
                g.csrf_token = generate_csrf_token()
            logger.debug(f"Generated CSRF token: {g.csrf_token}")

    @app.after_request
    def after_request(response: Response) -> Response:
        """
        Add CSRF token to response headers for API endpoints.
        """
        if request.path.startswith("/api"):
            if hasattr(g, "csrf_token") and g.csrf_token is not None:
                response.headers["X-CSRF-Token"] = g.csrf_token
                response.headers["Access-Control-Expose-Headers"] = "X-CSRF-Token"
        return response

    for rule in app.url_map.iter_rules():
        if rule.rule.startswith("/static") or not rule.rule.startswith("/api"):
            continue
        endpoint = app.view_functions.get(rule.endpoint)
        if (
            endpoint
            and rule.methods
            and any(
                (method not in ["GET", "HEAD", "OPTIONS"] for method in rule.methods)
            )
        ):
            if (
                not hasattr(endpoint, "__wrapped__")
                or endpoint.__wrapped__ != csrf_protect().__wrapped__
            ):
                app.view_functions[rule.endpoint] = csrf_protect()(endpoint)
