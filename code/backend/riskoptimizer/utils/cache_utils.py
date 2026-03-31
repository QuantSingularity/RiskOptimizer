"""
Caching decorators and utilities for performance optimization.
Provides caching functionality for frequently accessed data and expensive computations.
"""

import hashlib
import json
import logging
from functools import wraps
from typing import Any, Callable, Dict, Optional

from riskoptimizer.infrastructure.cache.redis_cache import redis_cache

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def generate_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    Generate a cache key from function arguments.

    Args:
        prefix: Cache key prefix
        *args: Function positional arguments
        **kwargs: Function keyword arguments

    Returns:
        Generated cache key
    """
    args_str = json.dumps(args, sort_keys=True, default=str)
    kwargs_str = json.dumps(kwargs, sort_keys=True, default=str)
    args_hash = hashlib.md5(f"{args_str}:{kwargs_str}".encode()).hexdigest()
    return f"{prefix}:{args_hash}"


def cache_result(
    prefix: str, ttl: int = 3600, key_func: Optional[Callable] = None
) -> Callable:
    """
    Decorator to cache function results.

    Args:
        prefix: Cache key prefix
        ttl: Time to live in seconds (default: 1 hour)
        key_func: Custom function to generate cache key (optional)

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = generate_cache_key(prefix, *args, **kwargs)
                cached_result = redis_cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit for key: {cache_key}")
                    return cached_result
                logger.debug(f"Cache miss for key: {cache_key}")
                result = func(*args, **kwargs)
                redis_cache.set(cache_key, result, ttl=ttl)
                return result
            except Exception as e:
                logger.error(f"Error in cache decorator: {str(e)}", exc_info=True)
                return func(*args, **kwargs)

        return wrapper

    return decorator


def cache_invalidate(prefix: str, key_func: Optional[Callable] = None) -> Callable:
    """
    Decorator to invalidate cache entries.

    Args:
        prefix: Cache key prefix
        key_func: Custom function to generate cache key (optional)

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            try:
                result = func(*args, **kwargs)
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    cache_key = generate_cache_key(prefix, *args, **kwargs)
                redis_cache.delete(cache_key)
                logger.debug(f"Cache invalidated for key: {cache_key}")
                return result
            except Exception as e:
                logger.error(
                    f"Error in cache invalidation decorator: {str(e)}", exc_info=True
                )
                return func(*args, **kwargs)

        return wrapper

    return decorator


def memoize(ttl: int = 3600) -> Callable:
    """
    Simple memoization decorator using Redis cache.

    Args:
        ttl: Time to live in seconds (default: 1 hour)

    Returns:
        Decorated function
    """

    def decorator(func: Callable) -> Callable:

        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            func_name = f"{func.__module__}.{func.__name__}"
            cache_key = generate_cache_key(func_name, *args, **kwargs)
            try:
                cached_result = redis_cache.get(cache_key)
                if cached_result is not None:
                    logger.debug(f"Memoization cache hit for: {func_name}")
                    return cached_result
                logger.debug(f"Memoization cache miss for: {func_name}")
                result = func(*args, **kwargs)
                redis_cache.set(cache_key, result, ttl=ttl)
                return result
            except Exception as e:
                logger.error(f"Error in memoization decorator: {str(e)}", exc_info=True)
                return func(*args, **kwargs)

        return wrapper

    return decorator


class CacheManager:
    """Manager for cache operations and strategies."""

    def __init__(self) -> None:
        """Initialize cache manager."""
        self.cache = redis_cache

    def warm_cache(self, cache_keys: Dict[str, Callable]) -> None:
        """
        Warm up cache with frequently accessed data.

        Args:
            cache_keys: Dictionary mapping cache keys to functions that generate the data
        """
        for key, func in cache_keys.items():
            try:
                if not self.cache.exists(key):
                    data = func()
                    self.cache.set(key, data, ttl=3600)
                    logger.info(f"Cache warmed for key: {key}")
            except Exception as e:
                logger.error(
                    f"Error warming cache for key {key}: {str(e)}", exc_info=True
                )

    def clear_pattern(self, pattern: str) -> int:
        """
        Clear cache entries matching a pattern.

        Args:
            pattern: Cache key pattern (e.g., "portfolio:*")

        Returns:
            Number of keys deleted
        """
        try:
            logger.warning(f"Pattern-based cache clearing not implemented: {pattern}")
            return 0
        except Exception as e:
            logger.error(
                f"Error clearing cache pattern {pattern}: {str(e)}", exc_info=True
            )
            return 0

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        try:
            is_healthy = self.cache.health_check()
            return {"healthy": is_healthy, "backend": "redis"}
        except Exception as e:
            logger.error(f"Error getting cache stats: {str(e)}", exc_info=True)
            return {"healthy": False, "backend": "redis", "error": str(e)}


cache_manager = CacheManager()
