"""
Integration tests for Authentication API.

Uses Flask's built-in test client and mocks all external dependencies
(database, Redis) so no live server or database is required.
"""

import logging
import unittest
from unittest.mock import MagicMock, patch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared test-client factory
# ---------------------------------------------------------------------------


def _infra_patches():
    """Return list of patches that neutralise all external infrastructure."""
    return [
        patch("src.infrastructure.database.session.init_db", return_value=None),
        patch(
            "src.infrastructure.database.session.check_db_connection", return_value=True
        ),
        patch(
            "src.api.middleware.rate_limit_middleware.apply_rate_limiting",
            return_value=None,
        ),
        patch("src.utils.performance.apply_performance_monitoring", return_value=None),
    ]


def _make_test_client(patches):
    """Start patches, build app, return (app, client)."""
    mock_redis = MagicMock()
    mock_redis.health_check.return_value = True
    redis_patch = patch("src.infrastructure.cache.redis_cache.redis_cache", mock_redis)
    patches.append(redis_patch)

    for p in patches:
        p.start()

    from app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return app, app.test_client()


class TestAuthAPI(unittest.TestCase):

    def setUp(self):
        self._patches = _infra_patches()
        self.app, self.client = _make_test_client(self._patches)

        self.email = "integration_test@example.com"
        self.username = "integration_test_user"
        self.password = "SecurePassword123!"

        self.mock_user = {"id": 1, "email": self.email, "username": self.username}
        self.mock_tokens = {
            "access_token": "mock_access_token",
            "refresh_token": "mock_refresh_token",
            "token_type": "bearer",
            "expires_in": 3600,
        }

    def tearDown(self):
        for p in self._patches:
            p.stop()

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _register(self):
        with patch(
            "src.domain.services.auth_service.auth_service.register_user",
            return_value=(self.mock_user, self.mock_tokens),
        ):
            return self.client.post(
                "/api/v1/auth/register",
                json={
                    "email": self.email,
                    "username": self.username,
                    "password": self.password,
                },
            )

    # ------------------------------------------------------------------
    # tests
    # ------------------------------------------------------------------

    def test_1_register_user(self):
        """POST /auth/register → 201 with user and tokens."""
        response = self._register()
        self.assertEqual(
            response.status_code,
            201,
            f"Expected 201, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        self.assertIn("user", payload)
        self.assertIn("tokens", payload)
        self.assertEqual(payload["user"]["email"], self.email)
        self.assertIn("access_token", payload["tokens"])
        self.assertIn("refresh_token", payload["tokens"])

    def test_2_login_user(self):
        """POST /auth/login → 200 with user and tokens."""
        with patch(
            "src.domain.services.auth_service.auth_service.authenticate_user",
            return_value=(self.mock_user, self.mock_tokens),
        ):
            response = self.client.post(
                "/api/v1/auth/login",
                json={"email": self.email, "password": self.password},
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        self.assertIn("user", payload)
        self.assertIn("tokens", payload)
        self.assertEqual(payload["user"]["email"], self.email)
        self.assertIn("access_token", payload["tokens"])
        self.assertIn("refresh_token", payload["tokens"])

    def test_3_register_existing_user(self):
        """POST /auth/register with duplicate email → error containing 'User with email'."""
        from src.core.exceptions import RiskOptimizerException

        conflict = RiskOptimizerException(
            f"User with email {self.email} already exists", "USER_ALREADY_EXISTS"
        )
        with patch(
            "src.domain.services.auth_service.auth_service.register_user",
            side_effect=conflict,
        ):
            response = self.client.post(
                "/api/v1/auth/register",
                json={
                    "email": self.email,
                    "username": "other",
                    "password": "Pass123!AbcDef",
                },
            )
        self.assertIn("User with email", str(response.get_json()))

    def test_4_login_invalid_credentials(self):
        """POST /auth/login with wrong password → 401."""
        from src.core.exceptions import AuthenticationError

        with patch(
            "src.domain.services.auth_service.auth_service.authenticate_user",
            side_effect=AuthenticationError("Invalid email or password"),
        ):
            response = self.client.post(
                "/api/v1/auth/login",
                json={"email": self.email, "password": "wrongpassword"},
            )
        self.assertEqual(
            response.status_code,
            401,
            f"Expected 401, got {response.status_code}: {response.data}",
        )
        self.assertIn("Invalid email or password", str(response.get_json()))

    def test_5_refresh_token(self):
        """POST /auth/refresh → 200 with new access token."""
        refreshed = {
            "access_token": "new_access_token",
            "token_type": "bearer",
            "expires_in": 3600,
        }
        with patch(
            "src.domain.services.auth_service.auth_service.refresh_access_token",
            return_value=refreshed,
        ):
            response = self.client.post(
                "/api/v1/auth/refresh",
                json={"refresh_token": "mock_refresh_token"},
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        self.assertIn("access_token", payload)
        self.assertIn("token_type", payload)
        self.assertIn("expires_in", payload)

    def test_6_logout_user(self):
        """POST /auth/logout → 200 with success message."""
        with patch(
            "src.domain.services.auth_service.auth_service.logout_user",
            return_value=None,
        ):
            response = self.client.post(
                "/api/v1/auth/logout",
                json={
                    "access_token": "mock_access_token",
                    "refresh_token": "mock_refresh_token",
                },
                headers={"Authorization": "Bearer mock_access_token"},
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        self.assertIn("message", str(response.get_json()))


if __name__ == "__main__":
    unittest.main()
