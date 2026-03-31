import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

import bcrypt
import jwt
from riskoptimizer.core.config import config
from riskoptimizer.core.exceptions import AuthenticationError, ValidationError
from riskoptimizer.domain.services.audit_service import audit_service
from riskoptimizer.infrastructure.cache.redis_cache import redis_cache
from riskoptimizer.infrastructure.database.repositories.user_repository import (
    user_repository,
)
from riskoptimizer.infrastructure.database.session import get_db_session

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for authentication and JWT token management.

    This service handles user registration, login, password hashing and verification,
    JWT token generation and validation, token blacklisting, and manages login attempts
    to prevent brute-force attacks.
    """

    def __init__(self) -> None:
        """
        Initialize authentication service with configurations and dependencies.
        """
        self.user_repo = user_repository
        self.cache = redis_cache
        self.audit_service = audit_service
        self.secret_key = config.security.jwt_secret_key
        self.access_token_expires = config.security.jwt_access_token_expires
        self.refresh_token_expires = config.security.jwt_refresh_token_expires
        self.password_rounds = config.security.password_hash_rounds
        self.max_login_attempts = config.security.max_login_attempts
        self.lockout_time = config.security.lockout_time

    def hash_password(self, password: str) -> str:
        """
        Hashes a plain text password using bcrypt.

        Args:
            password: The plain text password to hash.

        Returns:
            The hashed password as a UTF-8 string.

        Raises:
            ValidationError: If the password is empty or not a string.
        """
        if not password or not isinstance(password, str):
            raise ValidationError("Password is required", "password")
        salt = bcrypt.gensalt(rounds=self.password_rounds)
        hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    def verify_password(self, password: str, hashed_password: str) -> bool:
        """
        Verifies a plain text password against a hashed password.

        Args:
            password: The plain text password to verify.
            hashed_password: The hashed password to compare against.

        Returns:
            True if the password matches the hash, False otherwise.
        """
        try:
            return bcrypt.checkpw(
                password.encode("utf-8"), hashed_password.encode("utf-8")
            )
        except Exception as e:
            logger.error(f"Error verifying password: {str(e)}", exc_info=True)
            return False

    def generate_tokens(self, user_id: int, email: str, role: str) -> Dict[str, str]:
        """
        Generates access and refresh JWT tokens for a given user.

        Args:
            user_id: The ID of the user.
            email: The email of the user.
            role: The role of the user (e.g., "user", "admin").

        Returns:
            A dictionary containing the access token, refresh token, token type (Bearer),
            and the expiration time of the access token.
        """
        now = datetime.utcnow()
        access_payload = {
            "user_id": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": now + timedelta(seconds=self.access_token_expires),
        }
        access_token = jwt.encode(access_payload, self.secret_key, algorithm="HS256")
        refresh_payload = {
            "user_id": user_id,
            "email": email,
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(seconds=self.refresh_token_expires),
        }
        refresh_token = jwt.encode(refresh_payload, self.secret_key, algorithm="HS256")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": self.access_token_expires,
        }

    def verify_token(self, token: str, token_type: str = "access") -> Dict[str, Any]:
        """
        Verifies and decodes a JWT token.

        Args:
            token: The JWT token string.
            token_type: The expected type of the token ("access" or "refresh").

        Returns:
            The decoded token payload.

        Raises:
            AuthenticationError: If the token is invalid, expired, or blacklisted,
                                 or if the token type does not match the expected type.
        """
        try:
            if self.is_token_blacklisted(token):
                raise AuthenticationError("Token has been revoked")
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            if payload.get("type") != token_type:
                raise AuthenticationError(f"Invalid token type: expected {token_type}")
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise AuthenticationError(f"Invalid token: {str(e)}")

    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Generates a new access token using a valid refresh token.

        Args:
            refresh_token: The valid refresh token.

        Returns:
            A dictionary containing the new access token, token type, and expiration time.

        Raises:
            AuthenticationError: If the refresh token is invalid or the user is not found/inactive.
        """
        payload = self.verify_token(refresh_token, "refresh")
        with get_db_session() as session:
            user = self.user_repo.get_by_id(payload["user_id"], session)
            if not user or not user.is_active:
                raise AuthenticationError("User not found or inactive")
            tokens = self.generate_tokens(user.id, user.email, user.role)
            return {
                "access_token": tokens["access_token"],
                "token_type": "Bearer",
                "expires_in": self.access_token_expires,
            }

    def blacklist_token(self, token: str) -> None:
        """
        Adds a JWT token to a blacklist in Redis, effectively revoking it.
        The token will remain blacklisted until its original expiration time.

        Args:
            token: The JWT token string to blacklist.
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=["HS256"],
                options={"verify_exp": False},
            )
            exp = payload.get("exp")
            if exp:
                exp_datetime = datetime.utcfromtimestamp(exp)
                ttl = int((exp_datetime - datetime.utcnow()).total_seconds())
                if ttl > 0:
                    cache_key = f"blacklist:{token}"
                    self.cache.set(cache_key, True, ttl=ttl)
                    logger.info(f"Token blacklisted for {ttl} seconds")
        except Exception as e:
            logger.error(f"Error blacklisting token: {str(e)}", exc_info=True)

    def is_token_blacklisted(self, token: str) -> bool:
        """
        Checks if a given JWT token is present in the blacklist.

        Args:
            token: The JWT token string to check.

        Returns:
            True if the token is blacklisted, False otherwise.
        """
        try:
            cache_key = f"blacklist:{token}"
            return self.cache.exists(cache_key)
        except Exception as e:
            logger.error(f"Error checking token blacklist: {str(e)}", exc_info=True)
            return False

    def _get_login_attempt_key(self, email: str) -> str:
        """
        Generates a unique cache key for tracking login attempts for a given email.

        Args:
            email: The email address of the user.

        Returns:
            A string representing the cache key.
        """
        return f"login_attempts:{email}"

    def _record_failed_login_attempt(self, email: str) -> None:
        """
        Records a failed login attempt for a user and increments the attempt count.
        If it's the first attempt, sets an expiration for the lockout period.

        Args:
            email: The email address of the user who failed to log in.
        """
        key = self._get_login_attempt_key(email)
        attempts = self.cache.incr(key)
        if attempts == 1:
            self.cache.expire(key, self.lockout_time)
        logger.warning(f"Failed login attempt for {email}. Attempts: {attempts}")

    def _reset_login_attempts(self, email: str) -> None:
        """
        Resets the failed login attempt count for a user.
        This should be called upon successful login.

        Args:
            email: The email address of the user.
        """
        key = self._get_login_attempt_key(email)
        self.cache.delete(key)
        logger.info(f"Login attempts reset for {email}")

    def _is_account_locked(self, email: str) -> bool:
        """
        Checks if a user's account is currently locked due to too many failed login attempts.

        Args:
            email: The email address of the user.

        Returns:
            True if the account is locked, False otherwise.
        """
        key = self._get_login_attempt_key(email)
        attempts = self.cache.get(key)
        if attempts and int(attempts) >= self.max_login_attempts:
            logger.warning(
                f"Account for {email} is locked due to too many failed login attempts."
            )
            return True
        return False

    def authenticate_user(
        self, email: str, password: str
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Authenticates a user by verifying their email and password.
        Manages login attempts and account lockout.

        Args:
            email: The user's email address.
            password: The user's plain text password.

        Returns:
            A tuple containing the user's data (dict) and generated JWT tokens (dict).

        Raises:
            ValidationError: If email or password input is invalid.
            AuthenticationError: If authentication fails due to incorrect credentials,
                                 inactive account, or account lockout.
        """
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required", "email")
        if not password or not isinstance(password, str):
            raise ValidationError("Password is required", "password")
        if self._is_account_locked(email):
            self.audit_service.log_action(
                user_id=None,
                action_type="LOGIN_ATTEMPT_LOCKED",
                entity_type="USER",
                details={
                    "email": email,
                    "ip_address": request.remote_addr if request else "N/A",
                },
            )
            raise AuthenticationError(
                f"Account locked. Please try again in {self.lockout_time // 60} minutes."
            )
        with get_db_session() as session:
            user = self.user_repo.get_by_email(email, session)
            if not user:
                self._record_failed_login_attempt(email)
                self.audit_service.log_action(
                    user_id=None,
                    action_type="LOGIN_FAILURE",
                    entity_type="USER",
                    details={
                        "email": email,
                        "reason": "Invalid credentials",
                        "ip_address": request.remote_addr if request else "N/A",
                    },
                )
                raise AuthenticationError("Invalid email or password")
            if not user.is_active:
                self._record_failed_login_attempt(email)
                self.audit_service.log_action(
                    user_id=user.id,
                    action_type="LOGIN_FAILURE",
                    entity_type="USER",
                    details={
                        "email": email,
                        "reason": "Account inactive",
                        "ip_address": request.remote_addr if request else "N/A",
                    },
                )
                raise AuthenticationError("User account is inactive")
            if not self.verify_password(password, user.hashed_password):
                self._record_failed_login_attempt(email)
                self.audit_service.log_action(
                    user_id=user.id,
                    action_type="LOGIN_FAILURE",
                    entity_type="USER",
                    details={
                        "email": email,
                        "reason": "Invalid credentials",
                        "ip_address": request.remote_addr if request else "N/A",
                    },
                )
                raise AuthenticationError("Invalid email or password")
            self._reset_login_attempts(email)
            self.audit_service.log_action(
                user_id=user.id,
                action_type="LOGIN_SUCCESS",
                entity_type="USER",
                details={
                    "email": email,
                    "ip_address": request.remote_addr if request else "N/A",
                },
            )
            tokens = self.generate_tokens(user.id, user.email, user.role)
            user_data = {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "wallet_address": user.wallet_address,
                "role": user.role,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }
            logger.info(f"User authenticated successfully: {email}")
            return (user_data, tokens)

    def register_user(
        self,
        email: str,
        username: str,
        password: str,
        wallet_address: Optional[str] = None,
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        """
        Registers a new user in the system.

        Args:
            email: The new user's email address.
            username: The new user's chosen username.
            password: The new user's plain text password.
            wallet_address: An optional blockchain wallet address for the user.

        Returns:
            A tuple containing the newly created user's data (dict) and generated JWT tokens (dict).

        Raises:
            ValidationError: If any input is invalid.
            ConflictError: If a user with the provided email, username, or wallet address already exists.
        """
        if not email or not isinstance(email, str):
            raise ValidationError("Email is required", "email")
        if not username or not isinstance(username, str):
            raise ValidationError("Username is required", "username")
        if not password or not isinstance(password, str):
            raise ValidationError("Password is required", "password")
        hashed_password = self.hash_password(password)
        with get_db_session() as session:
            user = self.user_repo.create(
                email=email,
                username=username,
                hashed_password=hashed_password,
                wallet_address=wallet_address,
                session=session,
            )
            tokens = self.generate_tokens(user.id, user.email, user.role)
            user_data = {
                "id": user.id,
                "email": user.email,
                "username": user.username,
                "wallet_address": user.wallet_address,
                "role": user.role,
                "is_verified": user.is_verified,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            }
            logger.info(f"User registered successfully: {email}")
            self.audit_service.log_action(
                user_id=user.id,
                action_type="USER_REGISTERED",
                entity_type="USER",
                entity_id=user.id,
                details={
                    "email": email,
                    "username": username,
                    "ip_address": request.remote_addr if request else "N/A",
                },
            )
            return (user_data, tokens)

    def logout_user(self, access_token: str, refresh_token: str) -> None:
        """
        Logs out a user by blacklisting their access and refresh tokens.

        Args:
            access_token: The user's current access token.
            refresh_token: The user's current refresh token.
        """
        self.blacklist_token(access_token)
        self.blacklist_token(refresh_token)
        self.audit_service.log_action(
            user_id=None,
            action_type="USER_LOGOUT",
            details={"access_token_prefix": access_token[:10]},
        )
        logger.info("User logged out successfully")


auth_service = AuthService()
