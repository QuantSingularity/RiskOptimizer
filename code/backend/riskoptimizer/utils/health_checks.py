"""
Health check system for monitoring application health.
Provides comprehensive health checks for all application components.
"""

import logging
import os
import time
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from riskoptimizer.infrastructure.cache.redis_cache import redis_cache
from riskoptimizer.infrastructure.database.session import get_db_session
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health check status enumeration."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class HealthCheck:
    """Individual health check."""

    def __init__(
        self,
        name: str,
        check_func: Callable[[], Dict[str, Any]],
        timeout: float = 5.0,
        critical: bool = True,
    ) -> None:
        """
        Initialize health check.

        Args:
            name: Health check name
            check_func: Function that performs the health check
            timeout: Timeout in seconds
            critical: Whether this check is critical for overall health
        """
        self.name = name
        self.check_func = check_func
        self.timeout = timeout
        self.critical = critical

    def run(self) -> Dict[str, Any]:
        """
        Run the health check.

        Returns:
            Health check result
        """
        start_time = time.time()
        try:
            result = self.check_func()
            duration = time.time() - start_time
            status = result.get("status", HealthStatus.HEALTHY.value)
            return {
                "name": self.name,
                "status": status,
                "duration": duration,
                "critical": self.critical,
                "details": result.get("details", {}),
                "timestamp": time.time(),
            }
        except Exception as e:
            duration = time.time() - start_time
            logger.error(
                f"Health check failed for {self.name}: {str(e)}", exc_info=True
            )
            return {
                "name": self.name,
                "status": HealthStatus.UNHEALTHY.value,
                "duration": duration,
                "critical": self.critical,
                "error": str(e),
                "timestamp": time.time(),
            }


class HealthCheckManager:
    """Manager for all health checks."""

    def __init__(self) -> None:
        """Initialize health check manager."""
        self.checks: List[HealthCheck] = []
        self._register_default_checks()

    def register_check(self, check: HealthCheck) -> None:
        """
        Register a health check.

        Args:
            check: Health check to register
        """
        self.checks.append(check)
        logger.info(f"Registered health check: {check.name}")

    def _register_default_checks(self) -> None:
        """Register default health checks."""
        self.register_check(
            HealthCheck(
                name="database",
                check_func=self._check_database,
                timeout=5.0,
                critical=True,
            )
        )
        self.register_check(
            HealthCheck(
                name="redis", check_func=self._check_redis, timeout=3.0, critical=False
            )
        )
        self.register_check(
            HealthCheck(
                name="application",
                check_func=self._check_application,
                timeout=1.0,
                critical=True,
            )
        )

    def _check_database(self) -> Dict[str, Any]:
        """Check database health."""
        try:
            with get_db_session() as session:
                result = session.execute(text("SELECT 1")).scalar()
                if result == 1:
                    return {
                        "status": HealthStatus.HEALTHY.value,
                        "details": {"connection": "ok", "query_test": "passed"},
                    }
                else:
                    return {
                        "status": HealthStatus.UNHEALTHY.value,
                        "details": {
                            "connection": "ok",
                            "query_test": "failed",
                            "error": "Unexpected query result",
                        },
                    }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "details": {"connection": "failed", "error": str(e)},
            }

    def _check_redis(self) -> Dict[str, Any]:
        """Check Redis health."""
        try:
            is_healthy = redis_cache.health_check()
            if is_healthy:
                test_key = "health_check_test"
                test_value = "test_value"
                redis_cache.set(test_key, test_value, ttl=10)
                retrieved_value = redis_cache.get(test_key)
                if retrieved_value == test_value:
                    redis_cache.delete(test_key)
                    return {
                        "status": HealthStatus.HEALTHY.value,
                        "details": {"connection": "ok", "operations": "ok"},
                    }
                else:
                    return {
                        "status": HealthStatus.DEGRADED.value,
                        "details": {
                            "connection": "ok",
                            "operations": "failed",
                            "error": "Set/get operation failed",
                        },
                    }
            else:
                return {
                    "status": HealthStatus.UNHEALTHY.value,
                    "details": {"connection": "failed"},
                }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "details": {"connection": "failed", "error": str(e)},
            }

    def _check_application(self) -> Dict[str, Any]:
        """Check application health."""
        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            disk = psutil.disk_usage(os.path.abspath(os.sep))
            disk_usage = disk.used / disk.total * 100
            if memory_usage > 90 or disk_usage > 90:
                status = HealthStatus.UNHEALTHY.value
            elif memory_usage > 80 or disk_usage > 80:
                status = HealthStatus.DEGRADED.value
            else:
                status = HealthStatus.HEALTHY.value
            return {
                "status": status,
                "details": {
                    "memory_usage": memory_usage,
                    "disk_usage": disk_usage,
                    "uptime": time.time(),
                },
            }
        except Exception as e:
            return {
                "status": HealthStatus.UNHEALTHY.value,
                "details": {"error": str(e)},
            }

    def run_all_checks(self) -> Dict[str, Any]:
        """
        Run all health checks.

        Returns:
            Comprehensive health check result
        """
        start_time = time.time()
        results = []
        for check in self.checks:
            result = check.run()
            results.append(result)
        overall_status = self._determine_overall_status(results)
        total_duration = time.time() - start_time
        return {
            "status": overall_status,
            "timestamp": time.time(),
            "duration": total_duration,
            "checks": results,
            "summary": self._create_summary(results),
        }

    def _determine_overall_status(self, results: List[Dict[str, Any]]) -> str:
        """
        Determine overall health status from individual check results.

        Args:
            results: List of health check results

        Returns:
            Overall health status
        """
        critical_checks = [r for r in results if r.get("critical", True)]
        non_critical_checks = [r for r in results if not r.get("critical", True)]
        critical_unhealthy = any(
            (r["status"] == HealthStatus.UNHEALTHY.value for r in critical_checks)
        )
        critical_degraded = any(
            (r["status"] == HealthStatus.DEGRADED.value for r in critical_checks)
        )
        non_critical_unhealthy = any(
            (r["status"] == HealthStatus.UNHEALTHY.value for r in non_critical_checks)
        )
        if critical_unhealthy:
            return HealthStatus.UNHEALTHY.value
        elif critical_degraded or non_critical_unhealthy:
            return HealthStatus.DEGRADED.value
        else:
            return HealthStatus.HEALTHY.value

    def _create_summary(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Create summary of health check results.

        Args:
            results: List of health check results

        Returns:
            Summary of results
        """
        total_checks = len(results)
        healthy_checks = len(
            [r for r in results if r["status"] == HealthStatus.HEALTHY.value]
        )
        degraded_checks = len(
            [r for r in results if r["status"] == HealthStatus.DEGRADED.value]
        )
        unhealthy_checks = len(
            [r for r in results if r["status"] == HealthStatus.UNHEALTHY.value]
        )
        return {
            "total_checks": total_checks,
            "healthy": healthy_checks,
            "degraded": degraded_checks,
            "unhealthy": unhealthy_checks,
            "success_rate": (
                healthy_checks / total_checks * 100 if total_checks > 0 else 0
            ),
        }

    def get_check_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get health check result by name.

        Args:
            name: Health check name

        Returns:
            Health check result or None
        """
        for check in self.checks:
            if check.name == name:
                return check.run()
        return None


health_manager = HealthCheckManager()
