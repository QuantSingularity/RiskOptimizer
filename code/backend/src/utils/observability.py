import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

from flask import g, has_request_context, request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

correlation_id: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)


class CorrelationIdFilter:
    """Filter to add correlation ID to log records."""

    def filter(self, record: object) -> object:
        """Add correlation ID to log record."""
        corr_id = correlation_id.get()
        if not corr_id and has_request_context():
            corr_id = getattr(g, "correlation_id", None)
        record.correlation_id = corr_id or "unknown"
        return True


class StructuredLogger:
    """Structured logger with correlation ID support."""

    def __init__(self, name: str) -> None:
        """
        Initialize structured logger.

        Args:
            name: Logger name
        """
        self.logger = logging.getLogger(name)
        correlation_filter = CorrelationIdFilter()
        self.logger.addFilter(correlation_filter)

    def _create_log_entry(self, level: str, message: str, **kwargs) -> Dict[str, Any]:
        """
        Create structured log entry.

        Args:
            level: Log level
            message: Log message
            **kwargs: Additional log data

        Returns:
            Structured log entry
        """
        entry = {
            "timestamp": time.time(),
            "level": level,
            "message": message,
            "correlation_id": correlation_id.get()
            or (getattr(g, "correlation_id", None) if has_request_context() else None),
            "service": "riskoptimizer",
        }
        if has_request_context():
            entry.update(
                {
                    "request": {
                        "method": request.method,
                        "path": request.path,
                        "remote_addr": request.remote_addr,
                        "user_agent": request.headers.get("User-Agent"),
                        "request_id": getattr(g, "request_id", None),
                    }
                }
            )
            if hasattr(g, "user") and g.user:
                entry["user"] = {
                    "id": g.user.get("id"),
                    "email": g.user.get("email"),
                    "role": g.user.get("role"),
                }
        if kwargs:
            entry["data"] = kwargs
        return entry

    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        entry = self._create_log_entry("DEBUG", message, **kwargs)
        self.logger.debug(json.dumps(entry))

    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        entry = self._create_log_entry("INFO", message, **kwargs)
        self.logger.info(json.dumps(entry))

    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        entry = self._create_log_entry("WARNING", message, **kwargs)
        self.logger.warning(json.dumps(entry))

    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        entry = self._create_log_entry("ERROR", message, **kwargs)
        self.logger.error(json.dumps(entry))

    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        entry = self._create_log_entry("CRITICAL", message, **kwargs)
        self.logger.critical(json.dumps(entry))


def generate_correlation_id() -> str:
    """
    Generate a new correlation ID.

    Returns:
        Correlation ID
    """
    return str(uuid.uuid4())


def set_correlation_id(corr_id: str) -> None:
    """
    Set correlation ID in context.

    Args:
        corr_id: Correlation ID
    """
    correlation_id.set(corr_id)
    if has_request_context():
        g.correlation_id = corr_id


def get_correlation_id() -> Optional[str]:
    """
    Get current correlation ID.

    Returns:
        Current correlation ID or None
    """
    corr_id = correlation_id.get()
    if not corr_id and has_request_context():
        corr_id = getattr(g, "correlation_id", None)
    return corr_id


def log_request_start(method: str, path: str, **kwargs) -> None:
    """
    Log request start.

    Args:
        method: HTTP method
        path: Request path
        **kwargs: Additional log data
    """
    structured_logger = StructuredLogger(__name__)
    structured_logger.info(
        f"Request started: {method} {path}",
        request_method=method,
        request_path=path,
        **kwargs,
    )


def log_request_end(
    method: str, path: str, status_code: int, response_time: float, **kwargs
) -> None:
    """
    Log request end.

    Args:
        method: HTTP method
        path: Request path
        status_code: HTTP status code
        response_time: Response time in seconds
        **kwargs: Additional log data
    """
    structured_logger = StructuredLogger(__name__)
    structured_logger.info(
        f"Request completed: {method} {path} - {status_code}",
        request_method=method,
        request_path=path,
        status_code=status_code,
        response_time=response_time,
        **kwargs,
    )


def log_error(error: Exception, context: Optional[str] = None, **kwargs) -> None:
    """
    Log error with context.

    Args:
        error: Exception instance
        context: Error context
        **kwargs: Additional log data
    """
    structured_logger = StructuredLogger(__name__)
    structured_logger.error(
        f"Error occurred: {str(error)}",
        error_type=type(error).__name__,
        error_message=str(error),
        context=context,
        **kwargs,
    )


def log_business_event(event_type: str, event_data: Dict[str, Any], **kwargs) -> None:
    """
    Log business event.

    Args:
        event_type: Type of business event
        event_data: Event data
        **kwargs: Additional log data
    """
    structured_logger = StructuredLogger(__name__)
    structured_logger.info(
        f"Business event: {event_type}",
        event_type=event_type,
        event_data=event_data,
        **kwargs,
    )


def log_security_event(
    event_type: str, severity: str, details: Dict[str, Any], **kwargs
) -> None:
    """
    Log security event.

    Args:
        event_type: Type of security event
        severity: Event severity (low, medium, high, critical)
        details: Event details
        **kwargs: Additional log data
    """
    structured_logger = StructuredLogger(__name__)
    if severity in ["critical", "high"]:
        log_func = structured_logger.critical
    elif severity == "medium":
        log_func = structured_logger.warning
    else:
        log_func = structured_logger.info
    log_func(
        f"Security event: {event_type}",
        event_type=event_type,
        severity=severity,
        security_event=True,
        details=details,
        **kwargs,
    )


def apply_correlation_middleware(app: object) -> None:
    """
    Apply correlation ID middleware to Flask app.

    Args:
        app: Flask application instance
    """

    @app.before_request
    def before_request() -> None:
        """Generate correlation ID for each request."""
        corr_id = request.headers.get("X-Correlation-ID")
        if not corr_id:
            corr_id = generate_correlation_id()
        set_correlation_id(corr_id)
        g.request_id = str(uuid.uuid4())
        g.start_time = time.time()
        log_request_start(
            request.method,
            request.path,
            request_id=g.request_id,
            correlation_id=corr_id,
        )

    @app.after_request
    def after_request(response):
        """Add correlation ID to response headers and log request completion."""
        corr_id = get_correlation_id()
        if corr_id:
            response.headers["X-Correlation-ID"] = corr_id
        if hasattr(g, "request_id"):
            response.headers["X-Request-ID"] = g.request_id
        response_time = time.time() - getattr(g, "start_time", time.time())
        log_request_end(
            request.method,
            request.path,
            response.status_code,
            response_time,
            request_id=getattr(g, "request_id", None),
            correlation_id=corr_id,
        )
        return response
