import logging
from typing import Any, Dict, List, Optional

from cryptography.fernet import Fernet
from riskoptimizer.core.config import config
from riskoptimizer.core.exceptions import ConflictError, DatabaseError, NotFoundError
from riskoptimizer.domain.services.audit_service import audit_service
from riskoptimizer.infrastructure.database.models import User
from riskoptimizer.infrastructure.database.session import get_db_session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class UserRepository:
    """
    Repository for user-related database operations.

    This class provides methods for interacting with the User model in the database,
    including creating, retrieving, updating, and deleting user records.
    It also handles encryption/decryption of sensitive user data like wallet addresses
    and integrates with an audit service for logging database actions.
    """

    def __init__(self, session: Optional[Session] = None) -> None:
        """
        Initializes the UserRepository.

        Args:
            session: An optional SQLAlchemy session to use. If not provided,
                     methods will obtain a session internally.
        """
        self._session = session
        key = config.security.data_encryption_key
        if isinstance(key, str):
            key = key.encode("utf-8")
        self.fernet = Fernet(key)
        self.audit_service = audit_service

    def _get_session(self, session: Optional[Session] = None) -> Session:
        """
        Helper method to get a SQLAlchemy session.

        Args:
            session: An optional session provided by the caller.

        Returns:
            A SQLAlchemy session. If a session is provided, it's used; otherwise,
            a new session is obtained from `get_db_session()`.
        """
        return session or get_db_session()

    def _encrypt_data(self, data: Optional[str]) -> Optional[str]:
        """
        Encrypts a string using the configured Fernet key.

        Args:
            data: The string to encrypt. Can be None.

        Returns:
            The encrypted string as a UTF-8 decoded byte string, or None if input was None.
        """
        if data is None:
            return None
        return self.fernet.encrypt(data.encode("utf-8")).decode("utf-8")

    def _decrypt_data(self, data: Optional[str]) -> Optional[str]:
        """
        Decrypts a string using the configured Fernet key.

        Args:
            data: The encrypted string to decrypt. Can be None.

        Returns:
            The decrypted string, or None if input was None or decryption failed.
        """
        if data is None:
            return None
        try:
            return self.fernet.decrypt(data.encode("utf-8")).decode("utf-8")
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}", exc_info=True)
            return None

    def get_by_id(
        self, user_id: int, session: Optional[Session] = None
    ) -> Optional[User]:
        """
        Retrieves a user by their unique ID.

        Args:
            user_id: The integer ID of the user.
            session: An optional SQLAlchemy session.

        Returns:
            The User object if found, otherwise None.
            The wallet_address field will be decrypted if present.

        Raises:
            DatabaseError: If a database error occurs during retrieval.
        """
        try:
            db = self._get_session(session)
            user = db.query(User).filter(User.id == user_id).first()
            if user and user.wallet_address:
                user.wallet_address = self._decrypt_data(user.wallet_address)
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by ID: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=user_id,
                action_type="DB_ERROR",
                entity_type="USER",
                details={"action": "get_by_id", "error": str(e)},
            )
            raise DatabaseError(f"Failed to get user: {str(e)}")

    def get_by_email(
        self, email: str, session: Optional[Session] = None
    ) -> Optional[User]:
        """
        Retrieves a user by their email address.

        Args:
            email: The email address of the user.
            session: An optional SQLAlchemy session.

        Returns:
            The User object if found, otherwise None.
            The wallet_address field will be decrypted if present.

        Raises:
            DatabaseError: If a database error occurs during retrieval.
        """
        try:
            db = self._get_session(session)
            user = db.query(User).filter(User.email == email).first()
            if user and user.wallet_address:
                user.wallet_address = self._decrypt_data(user.wallet_address)
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by email: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="USER",
                details={"action": "get_by_email", "email": email, "error": str(e)},
            )
            raise DatabaseError(f"Failed to get user: {str(e)}")

    def get_by_username(
        self, username: str, session: Optional[Session] = None
    ) -> Optional[User]:
        """
        Retrieves a user by their username.

        Args:
            username: The username of the user.
            session: An optional SQLAlchemy session.

        Returns:
            The User object if found, otherwise None.
            The wallet_address field will be decrypted if present.

        Raises:
            DatabaseError: If a database error occurs during retrieval.
        """
        try:
            db = self._get_session(session)
            user = db.query(User).filter(User.username == username).first()
            if user and user.wallet_address:
                user.wallet_address = self._decrypt_data(user.wallet_address)
            return user
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by username: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="USER",
                details={
                    "action": "get_by_username",
                    "username": username,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to get user: {str(e)}")

    def get_by_wallet_address(
        self, wallet_address: str, session: Optional[Session] = None
    ) -> Optional[User]:
        """
        Retrieves a user by their wallet address.
        The provided wallet address is encrypted before querying the database.

        Args:
            wallet_address: The wallet address of the user.
            session: An optional SQLAlchemy session.

        Returns:
            The User object if found, otherwise None.
            The wallet_address field will be decrypted before returning.

        Raises:
            DatabaseError: If a database error occurs during retrieval.
        """
        try:
            db = self._get_session(session)
            encrypted_wallet_address = self._encrypt_data(wallet_address)
            user = (
                db.query(User)
                .filter(User.wallet_address == encrypted_wallet_address)
                .first()
            )
            if user and user.wallet_address:
                user.wallet_address = self._decrypt_data(user.wallet_address)
            return user
        except SQLAlchemyError as e:
            logger.error(
                f"Error getting user by wallet address: {str(e)}", exc_info=True
            )
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="USER",
                details={"action": "get_by_wallet_address", "error": str(e)},
            )
            raise DatabaseError(f"Failed to get user: {str(e)}")

    def create(
        self,
        email: str,
        username: str,
        hashed_password: str,
        wallet_address: Optional[str] = None,
        role: str = "user",
        session: Optional[Session] = None,
    ) -> User:
        """
        Creates a new user record in the database.

        Args:
            email: The user's email address.
            username: The user's chosen username.
            hashed_password: The bcrypt hashed password for the user.
            wallet_address: An optional wallet address for the user. This will be encrypted.
            role: The role of the user (e.g., "user", "admin"). Defaults to "user".
            session: An optional SQLAlchemy session.

        Returns:
            The newly created User object.

        Raises:
            ConflictError: If a user with the given email, username, or wallet address already exists.
            DatabaseError: If any other database error occurs during creation.
        """
        try:
            db = self._get_session(session)
            encrypted_wallet_address = self._encrypt_data(wallet_address)
            user = User(
                email=email,
                username=username,
                hashed_password=hashed_password,
                wallet_address=encrypted_wallet_address,
                role=role,
            )
            db.add(user)
            db.flush()
            if user.wallet_address:
                user.wallet_address = self._decrypt_data(user.wallet_address)
            logger.info(f"Created user {user.id} with email {email}")
            self.audit_service.log_action(
                user_id=user.id,
                action_type="USER_CREATED",
                entity_type="USER",
                entity_id=user.id,
                details={"email": email, "username": username},
            )
            return user
        except IntegrityError as e:
            logger.error(f"Error creating user (conflict): {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="USER",
                details={
                    "action": "create",
                    "email": email,
                    "username": username,
                    "error": str(e),
                },
            )
            if "email" in str(e).lower():
                raise ConflictError(f"User with email {email} already exists", "user")
            elif "username" in str(e).lower():
                raise ConflictError(
                    f"User with username {username} already exists", "user"
                )
            elif "wallet_address" in str(e).lower():
                raise ConflictError(
                    f"User with wallet address {wallet_address} already exists", "user"
                )
            else:
                raise ConflictError("User already exists", "user")
        except SQLAlchemyError as e:
            logger.error(f"Error creating user: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="USER",
                details={
                    "action": "create",
                    "email": email,
                    "username": username,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to create user: {str(e)}")

    def update(
        self, user_id: int, data: Dict[str, Any], session: Optional[Session] = None
    ) -> User:
        """
        Updates an existing user's information.

        Args:
            user_id: The ID of the user to update.
            data: A dictionary containing the fields to update and their new values.
                  Sensitive fields like 'wallet_address' will be encrypted.
            session: An optional SQLAlchemy session.

        Returns:
            The updated User object.

        Raises:
            NotFoundError: If the user with the given ID is not found.
            ConflictError: If the update violates unique constraints (e.g., duplicate email).
            DatabaseError: If any other database error occurs during update.
        """
        try:
            db = self._get_session(session)
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                raise NotFoundError(f"User {user_id} not found", "user", str(user_id))
            old_data = {
                key: getattr(user, key) for key in data.keys() if hasattr(user, key)
            }
            if "wallet_address" in data and data["wallet_address"] is not None:
                data["wallet_address"] = self._encrypt_data(data["wallet_address"])
            for key, value in data.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            db.flush()
            if user.wallet_address:
                user.wallet_address = self._decrypt_data(user.wallet_address)
            logger.info(f"Updated user {user_id}")
            self.audit_service.log_action(
                user_id=user.id,
                action_type="USER_UPDATED",
                entity_type="USER",
                entity_id=user.id,
                details={"old_data": old_data, "new_data": data},
            )
            return user
        except NotFoundError:
            raise
        except IntegrityError as e:
            logger.error(f"Error updating user (conflict): {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=user_id,
                action_type="DB_ERROR",
                entity_type="USER",
                details={
                    "action": "update",
                    "user_id": user_id,
                    "data": data,
                    "error": str(e),
                },
            )
            if "email" in str(e).lower():
                raise ConflictError(
                    f"User with email {data.get('email')} already exists", "user"
                )
            elif "username" in str(e).lower():
                raise ConflictError(
                    f"User with username {data.get('username')} already exists", "user"
                )
            elif "wallet_address" in str(e).lower():
                display_wallet_address = (
                    self._decrypt_data(data.get("wallet_address"))
                    if data.get("wallet_address")
                    else ""
                )
                raise ConflictError(
                    f"User with wallet address {display_wallet_address} already exists",
                    "user",
                )
            else:
                raise ConflictError("Update violates unique constraints", "user")
        except SQLAlchemyError as e:
            logger.error(f"Error updating user: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=user_id,
                action_type="DB_ERROR",
                entity_type="USER",
                details={
                    "action": "update",
                    "user_id": user_id,
                    "data": data,
                    "error": str(e),
                },
            )
            raise DatabaseError(f"Failed to update user: {str(e)}")

    def delete(self, user_id: int, session: Optional[Session] = None) -> bool:
        """
        Deletes a user record from the database.

        Args:
            user_id: The ID of the user to delete.
            session: An optional SQLAlchemy session.

        Returns:
            True if the user was successfully deleted, False if not found.

        Raises:
            DatabaseError: If a database error occurs during deletion.
        """
        try:
            db = self._get_session(session)
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                return False
            audit_details = {
                "user_id": user.id,
                "email": user.email,
                "username": user.username,
            }
            db.delete(user)
            db.flush()
            logger.info(f"Deleted user {user_id}")
            self.audit_service.log_action(
                user_id=user.id,
                action_type="USER_DELETED",
                entity_type="USER",
                entity_id=user.id,
                details=audit_details,
            )
            return True
        except SQLAlchemyError as e:
            logger.error(f"Error deleting user: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=user_id,
                action_type="DB_ERROR",
                entity_type="USER",
                details={"action": "delete", "user_id": user_id, "error": str(e)},
            )
            raise DatabaseError(f"Failed to delete user: {str(e)}")

    def get_all(
        self, skip: int = 0, limit: int = 100, session: Optional[Session] = None
    ) -> List[User]:
        """
        Retrieves a paginated list of all users.

        Args:
            skip: The number of records to skip (for pagination offset). Defaults to 0.
            limit: The maximum number of records to return. Defaults to 100.
            session: An optional SQLAlchemy session.

        Returns:
            A list of User objects.
            Wallet addresses will be decrypted for each user.

        Raises:
            DatabaseError: If a database error occurs during retrieval.
        """
        try:
            db = self._get_session(session)
            users = db.query(User).offset(skip).limit(limit).all()
            for user in users:
                if user.wallet_address:
                    user.wallet_address = self._decrypt_data(user.wallet_address)
            return users
        except SQLAlchemyError as e:
            logger.error(f"Error getting all users: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="USER",
                details={"action": "get_all", "error": str(e)},
            )
            raise DatabaseError(f"Failed to get users: {str(e)}")

    def count(self, session: Optional[Session] = None) -> int:
        """
        Counts the total number of user records in the database.

        Args:
            session: An optional SQLAlchemy session.

        Returns:
            The total count of users as an integer.

        Raises:
            DatabaseError: If a database error occurs during counting.
        """
        try:
            db = self._get_session(session)
            count = db.query(User).count()
            return count
        except SQLAlchemyError as e:
            logger.error(f"Error counting users: {str(e)}", exc_info=True)
            self.audit_service.log_action(
                user_id=None,
                action_type="DB_ERROR",
                entity_type="USER",
                details={"action": "count", "error": str(e)},
            )
            raise DatabaseError(f"Failed to count users: {str(e)}")


user_repository = UserRepository()
