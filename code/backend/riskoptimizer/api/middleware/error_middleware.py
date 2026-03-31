import logging
import traceback
from typing import Any, Dict, Union

import werkzeug.exceptions as werkzeug_exceptions
from flask import Flask, Response, current_app, g, jsonify, request
from riskoptimizer.core.exceptions import RiskOptimizerException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_error_response(error: Exception) -> Dict[str, Any]:
    """
    Create standardized error response.

    Args:
        error: Exception instance

    Returns:
        Standardized error response dictionary
    """
    response_data = {
        "status": "error",
        "error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "details": {},
        },
    }

    if isinstance(error, RiskOptimizerException):
        # Use custom exception's to_dict method
        response_data["error"] = error.to_dict()
    elif isinstance(error, werkzeug_exceptions.HTTPException):
        # Handle Werkzeug HTTP exceptions
        response_data["error"] = {
            "code": f"HTTP_{error.code}",
            "message": error.description,
            "details": {},
        }
        # Add traceback in development mode for HTTP exceptions as well
        if current_app.debug:
            response_data["error"]["details"]["traceback"] = [traceback.format_exc()]
    else:
        # Handle generic exceptions
        response_data["error"]["message"] = str(error) or "An unexpected error occurred"

        # Add traceback in development mode
        if current_app.debug:
            response_data["error"]["details"]["traceback"] = [traceback.format_exc()]

    return response_data


def register_error_handlers(app: Flask) -> None:
    """
    Register error handlers for the Flask application.

    Args:
        app: Flask application instance
    """

    @app.errorhandler(RiskOptimizerException)
    def handle_risk_optimizer_exception(
        error: RiskOptimizerException,
    ) -> Union[Response, tuple[Response, int]]:
        """
        Handle custom RiskOptimizer exceptions.
        Logs the error and returns a standardized JSON response.
        """
        status_code = 500

        # Map exception types to status codes
        if error.__class__.__name__ == "ValidationError":
            status_code = 400
        elif error.__class__.__name__ == "AuthenticationError":
            status_code = 401
        elif error.__class__.__name__ == "AuthorizationError":
            status_code = 403
        elif error.__class__.__name__ == "NotFoundError":
            status_code = 404
        elif error.__class__.__name__ == "ConflictError":
            status_code = 409
        elif error.__class__.__name__ == "RateLimitError":
            status_code = 429
        elif error.__class__.__name__ == "CalculationError":
            status_code = 422

        logger.error(
            f"{error.__class__.__name__}: {str(error)}",
            exc_info=True,
            extra={
                "error_code": error.error_code,
                "error_message": error.message,
                "error_details": error.details,
            },
        )
        response = create_error_response(error)
        return jsonify(response), status_code

    @app.errorhandler(werkzeug_exceptions.HTTPException)
    def handle_http_exception(
        error: werkzeug_exceptions.HTTPException,
    ) -> Union[Response, tuple[Response, int]]:
        """
        Handle Werkzeug HTTP exceptions (e.g., 404, 405).
        Logs the error and returns a standardized JSON response.
        """
        logger.error(
            f"HTTP Exception {error.code}: {error.description}",
            exc_info=True,
            extra={
                "http_status_code": error.code,
                "http_description": error.description,
            },
        )
        response = create_error_response(error)
        return jsonify(response), error.code or 500

    @app.errorhandler(Exception)
    def handle_generic_exception(
        error: Exception,
    ) -> Union[Response, tuple[Response, int]]:
        """
        Handle generic, unhandled exceptions.
        Logs the critical error and returns a generic internal server error response.
        """
        logger.critical(
            f"Unhandled exception: {str(error)}",
            exc_info=True,
            extra={
                "exception_type": type(error).__name__,
                "exception_message": str(error),
            },
        )
        response = create_error_response(error)
        return jsonify(response), 500

    # Specific HTTP error handlers for better logging context
    @app.errorhandler(404)
    def handle_not_found(
        error: werkzeug_exceptions.NotFound,
    ) -> Union[Response, tuple[Response, int]]:
        logger.warning(
            f"Not Found: {request.path}",
            extra={"path": request.path, "method": request.method},
        )
        response = create_error_response(error)
        return jsonify(response), 404

    @app.errorhandler(405)
    def handle_method_not_allowed(
        error: werkzeug_exceptions.MethodNotAllowed,
    ) -> Union[Response, tuple[Response, int]]:
        logger.warning(
            f"Method Not Allowed: {request.method} {request.path}",
            extra={"path": request.path, "method": request.method},
        )
        response = create_error_response(error)
        return jsonify(response), 405

    @app.errorhandler(500)
    def handle_server_error(
        error: werkzeug_exceptions.InternalServerError,
    ) -> Union[Response, tuple[Response, int]]:
        logger.critical(
            f"Internal Server Error: {str(error)}",
            exc_info=True,
            extra={
                "path": request.path,
                "method": request.method,
                "exception_message": str(error),
            },
        )
        response = create_error_response(error)
        return jsonify(response), 500


def error_handling_middleware(app: Flask) -> None:
    """
    Register error handling middleware for the Flask application.

    Args:
        app: Flask application instance
    """
    register_error_handlers(app)

    @app.before_request
    def before_request() -> None:
        """
        Set up request context (request ID, user ID, IP address) for logging.
        """
        # Generate request ID if not already set
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            import uuid

            request_id = str(uuid.uuid4())

        # Store request ID and user IP in g for access in other parts of the application
        g.request_id = request_id
        g.ip_address = request.remote_addr  # Capture client IP address

        # Add request ID and IP address to logger context
        logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.path,
                "ip_address": g.ip_address,
            },
        )

    @app.after_request
    def after_request(response: Response) -> Union[Response, tuple[Response, int]]:
        """
        Log after request and add security headers.
        """
        # Add request ID to response headers
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id

        # Add security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains; preload"  # HSTS
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'"  # Basic CSP, needs refinement
        )
        response.headers["Referrer-Policy"] = "no-referrer-when-downgrade"

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.path} {response.status_code}",
            extra={
                "request_id": getattr(g, "request_id", None),
                "method": request.method,
                "path": request.path,
                "status_code": response.status_code,
                "ip_address": getattr(g, "ip_address", None),
            },
        )

        return response
