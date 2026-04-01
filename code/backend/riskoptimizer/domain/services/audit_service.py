import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from riskoptimizer.infrastructure.database.models import AuditLog
from riskoptimizer.infrastructure.database.session import get_db_session
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
            user_id (Optional[int]): The ID of the user performing the action.
            action_type (str): A string describing the type of action.
            entity_type (Optional[str]): The type of entity affected by the action.
            entity_id (Optional[int]): The ID of the entity affected by the action.
            details (Optional[Dict[str, Any]]): Additional details about the action.
            session (Optional[Session]): An optional SQLAlchemy session to use.
        """
        details_str = json.dumps(details, default=str) if details else None
        resource_id = str(entity_id) if entity_id is not None else None

        def _do_log(db: Session) -> None:
            audit_log = AuditLog(
                user_id=user_id,
                action=action_type,
                resource_type=entity_type,
                resource_id=resource_id,
                details=details_str,
                status="success",
                created_at=datetime.utcnow(),
            )
            db.add(audit_log)
            db.flush()
            logger.info(
                f"Audit log recorded: Action={action_type}, User={user_id}, "
                f"Entity={entity_type}:{entity_id}"
            )

        try:
            if session is not None:
                _do_log(session)
            else:
                with get_db_session() as db:
                    _do_log(db)
        except SQLAlchemyError as e:
            logger.error(
                f"Failed to log audit action: {action_type}. Error: {e}", exc_info=True
            )


audit_service = AuditService()
