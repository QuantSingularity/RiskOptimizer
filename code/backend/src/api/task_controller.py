import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple

from flask import Blueprint, jsonify, request
from src.api.middleware.auth_middleware import admin_required, jwt_required
from src.core.exceptions import RiskOptimizerException, ValidationError
from src.tasks import maintenance_tasks, portfolio_tasks, report_tasks, risk_tasks
from src.tasks.celery_app import (
    cancel_task,
    celery_app,
    get_active_tasks,
    get_scheduled_tasks,
    get_task_status,
    get_worker_stats,
    task_result_manager,
)

logger = logging.getLogger(__name__)

tasks_bp = Blueprint("tasks", __name__, url_prefix="/api/v1/tasks")

REQUIRED = object()
MAX_SIMULATIONS = 100000
QUEUE_DEGRADED_THRESHOLD = 1000

SUBMISSIONS: List[Tuple[str, str, Callable, List[Tuple[str, str, Any]]]] = [
    (
        "/risk/monte-carlo",
        "monte_carlo_simulation",
        risk_tasks.monte_carlo_simulation,
        [
            ("portfolio_data", "dict", REQUIRED),
            ("num_simulations", "count", 10000),
            ("time_horizon", "horizon", 252),
        ],
    ),
    (
        "/risk/var-cvar",
        "var_cvar_calculation",
        risk_tasks.calculate_var_cvar,
        [
            ("portfolio_data", "dict", REQUIRED),
            ("confidence_levels", "levels", [0.95, 0.99]),
        ],
    ),
    (
        "/risk/efficient-frontier",
        "efficient_frontier_calculation",
        risk_tasks.efficient_frontier_calculation,
        [("assets_data", "dict", REQUIRED), ("num_portfolios", "count", 10000)],
    ),
    (
        "/risk/stress-test",
        "stress_test",
        risk_tasks.stress_test_portfolio,
        [
            ("portfolio_data", "dict", REQUIRED),
            ("stress_scenarios", "dict_list", REQUIRED),
        ],
    ),
    (
        "/portfolio/optimize",
        "portfolio_optimization",
        portfolio_tasks.optimize_portfolio,
        [("assets_data", "dict", REQUIRED), ("optimization_params", "dict", REQUIRED)],
    ),
    (
        "/portfolio/rebalance",
        "portfolio_rebalancing",
        portfolio_tasks.rebalance_portfolio,
        [
            ("current_portfolio", "dict", REQUIRED),
            ("target_weights", "dict", REQUIRED),
            ("rebalancing_params", "dict", REQUIRED),
        ],
    ),
    (
        "/portfolio/performance-analysis",
        "performance_analysis",
        portfolio_tasks.analyze_portfolio_performance,
        [
            ("portfolio_data", "dict", REQUIRED),
            ("benchmark_data", "dict", REQUIRED),
            ("analysis_period", "dict", REQUIRED),
        ],
    ),
    (
        "/reports/portfolio",
        "portfolio_report",
        report_tasks.generate_portfolio_report,
        [("portfolio_data", "dict", REQUIRED), ("report_config", "dict", REQUIRED)],
    ),
    (
        "/reports/risk",
        "risk_report",
        report_tasks.generate_risk_report,
        [("risk_analysis_data", "dict", REQUIRED), ("report_config", "dict", REQUIRED)],
    ),
    (
        "/export/portfolio",
        "portfolio_export",
        report_tasks.export_portfolio_data,
        [("portfolio_data", "dict", REQUIRED), ("export_config", "dict", REQUIRED)],
    ),
]

MAINTENANCE: List[Tuple[str, str, Callable]] = [
    (
        "/maintenance/cleanup",
        "cleanup_expired_tasks",
        maintenance_tasks.cleanup_expired_tasks,
    ),
    (
        "/maintenance/health-check",
        "system_health_check",
        maintenance_tasks.system_health_check,
    ),
    ("/maintenance/cache-warmup", "cache_warmup", maintenance_tasks.cache_warmup),
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def respond(data: Dict[str, Any], status: int = 200) -> Any:
    return jsonify({"status": "success", "data": data}), status


def error_response(message: str, code: str, status: int) -> Any:
    return (
        jsonify(
            {
                "status": "error",
                "error": {"code": code, "message": message, "details": {}},
            }
        ),
        status,
    )


def guarded(operation: str) -> Callable:
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except ValidationError as error:
                return (
                    jsonify({"status": "error", "error": error.to_dict()}),
                    400,
                )
            except RiskOptimizerException as error:
                logger.error("%s failed: %s", operation, error, exc_info=True)
                return error_response(error.message, error.error_code, 500)
            except Exception as error:
                logger.error("%s failed: %s", operation, error, exc_info=True)
                return error_response(f"{operation} failed", "TASK_ERROR", 500)

        return wrapper

    return decorator


def coerce(name: str, kind: str, value: Any) -> Any:
    if kind == "dict":
        if not isinstance(value, dict) or not value:
            raise ValidationError(f"{name} must be a non-empty object", name)
        return value
    if kind == "dict_list":
        if (
            not isinstance(value, list)
            or not value
            or not all(isinstance(item, dict) for item in value)
        ):
            raise ValidationError(f"{name} must be a non-empty list of objects", name)
        return value
    if kind in ("count", "horizon"):
        limit = MAX_SIMULATIONS if kind == "count" else 2520
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or not 1 <= value <= limit
        ):
            raise ValidationError(
                f"{name} must be an integer between 1 and {limit}", name
            )
        return value
    if kind == "levels":
        if (
            not isinstance(value, list)
            or not value
            or not all(
                isinstance(level, (int, float))
                and not isinstance(level, bool)
                and 0 < level < 1
                for level in value
            )
        ):
            raise ValidationError(
                f"{name} must be a list of numbers between 0 and 1", name
            )
        return [float(level) for level in value]
    raise ValidationError(f"Unsupported field type for {name}", name)


def parse_arguments(spec: List[Tuple[str, str, Any]]) -> List[Any]:
    body = request.get_json(silent=True)
    if not isinstance(body, dict):
        raise ValidationError("A JSON object request body is required")
    arguments = []
    for name, kind, default in spec:
        value = body.get(name)
        if value is None:
            if default is REQUIRED:
                raise ValidationError(f"{name} is required", name)
            value = default
        arguments.append(coerce(name, kind, value))
    return arguments


def submission_payload(task: Any, task_type: str) -> Dict[str, Any]:
    return {
        "task_id": task.id,
        "task_type": task_type,
        "status": "PENDING",
        "submitted_at": now(),
    }


def register_submission(
    path: str, task_type: str, task_function: Callable, spec: List[Tuple[str, str, Any]]
) -> None:
    @jwt_required()
    @guarded(task_type)
    def view() -> Any:
        task = task_function.delay(*parse_arguments(spec))
        return respond(submission_payload(task, task_type), 202)

    tasks_bp.add_url_rule(path, f"submit_{task_type}", view, methods=["POST"])


def register_maintenance(path: str, task_type: str, task_function: Callable) -> None:
    @admin_required
    @guarded(task_type)
    def view() -> Any:
        return respond(submission_payload(task_function.delay(), task_type), 202)

    tasks_bp.add_url_rule(path, f"maintenance_{task_type}", view, methods=["POST"])


for _path, _type, _function, _spec in SUBMISSIONS:
    register_submission(_path, _type, _function, _spec)

for _path, _type, _function in MAINTENANCE:
    register_maintenance(_path, _type, _function)


@tasks_bp.route("/<task_id>/status", methods=["GET"])
@jwt_required()
@guarded("Task status")
def task_status(task_id: str) -> Any:
    result = get_task_status(task_id)
    data = {
        "task_id": task_id,
        "status": result.status,
        "result": result.result if result.successful() else None,
        "progress": task_result_manager.get_task_progress(task_id),
        "metadata": task_result_manager.get_task_metadata(task_id),
    }
    if result.failed():
        data["error"] = str(result.info)
    return respond(data)


@tasks_bp.route("/<task_id>/result", methods=["GET"])
@jwt_required()
@guarded("Task result")
def task_result(task_id: str) -> Any:
    result = get_task_status(task_id)
    if not result.ready():
        return error_response("Task not yet completed", "TASK_PENDING", 202)
    if result.failed():
        return error_response(f"Task failed: {result.info}", "TASK_FAILED", 500)
    completed = result.date_done
    return respond(
        {
            "task_id": task_id,
            "result": result.result,
            "completed_at": completed.isoformat() if completed else None,
        }
    )


@tasks_bp.route("/<task_id>", methods=["DELETE"])
@jwt_required()
@guarded("Task cancellation")
def cancel(task_id: str) -> Any:
    cancel_task(task_id)
    return respond(
        {
            "task_id": task_id,
            "message": "Task cancellation requested",
            "cancelled_at": now(),
        }
    )


@tasks_bp.route("/active", methods=["GET"])
@admin_required
@guarded("Active task listing")
def active_tasks() -> Any:
    return respond({"active_tasks": get_active_tasks(), "retrieved_at": now()})


@tasks_bp.route("/scheduled", methods=["GET"])
@admin_required
@guarded("Scheduled task listing")
def scheduled_tasks() -> Any:
    return respond({"scheduled_tasks": get_scheduled_tasks(), "retrieved_at": now()})


@tasks_bp.route("/workers/stats", methods=["GET"])
@admin_required
@guarded("Worker statistics")
def worker_stats() -> Any:
    return respond({"worker_stats": get_worker_stats(), "retrieved_at": now()})


@tasks_bp.route("/queue/stats", methods=["GET"])
@admin_required
@guarded("Queue statistics")
def queue_stats() -> Any:
    inspector = celery_app.control.inspect()
    reserved = inspector.reserved()
    active = inspector.active()
    queued = sum(len(items) for items in (reserved or {}).values())
    running = sum(len(items) for items in (active or {}).values())
    return respond(
        {
            "queue_stats": {
                "total_queued_tasks": queued,
                "total_active_tasks": running,
                "reserved_tasks_by_worker": reserved,
                "active_tasks_by_worker": active,
                "queue_health": (
                    "healthy" if queued < QUEUE_DEGRADED_THRESHOLD else "degraded"
                ),
            },
            "retrieved_at": now(),
        }
    )
