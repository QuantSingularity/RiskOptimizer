import logging
from datetime import datetime
from typing import Any, Dict, Optional

from riskoptimizer.core.exceptions import DatabaseError
from riskoptimizer.infrastructure.database.models import AuditLog
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AuditService:
    """
    Service for logging audit trails of financial transactions and key actions.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        """
        Initialize AuditService with an optional SQLAlchemy session.
        """
        self._session = session

    def _get_session(self, session: Optional[Session] = None) -> Session:
        """Get the SQLAlchemy session to use for database operations."""
        result_session = session or self._session
        if result_session is None:
            raise DatabaseError("No session available")
        return result_session

    def log_action(
        self,
        user_id: Optional[int],
        action_type: str,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        session: Optional[Session] = None,
    ) -> None:
        """
        Logs an action to the audit trail.

        Args:
            user_id (Optional[int]): The ID of the user performing the action. Can be None for system actions.
            action_type (str): A string describing the type of action (e.g., 'PORTFOLIO_CREATE', 'LOGIN_SUCCESS').
            entity_type (Optional[str]): The type of entity affected by the action (e.g., 'PORTFOLIO', 'USER').
            entity_id (Optional[int]): The ID of the entity affected by the action.
            details (Optional[Dict[str, Any]]): A dictionary containing additional details about the action.
            session (Optional[Session]): An optional SQLAlchemy session to use. If None, a new one is created.

        Raises:
            DatabaseError: If there's an issue logging the action to the database.
        """
        db = self._get_session(session)
        try:
            audit_log = AuditLog(
                user_id=user_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
                timestamp=datetime.utcnow(),
            )
            db.add(audit_log)
            db.flush()
            logger.info(
                f"Audit log recorded: Action={action_type}, User={user_id}, Entity={entity_type}:{entity_id}"
            )
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to log audit action: {action_type}. Error: {e}", exc_info=True
            )
            raise DatabaseError(f"Failed to log audit action: {e}")


audit_service = AuditService()
