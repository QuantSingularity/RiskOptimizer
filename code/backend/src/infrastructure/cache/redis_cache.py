"""
Redis cache implementation for the RiskOptimizer application.
Provides a Redis-backed cache with JSON serialization and graceful fallback.
"""

import json
import logging
import os
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class RedisCache:
    """
    Redis-backed cache with JSON serialization.
    Falls back gracefully when Redis is unavailable.
    """

    def __init__(self) -> None:
        self._client = None
        self._available = False
        self._connect()

    def _connect(self) -> None:
        """Attempt to connect to Redis."""
        try:
            import redis

            redis_host = os.getenv("REDIS_HOST", "localhost")
            redis_port = int(os.getenv("REDIS_PORT", "6379"))
            redis_db = int(os.getenv("REDIS_DB", "0"))
            redis_password = os.getenv("REDIS_PASSWORD") or None
            socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", "30"))
            socket_connect_timeout = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "5"))

            self._client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=True,
                retry_on_timeout=True,
            )
            self._client.ping()
            self._available = True
            logger.info(f"Redis connected at {redis_host}:{redis_port}/{redis_db}")
        except Exception as e:
            self._available = False
            logger.warning(f"Redis unavailable, running without cache: {e}")

    def _serialize(self, value: Any) -> str:
        """Serialize value to JSON string."""
        return json.dumps(value, default=str)

    def _deserialize(self, value: Optional[str]) -> Any:
        """Deserialize JSON string to Python object."""
        if value is None:
            return None
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value

    def get(self, key: str) -> Any:
        """
        Get a value from the cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self._available:
            return None
        try:
            value = self._client.get(key)
            return self._deserialize(value)
        except Exception as e:
            logger.warning(f"Redis GET error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: int = 3600) -> bool:
        """
        Set a value in the cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._available:
            return False
        try:
            serialized = self._serialize(value)
            self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.warning(f"Redis SET error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.

        Args:
            key: Cache key

        Returns:
            True if the key was deleted, False otherwise
        """
        if not self._available:
            return False
        try:
            return bool(self._client.delete(key))
        except Exception as e:
            logger.warning(f"Redis DELETE error for key '{key}': {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.

        Args:
            key: Cache key

        Returns:
            True if the key exists, False otherwise
        """
        if not self._available:
            return False
        try:
            return bool(self._client.exists(key))
        except Exception as e:
            logger.warning(f"Redis EXISTS error for key '{key}': {e}")
            return False

    def incr(self, key: str) -> int:
        """
        Increment a counter in the cache.

        Args:
            key: Cache key

        Returns:
            New counter value
        """
        if not self._available:
            return 0
        try:
            return self._client.incr(key)
        except Exception as e:
            logger.warning(f"Redis INCR error for key '{key}': {e}")
            return 0

    def expire(self, key: str, ttl: int) -> bool:
        """
        Set expiration on a key.

        Args:
            key: Cache key
            ttl: Time to live in seconds

        Returns:
            True if successful, False otherwise
        """
        if not self._available:
            return False
        try:
            return bool(self._client.expire(key, ttl))
        except Exception as e:
            logger.warning(f"Redis EXPIRE error for key '{key}': {e}")
            return False

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is reachable, False otherwise
        """
        if not self._available:
            return False
        try:
            self._client.ping()
            return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._available = False
            return False


redis_cache = RedisCache()
