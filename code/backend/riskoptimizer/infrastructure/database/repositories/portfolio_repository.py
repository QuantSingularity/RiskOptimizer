import logging
from decimal import Decimal
from typing import Any, Dict, List, Optional

from riskoptimizer.core.exceptions import DatabaseError, NotFoundError
from riskoptimizer.domain.services.audit_service import audit_service
from riskoptimizer.infrastructure.database.models import Allocation, Portfolio, User
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class PortfolioRepository:
    """Repository for portfolio-related database operations."""

    def __init__(self, session: Optional[Session] = None) -> None:
        """
        Initialize repository with optional session.

        Args:
            session: SQLAlchemy session (optional)
        """
        self._session = session
        self.audit_service = audit_service

    def _get_session(self, session: Optional[Session] = None) -> Session:
        """
        Get session for database operations.

        Args:
            session: SQLAlchemy session (optional)

        Returns:
            SQLAlchemy session
        """
        return session or self._session

    def get_by_address(
        self, user_address: str, session: Optional[Session] = None
    ) -> Optional[Portfolio]:
        """
        Get portfolio by user address.

        Args:
            user_address: User wallet address
            session: SQLAlchemy session (optional)

        Returns:
            Portfolio or None if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolio = (
                db.query(Portfolio)
                .filter(Portfolio.user_address == user_address)
                .first()
            )
            return portfolio
        except SQLAlchemyError as e:
            logger.error(f"Error getting portfolio by address: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={
                    "action": "get_by_address",
                    "user_address": user_address,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to get portfolio: {str(e)}")

    def get_by_id(
        self, portfolio_id: int, session: Optional[Session] = None
    ) -> Optional[Portfolio]:
        """
        Get portfolio by ID.

        Args:
            portfolio_id: Portfolio ID
            session: SQLAlchemy session (optional)

        Returns:
            Portfolio or None if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            return portfolio
        except SQLAlchemyError as e:
            logger.error(f"Error getting portfolio by ID: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={
                    "action": "get_by_id",
                    "portfolio_id": portfolio_id,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to get portfolio: {str(e)}")

    def get_by_user_id(
        self, user_id: int, session: Optional[Session] = None
    ) -> List[Portfolio]:
        """
        Get all portfolios for a user.

        Args:
            user_id: User ID
            session: SQLAlchemy session (optional)

        Returns:
            List of portfolios

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolios = db.query(Portfolio).filter(Portfolio.user_id == user_id).all()
            return portfolios
        except SQLAlchemyError as e:
            logger.error(
                f"Error getting portfolios by user ID: {str(e)}", exc_info=True
            )
            self.audit_service.log_action(
                user_id=user_id,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={"action": "get_by_user_id", "error": str(e)},
            )
            raise DatabaseError(f"Failed to get portfolios: {str(e)}")

    def create(
        self,
        user_id: int,
        user_address: str,
        name: str = "Default Portfolio",
        description: Optional[str] = None,
        session: Optional[Session] = None,
    ) -> Portfolio:
        """
        Create a new portfolio.

        Args:
            user_id: User ID
            user_address: User wallet address
            name: Portfolio name
            description: Portfolio description
            session: SQLAlchemy session (optional)

        Returns:
            Created portfolio

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolio = Portfolio(
                user_id=user_id,
                user_address=user_address,
                name=name,
                description=description,
            )
            db.add(portfolio)
            db.flush()
            logger.info(f"Created portfolio {portfolio.id} for user {user_id}")
            self.audit_service.log_action(
                user_id=user_id,
                action_type="PORTFOLIO_CREATED",
                entity_type="PORTFOLIO",
                entity_id=portfolio.id,
                details={"name": name, "user_address": user_address},
            )
            return portfolio
        except SQLAlchemyError as e:
            logger.error(f"Error creating portfolio: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=user_id,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={
                    "action": "create",
                    "name": name,
                    "user_address": user_address,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to create portfolio: {str(e)}")

    def update(
        self, portfolio_id: int, data: Dict[str, Any], session: Optional[Session] = None
    ) -> Portfolio:
        """
        Update portfolio.

        Args:
            portfolio_id: Portfolio ID
            data: Dictionary with fields to update
            session: SQLAlchemy session (optional)

        Returns:
            Updated portfolio

        Raises:
            NotFoundError: If portfolio not found
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise NotFoundError(
                    f"Portfolio {portfolio_id} not found",
                    "portfolio",
                    str(portfolio_id),
                )
            old_data = {
                key: getattr(portfolio, key)
                for key in data.keys()
                if hasattr(portfolio, key)
            }
            for key, value in data.items():
                if hasattr(portfolio, key):
                    setattr(portfolio, key, value)
            db.flush()
            logger.info(f"Updated portfolio {portfolio_id}")
            self.audit_service.log_action(
                user_id=portfolio.user_id,
                action_type="PORTFOLIO_UPDATED",
                entity_type="PORTFOLIO",
                entity_id=portfolio.id,
                details={"old_data": old_data, "new_data": data},
            )
            return portfolio
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error updating portfolio: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={
                    "action": "update",
                    "portfolio_id": portfolio_id,
                    "data": data,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to update portfolio: {str(e)}")

    def delete(self, portfolio_id: int, session: Optional[Session] = None) -> bool:
        """
        Delete portfolio.

        Args:
            portfolio_id: Portfolio ID
            session: SQLAlchemy session (optional)

        Returns:
            True if deleted, False if not found

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                return False
            audit_details = {
                "portfolio_id": portfolio.id,
                "name": portfolio.name,
                "user_address": portfolio.user_address,
            }
            db.delete(portfolio)
            db.flush()
            logger.info(f"Deleted portfolio {portfolio_id}")
            self.audit_service.log_action(
                user_id=portfolio.user_id,
                action_type="PORTFOLIO_DELETED",
                entity_type="PORTFOLIO",
                entity_id=portfolio.id,
                details=audit_details,
            )
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting portfolio: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={
                    "action": "delete",
                    "portfolio_id": portfolio_id,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to delete portfolio: {str(e)}")

    def save_allocations(
        self,
        portfolio_id: int,
        allocations: Dict[str, Decimal],
        session: Optional[Session] = None,
    ) -> List[Allocation]:
        """
        Save allocations for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            allocations: Dictionary mapping asset symbols to percentages (Decimal)
            session: SQLAlchemy session (optional)

        Returns:
            List of created allocations

        Raises:
            NotFoundError: If portfolio not found
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
            if not portfolio:
                raise NotFoundError(
                    f"Portfolio {portfolio_id} not found",
                    "portfolio",
                    str(portfolio_id),
                )
            db.query(Allocation).filter(
                Allocation.portfolio_id == portfolio_id
            ).delete()
            allocation_objects = []
            for asset, percentage in allocations.items():
                allocation = Allocation(
                    portfolio_id=portfolio_id, asset_symbol=asset, percentage=percentage
                )
                db.add(allocation)
                allocation_objects.append(allocation)
            db.flush()
            logger.info(
                f"Saved {len(allocation_objects)} allocations for portfolio {portfolio_id}"
            )
            self.audit_service.log_action(
                user_id=portfolio.user_id,
                action_type="ALLOCATIONS_SAVED",
                entity_type="PORTFOLIO",
                entity_id=portfolio.id,
                details={"allocations": {k: str(v) for k, v in allocations.items()}},
            )
            return allocation_objects
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(f"Error saving allocations: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="ALLOCATION",
                details={
                    "action": "save_allocations",
                    "portfolio_id": portfolio_id,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to save allocations: {str(e)}")

    def get_allocations(
        self, portfolio_id: int, session: Optional[Session] = None
    ) -> List[Allocation]:
        """
        Get allocations for a portfolio.

        Args:
            portfolio_id: Portfolio ID
            session: SQLAlchemy session (optional)

        Returns:
            List of allocations

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            allocations = (
                db.query(Allocation)
                .filter(Allocation.portfolio_id == portfolio_id)
                .all()
            )
            return allocations
        except SQLAlchemyError as e:
            logger.error(f"Error getting allocations: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="ALLOCATION",
                details={
                    "action": "get_allocations",
                    "portfolio_id": portfolio_id,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to get allocations: {str(e)}")

    def get_portfolio_with_allocations(
        self, user_address: str, session: Optional[Session] = None
    ) -> Dict[str, Any]:
        """
        Get portfolio with allocations for a user.

        Args:
            user_address: User wallet address
            session: SQLAlchemy session (optional)

        Returns:
            Dictionary with portfolio and allocations

        Raises:
            NotFoundError: If portfolio not found
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            portfolio = (
                db.query(Portfolio)
                .filter(Portfolio.user_address == user_address)
                .first()
            )
            if not portfolio:
                raise NotFoundError(
                    f"Portfolio for address {user_address} not found",
                    "portfolio",
                    user_address,
                )
            allocations = (
                db.query(Allocation)
                .filter(Allocation.portfolio_id == portfolio.id)
                .all()
            )
            assets = []
            allocation_percentages = []
            for allocation in allocations:
                assets.append(allocation.asset_symbol)
                allocation_percentages.append(float(allocation.percentage))
            return {
                "user_address": user_address,
                "portfolio_id": portfolio.id,
                "name": portfolio.name,
                "assets": assets,
                "allocations": allocation_percentages,
                "total_value": (
                    float(portfolio.total_value)
                    if portfolio.total_value is not None
                    else None
                ),
            }
        except NotFoundError:
            raise
        except SQLAlchemyError as e:
            logger.error(
                f"Error getting portfolio with allocations: {str(e)}", exc_info=True
            )
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={
                    "action": "get_portfolio_with_allocations",
                    "user_address": user_address,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to get portfolio with allocations: {str(e)}")

    def save_portfolio_with_allocations(
        self,
        user_address: str,
        allocations: Dict[str, Decimal],
        name: str = "Default Portfolio",
        session: Optional[Session] = None,
    ) -> Dict[str, Any]:
        """
        Save portfolio with allocations for a user.

        Args:
            user_address: User wallet address
            allocations: Dictionary mapping asset symbols to percentages (Decimal)
            name: Portfolio name
            session: SQLAlchemy session (optional)

        Returns:
            Dictionary with portfolio and allocations

        Raises:
            DatabaseError: If database operation fails
        """
        try:
            db = self._get_session(session)
            user = db.query(User).filter(User.wallet_address == user_address).first()
            user_id = user.id if user else None
            portfolio = (
                db.query(Portfolio)
                .filter(Portfolio.user_address == user_address)
                .first()
            )
            if portfolio:
                portfolio.name = name
                if user_id and (not portfolio.user_id):
                    portfolio.user_id = user_id
            else:
                portfolio = Portfolio(
                    user_id=user_id, user_address=user_address, name=name
                )
                db.add(portfolio)
                db.flush()
            self.save_allocations(portfolio.id, allocations, db)
            result = self.get_portfolio_with_allocations(user_address, db)
            logger.info(
                f"Saved portfolio with {len(allocations)} allocations for user {user_address}"
            )
            self.audit_service.log_action(
                user_id=user_id,
                action_type="PORTFOLIO_ALLOCATIONS_SAVED",
                entity_type="PORTFOLIO",
                entity_id=portfolio.id,
                details={
                    "user_address": user_address,
                    "name": name,
                    "num_allocations": len(allocations),
                },
            )
            return result
        except SQLAlchemyError as e:
            logger.error(
                f"Error saving portfolio with allocations: {str(e)}", exc_info=True
            )
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="PORTFOLIO",
                details={
                    "action": "save_portfolio_with_allocations",
                    "user_address": user_address,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to save portfolio with allocations: {str(e)}")


portfolio_repository = PortfolioRepository()
