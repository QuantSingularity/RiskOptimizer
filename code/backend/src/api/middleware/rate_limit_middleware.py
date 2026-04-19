"""
Rate limiting middleware for the API.
Implements rate limiting to prevent abuse of the API.
"""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

from flask import Response, g, jsonify, request
from src.core.config import config
from src.core.exceptions import RateLimitError, RiskOptimizerException
from src.infrastructure.cache.redis_cache import redis_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def create_error_response(error: RiskOptimizerException) -> Dict[str, Any]:
    """
    Create standardized error response.

    Args:
        error: Exception instance

    Returns:
        Standardized error response dictionary
    """
    return {"status": "error", "error": error.to_dict()}


def get_rate_limit_key(endpoint: str) -> str:
    """
    Get rate limit cache key for the current request.

    Args:
        endpoint: API endpoint name

    Returns:
        Cache key for rate limiting
    """
    client_ip = request.remote_addr
    user_id = getattr(g, "user", {}).get("id", "anonymous")
    return f"rate_limit:{endpoint}:{user_id}:{client_ip}"


def rate_limit(
    requests_per_minute: Optional[int] = None, burst: Optional[int] = None
) -> Callable:
    """
    Decorator to apply rate limiting to API endpoints.

    Args:
        requests_per_minute: Maximum number of requests per minute (default: from config)
        burst: Maximum burst size (default: from config)

    Returns:
        Decorated function
    """
    if requests_per_minute is None:
        requests_per_minute = config.security.rate_limit_per_minute
    if burst is None:
        burst = requests_per_minute * 2

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs) -> object:
            try:
                endpoint = request.endpoint or "unknown"
                key = get_rate_limit_key(endpoint)
                now = int(time.time())
                window_start = now - 60
                count = redis_cache.get(key) or []
                count = [ts for ts in count if ts > window_start]
                effective_limit = (
                    burst if burst > requests_per_minute else requests_per_minute
                )
                if len(count) >= effective_limit:
                    logger.warning(
                        f"Rate limit exceeded for {endpoint}: {len(count)} requests in last minute"
                    )
                    reset_time = count[0] + 60 - now if count else 60
                    error = RateLimitError(
                        f"Rate limit exceeded. Maximum {requests_per_minute} requests per minute allowed.",
                        reset_time=reset_time,
                        limit=requests_per_minute,
                    )
                    response = jsonify(create_error_response(error))
                    response.headers["X-RateLimit-Limit"] = str(requests_per_minute)
                    response.headers["X-RateLimit-Remaining"] = "0"
                    response.headers["X-RateLimit-Reset"] = str(reset_time)
                    response.headers["Retry-After"] = str(reset_time)
                    return (response, 429)
                count.append(now)
                redis_cache.set(key, count, ttl=60)
                response = func(*args, **kwargs)
                if isinstance(response, tuple) and len(response) == 2:
                    response_obj, status_code = response
                    if isinstance(response_obj, Response):
                        response_obj.headers["X-RateLimit-Limit"] = str(
                            requests_per_minute
                        )
                        response_obj.headers["X-RateLimit-Remaining"] = str(
                            max(0, requests_per_minute - len(count))
                        )
                        return (response_obj, status_code)
                return response
            except Exception as e:
                logger.error(f"Error in rate limit middleware: {str(e)}", exc_info=True)
                return func(*args, **kwargs)

        return wrapper

    return decorator


def apply_rate_limiting(app: object) -> None:
    """
    Apply rate limiting to all API endpoints.

    Args:
        app: Flask application instance
    """
    for rule in app.url_map.iter_rules():
        endpoint = app.view_functions.get(rule.endpoint)
        if rule.rule.startswith("/static") or not rule.rule.startswith("/api"):
            continue
        if endpoint:
            app.view_functions[rule.endpoint] = rate_limit()(endpoint)
