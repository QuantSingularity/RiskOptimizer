"""
Celery application configuration for RiskOptimizer.
Handles asynchronous task processing for heavy computations.
"""

import os
from typing import Any

import redis
from celery import Celery
from celery.schedules import crontab
from kombu import Queue

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
celery_app = Celery(
    "riskoptimizer",
    broker=REDIS_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "riskoptimizer.tasks.risk_tasks",
        "riskoptimizer.tasks.portfolio_tasks",
        "riskoptimizer.tasks.report_tasks",
        "riskoptimizer.tasks.maintenance_tasks",
    ],
)
celery_app.conf.update(
    task_routes={
        "riskoptimizer.tasks.risk_tasks.*": {"queue": "risk_calculations"},
        "riskoptimizer.tasks.portfolio_tasks.*": {"queue": "portfolio_operations"},
        "riskoptimizer.tasks.report_tasks.*": {"queue": "report_generation"},
        "riskoptimizer.tasks.maintenance_tasks.*": {"queue": "maintenance"},
    },
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("risk_calculations", routing_key="risk"),
        Queue("portfolio_operations", routing_key="portfolio"),
        Queue("report_generation", routing_key="reports"),
        Queue("maintenance", routing_key="maintenance"),
    ),
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    task_send_sent_event=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=1000,
    task_default_retry_delay=60,
    task_max_retries=3,
    beat_schedule={
        "cleanup-expired-tasks": {
            "task": "riskoptimizer.tasks.maintenance_tasks.cleanup_expired_tasks",
            "schedule": crontab(minute=0, hour=2),
        },
        "update-market-data": {
            "task": "riskoptimizer.tasks.maintenance_tasks.update_market_data",
            "schedule": crontab(minute=0, hour="*/6"),
        },
        "generate-daily-reports": {
            "task": "riskoptimizer.tasks.report_tasks.generate_daily_reports",
            "schedule": crontab(minute=0, hour=8),
        },
        "cache-warmup": {
            "task": "riskoptimizer.tasks.maintenance_tasks.cache_warmup",
            "schedule": crontab(minute=0, hour=6),
        },
    },
)
celery_app.conf.update(
    worker_send_task_events=True,
    task_send_sent_event=True,
    worker_hijack_root_logger=False,
    worker_log_color=False,
)
redis_client = redis.Redis.from_url(REDIS_URL)


def get_task_status(task_id: Any) -> Any:
    """Get the status of a task by ID."""
    return celery_app.AsyncResult(task_id)


def cancel_task(task_id: Any) -> Any:
    """Cancel a task by ID."""
    celery_app.control.revoke(task_id, terminate=True)


def get_active_tasks() -> Any:
    """Get list of active tasks."""
    inspect = celery_app.control.inspect()
    return inspect.active()


def get_scheduled_tasks() -> Any:
    """Get list of scheduled tasks."""
    inspect = celery_app.control.inspect()
    return inspect.scheduled()


def get_worker_stats() -> Any:
    """Get worker statistics."""
    inspect = celery_app.control.inspect()
    return inspect.stats()


class TaskResultManager:
    """Manages task results and provides utilities for task monitoring."""

    def __init__(self) -> None:
        self.redis_client = redis_client

    def store_task_progress(self, task_id: Any, progress_data: Any) -> Any:
        """Store task progress information."""
        key = f"task_progress:{task_id}"
        self.redis_client.hset(key, mapping=progress_data)
        self.redis_client.expire(key, 3600)

    def get_task_progress(self, task_id: Any) -> Any:
        """Get task progress information."""
        key = f"task_progress:{task_id}"
        return self.redis_client.hgetall(key)

    def store_task_metadata(self, task_id: Any, metadata: Any) -> Any:
        """Store task metadata."""
        key = f"task_metadata:{task_id}"
        self.redis_client.hset(key, mapping=metadata)
        self.redis_client.expire(key, 86400)

    def get_task_metadata(self, task_id: Any) -> Any:
        """Get task metadata."""
        key = f"task_metadata:{task_id}"
        return self.redis_client.hgetall(key)

    def cleanup_expired_task_data(self) -> Any:
        """Clean up expired task data."""
        # Implementation placeholder - scans for expired task keys


task_result_manager = TaskResultManager()


class TaskError(Exception):
    """Base exception for task errors."""


class TaskTimeoutError(TaskError):
    """Exception raised when a task times out."""


class TaskValidationError(TaskError):
    """Exception raised when task input validation fails."""


def task_with_progress(bind: Any = True, **kwargs) -> Any:
    """Decorator for tasks that report progress."""

    def decorator(func):

        @celery_app.task(bind=bind, **kwargs)
        def wrapper(self, *args, **kwargs):
            try:
                task_result_manager.store_task_metadata(
                    self.request.id,
                    {
                        "task_name": func.__name__,
                        "started_at": str(datetime.utcnow()),
                        "status": "STARTED",
                    },
                )
                result = func(self, *args, **kwargs)
                task_result_manager.store_task_metadata(
                    self.request.id,
                    {"completed_at": str(datetime.utcnow()), "status": "SUCCESS"},
                )
                return result
            except Exception as exc:
                task_result_manager.store_task_metadata(
                    self.request.id,
                    {
                        "failed_at": str(datetime.utcnow()),
                        "status": "FAILURE",
                        "error": str(exc),
                    },
                )
                raise

        return wrapper

    return decorator


from datetime import datetime

if __name__ == "__main__":
    celery_app.start()
