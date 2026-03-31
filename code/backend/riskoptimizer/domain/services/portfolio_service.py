import logging
from decimal import Decimal, getcontext
from typing import Any, Dict, List, Optional

from riskoptimizer.core.exceptions import NotFoundError, ValidationError
from riskoptimizer.domain.services.audit_service import audit_service
from riskoptimizer.infrastructure.cache.redis_cache import redis_cache
from riskoptimizer.infrastructure.database.repositories.portfolio_repository import (
    portfolio_repository,
)
from riskoptimizer.infrastructure.database.repositories.user_repository import (
    user_repository,
)
from riskoptimizer.infrastructure.database.session import get_db_session
from riskoptimizer.utils.cache_utils import cache_invalidate, cache_result

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

getcontext().prec = 28


class PortfolioService:
    """
    Service for managing user portfolios and their allocations.

    This service handles operations such as retrieving, saving, creating, updating,
    and deleting portfolios. It integrates with the database repository for data
    persistence, Redis for caching, and the audit service for logging financial actions.
    """

    def __init__(self) -> None:
        """
        Initializes the PortfolioService with necessary repositories and services.
        """
        self.portfolio_repo = portfolio_repository
        self.user_repo = user_repository
        self.cache = redis_cache
        self.audit_service = audit_service

    @cache_result("portfolio", ttl=300)
    def get_portfolio_by_address(self, user_address: str) -> Dict[str, Any]:
        """
        Retrieves a user's portfolio and its allocations by their wallet address.

        Args:
            user_address: The blockchain wallet address of the user.

        Returns:
            A dictionary containing the portfolio data, including total value and allocations.

        Raises:
            ValidationError: If the user address is invalid.
            NotFoundError: If no portfolio is found for the given address.
        """
        if not user_address or not isinstance(user_address, str):
            raise ValidationError(
                "User address is required", "user_address", user_address
            )
        cache_key = f"portfolio:{user_address}"
        cached_data = self.cache.get(cache_key)
        if cached_data:
            logger.debug(f"Portfolio cache hit for address {user_address}")
            if "total_value" in cached_data:
                cached_data["total_value"] = Decimal(cached_data["total_value"])
            if "allocations" in cached_data:
                for alloc in cached_data["allocations"]:
                    alloc["percentage"] = Decimal(alloc["percentage"])
                    if alloc["amount"] is not None:
                        alloc["amount"] = Decimal(alloc["amount"])
                    if alloc["current_price"] is not None:
                        alloc["current_price"] = Decimal(alloc["current_price"])
            return cached_data
        with get_db_session() as session:
            try:
                portfolio_data = self.portfolio_repo.get_portfolio_with_allocations(
                    user_address, session
                )
                serializable_portfolio_data = portfolio_data.copy()
                if "total_value" in serializable_portfolio_data:
                    serializable_portfolio_data["total_value"] = str(
                        serializable_portfolio_data["total_value"]
                    )
                if "allocations" in serializable_portfolio_data:
                    serializable_portfolio_data["allocations"] = [
                        {
                            k: str(v) if isinstance(v, Decimal) else v
                            for k, v in alloc.items()
                        }
                        for alloc in serializable_portfolio_data["allocations"]
                    ]
                self.cache.set(cache_key, serializable_portfolio_data, ttl=300)
                logger.info(f"Retrieved portfolio for address {user_address}")
                return portfolio_data
            except NotFoundError:
                logger.warning(f"Portfolio not found for address {user_address}")
                raise

    @cache_invalidate("portfolio")
    def save_portfolio(
        self,
        user_address: str,
        allocations: Dict[str, float],
        name: str = "Default Portfolio",
    ) -> Dict[str, Any]:
        """
        Saves or updates a user's portfolio allocations.

        If a portfolio for the user address exists, it updates its allocations.
        Otherwise, it creates a new portfolio.

        Args:
            user_address: The blockchain wallet address of the user.
            allocations: A dictionary mapping asset symbols (e.g., "BTC") to their
                         percentage allocations (e.g., 60.0 for 60%).
            name: An optional name for the portfolio. Defaults to "Default Portfolio".

        Returns:
            A dictionary containing the saved or updated portfolio data.

        Raises:
            ValidationError: If input data (user_address, allocations, name) is invalid.
        """
        self._validate_portfolio_input(user_address, allocations, name)
        normalized_allocations = self._normalize_allocations(allocations)
        decimal_allocations = {
            k: Decimal(str(v)) for k, v in normalized_allocations.items()
        }
        with get_db_session() as session:
            portfolio_data = self.portfolio_repo.save_portfolio_with_allocations(
                user_address, decimal_allocations, name, session
            )
            user = self.user_repo.get_by_wallet_address(user_address, session)
            user_id = user.id if user else None
            self.audit_service.log_action(
                user_id=user_id,
                action_type="PORTFOLIO_SAVED",
                entity_type="PORTFOLIO",
                entity_id=portfolio_data.get("portfolio_id"),
                details={
                    "user_address": user_address,
                    "name": name,
                    "allocations": {k: str(v) for k, v in decimal_allocations.items()},
                },
            )
            logger.info(
                f"Saved portfolio for address {user_address} with {len(decimal_allocations)} assets"
            )
            return portfolio_data

    def create_portfolio(
        self,
        user_id: int,
        user_address: str,
        name: str = "Default Portfolio",
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Creates a new portfolio for a specified user.

        Args:
            user_id: The ID of the user for whom the portfolio is being created.
            user_address: The blockchain wallet address to associate with the new portfolio.
            name: The name of the new portfolio. Defaults to "Default Portfolio".
            description: An optional description for the portfolio.

        Returns:
            A dictionary containing the newly created portfolio's data.

        Raises:
            ValidationError: If input data (user_id, user_address, name) is invalid.
            NotFoundError: If the specified user does not exist.
        """
        if not user_id or not isinstance(user_id, int):
            raise ValidationError(
                "User ID is required and must be an integer.", "user_id", user_id
            )
        if not user_address or not isinstance(user_address, str):
            raise ValidationError(
                "User address is required and must be a string.",
                "user_address",
                user_address,
            )
        if not name or not isinstance(name, str):
            raise ValidationError(
                "Portfolio name is required and must be a string.", "name", name
            )
        with get_db_session() as session:
            user = self.user_repo.get_by_id(user_id, session)
            if not user:
                raise NotFoundError(f"User {user_id} not found", "user", str(user_id))
            portfolio = self.portfolio_repo.create(
                user_id, user_address, name, description, session
            )
            portfolio_data = {
                "id": portfolio.id,
                "user_id": portfolio.user_id,
                "user_address": portfolio.user_address,
                "name": portfolio.name,
                "description": portfolio.description,
                "total_value": (
                    str(portfolio.total_value)
                    if isinstance(portfolio.total_value, Decimal)
                    else portfolio.total_value
                ),
                "created_at": portfolio.created_at.isoformat(),
                "updated_at": portfolio.updated_at.isoformat(),
            }
            self.audit_service.log_action(
                user_id=user_id,
                action_type="PORTFOLIO_CREATED",
                entity_type="PORTFOLIO",
                entity_id=portfolio.id,
                details={
                    "name": name,
                    "user_address": user_address,
                    "description": description,
                },
            )
            logger.info(f"Created portfolio {portfolio.id} for user {user_id}")
            return portfolio_data

    def update_portfolio(
        self, portfolio_id: int, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Updates an existing portfolio's details.

        Args:
            portfolio_id: The ID of the portfolio to update.
            data: A dictionary containing the fields to update (e.g., "name", "description", "total_value").

        Returns:
            A dictionary containing the updated portfolio data.

        Raises:
            ValidationError: If input data (portfolio_id or update data) is invalid.
            NotFoundError: If the portfolio with the given ID is not found.
        """
        if not portfolio_id or not isinstance(portfolio_id, int):
            raise ValidationError(
                "Portfolio ID is required and must be an integer.",
                "portfolio_id",
                portfolio_id,
            )
        if not data or not isinstance(data, dict) or (not data):
            raise ValidationError(
                "Update data is required and must be a non-empty dictionary.",
                "data",
                data,
            )
        allowed_fields = {"name", "description", "total_value"}
        processed_data = {}
        for key, value in data.items():
            if key not in allowed_fields:
                raise ValidationError(f"Invalid field for update: {key}", "data", data)
            if key == "total_value":
                try:
                    processed_data[key] = Decimal(str(value))
                except Exception:
                    raise ValidationError(
                        "Total value must be a valid number.", "total_value", value
                    )
            else:
                processed_data[key] = value
        with get_db_session() as session:
            old_portfolio = self.portfolio_repo.get_by_id(portfolio_id, session)
            if not old_portfolio:
                raise NotFoundError(
                    f"Portfolio {portfolio_id} not found",
                    "portfolio",
                    str(portfolio_id),
                )
            portfolio = self.portfolio_repo.update(
                portfolio_id, processed_data, session
            )
            if portfolio and portfolio.user_address:
                cache_key = f"portfolio:{portfolio.user_address}"
                self.cache.delete(cache_key)
            portfolio_data = {
                "id": portfolio.id,
                "user_id": portfolio.user_id,
                "user_address": portfolio.user_address,
                "name": portfolio.name,
                "description": portfolio.description,
                "total_value": (
                    str(portfolio.total_value)
                    if isinstance(portfolio.total_value, Decimal)
                    else portfolio.total_value
                ),
                "created_at": portfolio.created_at.isoformat(),
                "updated_at": portfolio.updated_at.isoformat(),
            }
            self.audit_service.log_action(
                user_id=portfolio.user_id,
                action_type="PORTFOLIO_UPDATED",
                entity_type="PORTFOLIO",
                entity_id=portfolio.id,
                details={
                    "old_data": {
                        k: str(getattr(old_portfolio, k))
                        for k in processed_data.keys()
                        if hasattr(old_portfolio, k)
                    },
                    "new_data": {k: str(v) for k, v in processed_data.items()},
                },
            )
            logger.info(f"Updated portfolio {portfolio_id}")
            return portfolio_data

    def delete_portfolio(self, portfolio_id: int) -> bool:
        """
        Deletes a portfolio from the system.

        Args:
            portfolio_id: The ID of the portfolio to delete.

        Returns:
            True if the portfolio was successfully deleted, False if not found.

        Raises:
            ValidationError: If the portfolio ID is invalid.
        """
        if not portfolio_id or not isinstance(portfolio_id, int):
            raise ValidationError(
                "Portfolio ID is required and must be an integer.",
                "portfolio_id",
                portfolio_id,
            )
        with get_db_session() as session:
            portfolio = self.portfolio_repo.get_by_id(portfolio_id, session)
            deleted = self.portfolio_repo.delete(portfolio_id, session)
            if deleted and portfolio and portfolio.user_address:
                cache_key = f"portfolio:{portfolio.user_address}"
                self.cache.delete(cache_key)
            if deleted:
                logger.info(f"Deleted portfolio {portfolio_id}")
                self.audit_service.log_action(
                    user_id=portfolio.user_id,
                    action_type="PORTFOLIO_DELETED",
                    entity_type="PORTFOLIO",
                    entity_id=portfolio.id,
                    details={
                        "portfolio_id": portfolio.id,
                        "name": portfolio.name,
                        "user_address": portfolio.user_address,
                    },
                )
            else:
                logger.warning(f"Portfolio {portfolio_id} not found for deletion")
            return deleted

    def get_user_portfolios(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Retrieves all portfolios associated with a specific user ID.

        Args:
            user_id: The ID of the user whose portfolios are to be retrieved.

        Returns:
            A list of dictionaries, each representing a portfolio belonging to the user.

        Raises:
            ValidationError: If the user ID is invalid.
        """
        if not user_id or not isinstance(user_id, int):
            raise ValidationError(
                "User ID is required and must be an integer.", "user_id", user_id
            )
        with get_db_session() as session:
            portfolios = self.portfolio_repo.get_by_user_id(user_id, session)
            portfolio_list = []
            for portfolio in portfolios:
                portfolio_data = {
                    "id": portfolio.id,
                    "user_id": portfolio.user_id,
                    "user_address": portfolio.user_address,
                    "name": portfolio.name,
                    "description": portfolio.description,
                    "total_value": (
                        str(portfolio.total_value)
                        if isinstance(portfolio.total_value, Decimal)
                        else portfolio.total_value
                    ),
                    "created_at": portfolio.created_at.isoformat(),
                    "updated_at": portfolio.updated_at.isoformat(),
                }
                portfolio_list.append(portfolio_data)
            logger.info(
                f"Retrieved {len(portfolio_list)} portfolios for user {user_id}"
            )
            return portfolio_list

    def _validate_portfolio_input(
        self, user_address: str, allocations: Dict[str, float], name: str
    ) -> None:
        """
        Internal helper method to validate common portfolio input parameters.

        Args:
            user_address: The user's wallet address.
            allocations: The asset allocations dictionary.
            name: The portfolio name.

        Raises:
            ValidationError: If any of the input parameters are invalid.
        """
        if not user_address or not isinstance(user_address, str):
            raise ValidationError(
                "User address is required and must be a string.",
                "user_address",
                user_address,
            )
        if not allocations or not isinstance(allocations, dict):
            raise ValidationError(
                "Allocations are required and must be a dictionary.",
                "allocations",
                allocations,
            )
        if len(allocations) == 0:
            raise ValidationError(
                "At least one allocation is required.", "allocations", allocations
            )
        for asset, percentage in allocations.items():
            if not isinstance(asset, str) or not asset.strip():
                raise ValidationError(
                    f"Invalid asset symbol: {asset}. Asset symbol must be a non-empty string.",
                    "allocations",
                    allocations,
                )
            try:
                Decimal(str(percentage))
            except Exception:
                raise ValidationError(
                    f"Invalid percentage for asset {asset}. Must be a valid number.",
                    "allocations",
                    allocations,
                )
            if not 0 <= percentage <= 100:
                raise ValidationError(
                    f"Percentage for asset {asset} must be between 0 and 100.",
                    "allocations",
                    allocations,
                )
        if not name or not isinstance(name, str) or (not name.strip()):
            raise ValidationError(
                "Portfolio name is required and must be a non-empty string.",
                "name",
                name,
            )

    def _normalize_allocations(self, allocations: Dict[str, float]) -> Dict[str, float]:
        """
        Normalizes portfolio allocations so that their sum is 100%.

        Args:
            allocations: A dictionary of asset allocations.

        Returns:
            A new dictionary with normalized allocations.

        Raises:
            ValidationError: If the sum of allocations is zero, preventing normalization.
        """
        total_percentage = sum(allocations.values())
        if total_percentage == 0:
            raise ValidationError(
                "Total allocation percentage cannot be zero.",
                "allocations",
                allocations,
            )
        normalized = {
            asset: percentage / total_percentage * 100
            for asset, percentage in allocations.items()
        }
        return normalized


portfolio_service = PortfolioService()
