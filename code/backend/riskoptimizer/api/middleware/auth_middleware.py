import logging
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, Union

from flask import g, jsonify, request
from riskoptimizer.core.exceptions import AuthenticationError, AuthorizationError
from riskoptimizer.domain.services.auth_service import auth_service

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
    if hasattr(error, "to_dict"):
        error_data = error.to_dict()
    else:
        error_data = {"code": "INTERNAL_ERROR", "message": str(error), "details": {}}

    return {"status": "error", "error": error_data}


def get_token_from_header() -> str:
    """
    Extract JWT token from Authorization header.

    Returns:
        JWT token

    Raises:
        AuthenticationError: If token is missing or invalid
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise AuthenticationError("Missing Authorization header")

    parts = auth_header.split()
    if parts[0].lower() != "bearer":
        raise AuthenticationError("Authorization header must start with Bearer")

    if len(parts) == 1:
        raise AuthenticationError("Token not found in Authorization header")

    if len(parts) > 2:
        raise AuthenticationError(
            "Authorization header must be in the format 'Bearer token'"
        )

    return parts[1]


def jwt_required(roles: Optional[Union[str, List[str]]] = None) -> Callable:
    """
    Decorator to protect API endpoints with JWT authentication.

    Args:
        roles: Required role(s) for access (optional). Can be a single role string or a list of role strings.

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                # Get token from header
                token = get_token_from_header()

                # Verify token
                payload = auth_service.verify_token(token)

                # Store user info in g for access in route handlers
                g.user = {
                    "id": payload["user_id"],
                    "email": payload["email"],
                    "role": payload.get(
                        "role", "user"
                    ),  # Default to 'user' role if not present
                }

                # Check role if required
                if roles:
                    required_roles = [roles] if isinstance(roles, str) else roles
                    if g.user["role"] not in required_roles:
                        logger.warning(
                            f"Authorization failed: User {g.user['id']} with role {g.user['role']} attempted to access endpoint requiring {required_roles}"
                        )
                        raise AuthorizationError(
                            f"Insufficient permissions. Required role(s): {', '.join(required_roles)}"
                        )

                # Call the original function
                return func(*args, **kwargs)

            except AuthenticationError as e:
                logger.warning(f"Authentication error: {str(e)}")
                response = create_error_response(e)
                return jsonify(response), 401

            except AuthorizationError as e:
                logger.warning(f"Authorization error: {str(e)}")
                response = create_error_response(e)
                return jsonify(response), 403

            except Exception as e:
                logger.error(
                    f"Unexpected error in auth middleware: {str(e)}", exc_info=True
                )
                error = AuthenticationError(f"Authentication failed: {str(e)}")
                response = create_error_response(error)
                return jsonify(response), 401

        return wrapper

    return decorator


def admin_required(func: Callable) -> Callable:
    """
    Decorator to restrict access to admin users only.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """
    return jwt_required(roles="admin")(func)


def optional_jwt(func: Callable) -> Callable:
    """
    Decorator to optionally authenticate with JWT.
    Does not require authentication but will process token if provided.

    Args:
        func: Function to decorate

    Returns:
        Decorated function
    """

    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            # Initialize g.user as None
            g.user = None

            # Check if Authorization header exists
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.lower().startswith("bearer "):
                # Get token from header
                token = auth_header.split(" ")[1]

                # Verify token
                payload = auth_service.verify_token(token)

                # Store user info in g for access in route handlers
                g.user = {
                    "id": payload["user_id"],
                    "email": payload["email"],
                    "role": payload.get("role", "user"),
                }
        except Exception:
            # Ignore authentication errors
            pass

        # Call the original function
        return func(*args, **kwargs)

    return wrapper
