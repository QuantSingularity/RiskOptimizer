import unittest
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import ANY, MagicMock

import bcrypt
import jwt
from src.core.config import config
from src.core.exceptions import AuthenticationError, ConflictError, ValidationError
from src.domain.services.auth_service import AuthService

config.security.jwt_secret_key = "test_secret_key"
config.security.jwt_access_token_expires = 3600
config.security.jwt_refresh_token_expires = 86400
config.security.password_hash_rounds = 4
config.security.max_login_attempts = 3
config.security.lockout_time = 300


class TestAuthService(unittest.TestCase):

    def setUp(self) -> Any:
        self.auth_service = AuthService()
        self.auth_service.user_repo = MagicMock()
        self.auth_service.cache = MagicMock()
        self.auth_service.audit_service = MagicMock()
        self.auth_service.cache.exists.return_value = False
        self.auth_service.cache.get.return_value = None
        self.auth_service.cache.set.return_value = True

    def test_hash_password(self) -> Any:
        password = "testpassword123"
        hashed_password = self.auth_service.hash_password(password)
        self.assertIsNotNone(hashed_password)
        self.assertTrue(
            bcrypt.checkpw(password.encode("utf-8"), hashed_password.encode("utf-8"))
        )

    def test_hash_password_invalid_input(self) -> Any:
        with self.assertRaises(ValidationError):
            self.auth_service.hash_password(None)
        with self.assertRaises(ValidationError):
            self.auth_service.hash_password("")

    def test_verify_password_success(self) -> Any:
        password = "testpassword123"
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=self.auth_service.password_rounds),
        ).decode("utf-8")
        self.assertTrue(self.auth_service.verify_password(password, hashed_password))

    def test_verify_password_failure(self) -> Any:
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=self.auth_service.password_rounds),
        ).decode("utf-8")
        self.assertFalse(
            self.auth_service.verify_password(wrong_password, hashed_password)
        )

    def test_generate_tokens(self) -> Any:
        user_id = 1
        email = "test@example.com"
        role = "user"
        tokens = self.auth_service.generate_tokens(user_id, email, role)
        self.assertIn("access_token", tokens)
        self.assertIn("refresh_token", tokens)
        self.assertIn("token_type", tokens)
        self.assertEqual(tokens["token_type"], "Bearer")
        self.assertIn("expires_in", tokens)
        access_payload = jwt.decode(
            tokens["access_token"], config.security.jwt_secret_key, algorithms=["HS256"]
        )
        self.assertEqual(access_payload["user_id"], user_id)
        self.assertEqual(access_payload["email"], email)
        self.assertEqual(access_payload["role"], role)
        self.assertEqual(access_payload["type"], "access")
        refresh_payload = jwt.decode(
            tokens["refresh_token"],
            config.security.jwt_secret_key,
            algorithms=["HS256"],
        )
        self.assertEqual(refresh_payload["user_id"], user_id)
        self.assertEqual(refresh_payload["email"], email)
        self.assertEqual(refresh_payload["type"], "refresh")

    def test_verify_token_access_success(self) -> Any:
        user_id = 1
        email = "test@example.com"
        role = "user"
        tokens = self.auth_service.generate_tokens(user_id, email, role)
        payload = self.auth_service.verify_token(tokens["access_token"], "access")
        self.assertEqual(payload["user_id"], user_id)
        self.assertEqual(payload["email"], email)

    def test_verify_token_refresh_success(self) -> Any:
        user_id = 1
        email = "test@example.com"
        role = "user"
        tokens = self.auth_service.generate_tokens(user_id, email, role)
        payload = self.auth_service.verify_token(tokens["refresh_token"], "refresh")
        self.assertEqual(payload["user_id"], user_id)
        self.assertEqual(payload["email"], email)

    def test_verify_token_expired(self) -> Any:
        expired_payload = {
            "user_id": 1,
            "email": "test@example.com",
            "type": "access",
            "iat": datetime.utcnow() - timedelta(hours=2),
            "exp": datetime.utcnow() - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload, config.security.jwt_secret_key, algorithm="HS256"
        )
        with self.assertRaises(AuthenticationError) as cm:
            self.auth_service.verify_token(expired_token, "access")
        self.assertIn("expired", str(cm.exception))

    def test_verify_token_invalid_signature(self) -> Any:
        invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        with self.assertRaises(AuthenticationError) as cm:
            self.auth_service.verify_token(invalid_token, "access")
        self.assertIn("Invalid token", str(cm.exception))

    def test_verify_token_wrong_type(self) -> Any:
        user_id = 1
        email = "test@example.com"
        role = "user"
        tokens = self.auth_service.generate_tokens(user_id, email, role)
        with self.assertRaises(AuthenticationError) as cm:
            self.auth_service.verify_token(tokens["access_token"], "refresh")
        self.assertIn("Invalid token type", str(cm.exception))

    def test_refresh_access_token_success(self) -> Any:
        user_id = 1
        email = "test@example.com"
        role = "user"
        tokens = self.auth_service.generate_tokens(user_id, email, role)
        mock_user = MagicMock()
        mock_user.id = user_id
        mock_user.email = email
        mock_user.role = role
        mock_user.is_active = True
        self.auth_service.user_repo.get_by_id.return_value = mock_user
        new_access_token_data = self.auth_service.refresh_access_token(
            tokens["refresh_token"]
        )
        self.assertIn("access_token", new_access_token_data)
        self.assertIn("token_type", new_access_token_data)
        self.assertIn("expires_in", new_access_token_data)
        self.auth_service.user_repo.get_by_id.assert_called_once_with(user_id, ANY)

    def test_refresh_access_token_invalid_refresh_token(self) -> Any:
        with self.assertRaises(AuthenticationError) as cm:
            self.auth_service.refresh_access_token("invalid_refresh_token")
        self.assertIn("Invalid token", str(cm.exception))

    def test_blacklist_token(self) -> Any:
        token = self.auth_service.generate_tokens(1, "test@example.com", "user")[
            "access_token"
        ]
        self.auth_service.blacklist_token(token)
        self.auth_service.cache.set.assert_called_once()

    def test_is_token_blacklisted(self) -> Any:
        token = "some_token"
        self.auth_service.cache.exists.return_value = True
        self.assertTrue(self.auth_service.is_token_blacklisted(token))
        self.auth_service.cache.exists.assert_called_once_with(f"blacklist:{token}")

    def test_is_token_not_blacklisted(self) -> Any:
        token = "some_token"
        self.auth_service.cache.exists.return_value = False
        self.assertFalse(self.auth_service.is_token_blacklisted(token))

    def test_authenticate_user_success(self) -> Any:
        email = "test@example.com"
        password = "testpassword123"
        hashed_password = bcrypt.hashpw(
            password.encode("utf-8"),
            bcrypt.gensalt(rounds=self.auth_service.password_rounds),
        ).decode("utf-8")
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = email
        mock_user.username = "testuser"
        mock_user.hashed_password = hashed_password
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.wallet_address = "0x123"
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()
        self.auth_service.user_repo.get_by_email.return_value = mock_user
        user_data, tokens = self.auth_service.authenticate_user(email, password)
        self.assertEqual(user_data["email"], email)
        self.assertIn("access_token", tokens)
        self.auth_service.user_repo.get_by_email.assert_called_once_with(email, ANY)
        self.auth_service.audit_service.log_action.assert_called_with(
            user_id=mock_user.id,
            action_type="LOGIN_SUCCESS",
            entity_type="USER",
            details={"email": email, "ip_address": ANY},
        )

    def test_authenticate_user_invalid_credentials(self) -> Any:
        email = "test@example.com"
        password = "wrongpassword"
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = email
        mock_user.hashed_password = bcrypt.hashpw(
            b"correctpassword", bcrypt.gensalt()
        ).decode("utf-8")
        mock_user.is_active = True
        self.auth_service.user_repo.get_by_email.return_value = mock_user
        with self.assertRaises(AuthenticationError) as cm:
            self.auth_service.authenticate_user(email, password)
        self.assertIn("Invalid email or password", str(cm.exception))
        self.auth_service.audit_service.log_action.assert_called_with(
            user_id=mock_user.id,
            action_type="LOGIN_FAILURE",
            entity_type="USER",
            details={
                "email": email,
                "reason": "Invalid credentials",
                "ip_address": ANY,
            },
        )

    def test_authenticate_user_account_locked(self) -> Any:
        email = "test@example.com"
        password = "testpassword123"
        self.auth_service.cache.get.return_value = str(
            self.auth_service.max_login_attempts
        )
        with self.assertRaises(AuthenticationError) as cm:
            self.auth_service.authenticate_user(email, password)
        self.assertIn("Account locked", str(cm.exception))
        self.auth_service.audit_service.log_action.assert_called_with(
            user_id=None,
            action_type="LOGIN_ATTEMPT_LOCKED",
            entity_type="USER",
            details={"email": email, "ip_address": ANY},
        )

    def test_register_user_success(self) -> Any:
        email = "newuser@example.com"
        username = "newuser"
        password = "newpassword123"
        mock_user = MagicMock()
        mock_user.id = 2
        mock_user.email = email
        mock_user.username = username
        mock_user.role = "user"
        mock_user.is_verified = False
        mock_user.wallet_address = None
        mock_user.created_at = datetime.utcnow()
        mock_user.updated_at = datetime.utcnow()
        self.auth_service.user_repo.create.return_value = mock_user
        user_data, tokens = self.auth_service.register_user(email, username, password)
        self.assertEqual(user_data["email"], email)
        self.assertIn("access_token", tokens)
        self.auth_service.user_repo.create.assert_called_once()
        self.auth_service.audit_service.log_action.assert_called_with(
            user_id=mock_user.id,
            action_type="USER_REGISTERED",
            entity_type="USER",
            entity_id=mock_user.id,
            details={"email": email, "username": username, "ip_address": ANY},
        )

    def test_register_user_conflict(self) -> Any:
        email = "existing@example.com"
        username = "existinguser"
        password = "password123"
        self.auth_service.user_repo.create.side_effect = ConflictError(
            "User already exists", "user"
        )
        with self.assertRaises(ConflictError):
            self.auth_service.register_user(email, username, password)
        self.auth_service.audit_service.log_action.assert_called_with(
            user_id=None,
            action_type="DB_ERROR",
            entity_type="USER",
            details={
                "action": "create",
                "email": email,
                "username": username,
                "error": "User already exists",
            },
        )

    def test_logout_user(self) -> Any:
        access_token = "access_token_value"
        refresh_token = "refresh_token_value"
        self.auth_service.blacklist_token = MagicMock()
        self.auth_service.logout_user(access_token, refresh_token)
        self.auth_service.blacklist_token.assert_any_call(access_token)
        self.auth_service.blacklist_token.assert_any_call(refresh_token)
        self.auth_service.audit_service.log_action.assert_called_with(
            user_id=None,
            action_type="USER_LOGOUT",
            details={"access_token_prefix": access_token[:10]},
        )

    def test_account_not_locked_below_limit(self) -> Any:
        email = "user@example.com"
        self.auth_service.cache.get.return_value = "2"
        self.assertFalse(self.auth_service._is_account_locked(email))

    def test_account_locked_at_limit(self) -> Any:
        email = "user@example.com"
        self.auth_service.cache.get.return_value = "3"
        self.assertTrue(self.auth_service._is_account_locked(email))

    def test_verify_token_blacklisted(self) -> Any:
        tokens = self.auth_service.generate_tokens(1, "t@t.com", "user")
        self.auth_service.cache.exists.return_value = True
        with self.assertRaises(AuthenticationError) as cm:
            self.auth_service.verify_token(tokens["access_token"], "access")
        self.assertIn("revoked", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
