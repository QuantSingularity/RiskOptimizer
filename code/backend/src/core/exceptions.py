"""
Custom exception classes for the RiskOptimizer application.
Provides structured error handling with specific exception types.
"""

from typing import Any, Dict, Optional


class RiskOptimizerException(Exception):
    """Base exception class for all RiskOptimizer-specific exceptions."""

    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.error_code = error_code or self.__class__.__name__.upper()
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format for API responses."""
        return {
            "code": self.error_code,
            "message": self.message,
            "details": self.details,
        }


class ValidationError(RiskOptimizerException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str = "Validation failed",
        field: Optional[str] = None,
        value: int = None,
    ) -> None:
        details = {}
        if field:
            details["field"] = field
        if value is not None:
            details["value"] = value
        super().__init__(message, "VALIDATION_ERROR", details)


class AuthenticationError(RiskOptimizerException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, "AUTHENTICATION_ERROR")


class AuthorizationError(RiskOptimizerException):
    """Raised when authorization fails."""

    def __init__(
        self, message: str = "Access denied", required_permission: Optional[str] = None
    ) -> None:
        details = {}
        if required_permission:
            details["required_permission"] = required_permission
        super().__init__(message, "AUTHORIZATION_ERROR", details)


class NotFoundError(RiskOptimizerException):
    """Raised when a requested resource is not found."""

    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(message, "NOT_FOUND", details)


class ConflictError(RiskOptimizerException):
    """Raised when a resource conflict occurs."""

    def __init__(
        self, message: str = "Resource conflict", resource_type: Optional[str] = None
    ) -> None:
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        super().__init__(message, "CONFLICT", details)


class DatabaseError(RiskOptimizerException):
    """Raised when database operations fail."""

    def __init__(
        self,
        message: str = "Database operation failed",
        operation: Optional[str] = None,
    ) -> None:
        details = {}
        if operation:
            details["operation"] = operation
        super().__init__(message, "DATABASE_ERROR", details)


class ExternalServiceError(RiskOptimizerException):
    """Raised when external service calls fail."""

    def __init__(
        self,
        message: str = "External service error",
        service: Optional[str] = None,
        status_code: Optional[int] = None,
    ) -> None:
        details = {}
        if service:
            details["service"] = service
        if status_code is not None:
            details["status_code"] = str(status_code)
        super().__init__(message, "EXTERNAL_SERVICE_ERROR", details)


class RateLimitError(RiskOptimizerException):
    """Raised when rate limit is exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        window: Optional[int] = None,
        reset_time: Optional[int] = None,
    ) -> None:
        details: Dict[str, Any] = {}
        if limit:
            details["limit"] = limit
        if window:
            details["window"] = window
        if reset_time is not None:
            details["reset_time"] = reset_time
        super().__init__(message, "RATE_LIMIT_ERROR", details)


class SecurityError(RiskOptimizerException):
    """Raised when security validations fail."""

    def __init__(self, message: str = "Security error") -> None:
        super().__init__(message, "SECURITY_ERROR")


class ModelError(RiskOptimizerException):
    """Raised when AI model operations fail."""

    def __init__(
        self, message: str = "Model operation failed", model_type: Optional[str] = None
    ) -> None:
        details = {}
        if model_type:
            details["model_type"] = model_type
        super().__init__(message, "MODEL_ERROR", details)


class CalculationError(RiskOptimizerException):
    """Raised when risk calculations fail."""

    def __init__(
        self,
        message: str = "Calculation failed",
        calculation_type: Optional[str] = None,
    ) -> None:
        details = {}
        if calculation_type:
            details["calculation_type"] = calculation_type
        super().__init__(message, "CALCULATION_ERROR", details)


class BlockchainError(RiskOptimizerException):
    """Raised when blockchain operations fail."""

    def __init__(
        self,
        message: str = "Blockchain operation failed",
        transaction_hash: Optional[str] = None,
    ) -> None:
        details = {}
        if transaction_hash:
            details["transaction_hash"] = transaction_hash
        super().__init__(message, "BLOCKCHAIN_ERROR", details)


class CacheError(RiskOptimizerException):
    """Raised when cache operations fail."""

    def __init__(
        self, message: str = "Cache operation failed", operation: Optional[str] = None
    ) -> None:
        details = {}
        if operation:
            details["operation"] = operation
        super().__init__(message, "CACHE_ERROR", details)


class TaskError(RiskOptimizerException):
    """Raised when background task operations fail."""

    def __init__(
        self,
        message: str = "Task operation failed",
        task_id: Optional[str] = None,
        task_type: Optional[str] = None,
    ) -> None:
        details = {}
        if task_id:
            details["task_id"] = task_id
        if task_type:
            details["task_type"] = task_type
        super().__init__(message, "TASK_ERROR", details)
