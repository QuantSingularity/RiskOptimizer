import logging
import unittest
from typing import Any

import requests

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

BASE_URL = "http://localhost:8000/api/v1"


class TestAuthAPI(unittest.TestCase):

    def setUp(self) -> Any:
        try:
            requests.get(f"{BASE_URL}/health")
        except requests.exceptions.ConnectionError:
            self.fail(
                "Backend not running. Please start the backend server before running integration tests."
            )
        self.test_user_email = "integration_test@example.com"
        self.test_user_username = "integration_test_user"
        self.test_user_password = "SecurePassword123!"
        self._cleanup_test_user()

    def tearDown(self) -> Any:
        self._cleanup_test_user()

    def _cleanup_test_user(self) -> Any:
        try:
            login_data = {
                "email": self.test_user_email,
                "password": self.test_user_password,
            }
            login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
            if login_response.status_code == 200:
                login_response.json()["access_token"]
        except Exception as e:
            logger.info(f"Error during test user cleanup: {e}")

    def test_1_register_user(self) -> Any:
        register_data = {
            "email": self.test_user_email,
            "username": self.test_user_username,
            "password": self.test_user_password,
        }
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        self.assertEqual(
            response.status_code,
            201,
            f"Expected 201, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertIn("user", data)
        self.assertIn("tokens", data)
        self.assertEqual(data["user"]["email"], self.test_user_email)
        self.assertIn("access_token", data["tokens"])
        self.assertIn("refresh_token", data["tokens"])

    def test_2_login_user(self) -> Any:
        self.test_1_register_user()
        login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
        }
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertIn("user", data)
        self.assertIn("tokens", data)
        self.assertEqual(data["user"]["email"], self.test_user_email)
        self.assertIn("access_token", data["tokens"])
        self.assertIn("refresh_token", data["tokens"])

    def test_3_register_existing_user(self) -> Any:
        self.test_1_register_user()
        register_data = {
            "email": self.test_user_email,
            "username": "another_username",
            "password": "AnotherPassword123!",
        }
        response = requests.post(f"{BASE_URL}/auth/register", json=register_data)
        self.assertEqual(
            response.status_code,
            409,
            f"Expected 409, got {response.status_code}: {response.text}",
        )
        self.assertIn("User with email", response.json()["detail"])

    def test_4_login_invalid_credentials(self) -> Any:
        login_data = {"email": self.test_user_email, "password": "wrongpassword"}
        response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        self.assertEqual(
            response.status_code,
            401,
            f"Expected 401, got {response.status_code}: {response.text}",
        )
        self.assertIn("Invalid email or password", response.json()["detail"])

    def test_5_refresh_token(self) -> Any:
        login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
        }
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        self.assertEqual(login_response.status_code, 200)
        refresh_token = login_response.json()["tokens"]["refresh_token"]
        refresh_data = {"refresh_token": refresh_token}
        response = requests.post(f"{BASE_URL}/auth/refresh", json=refresh_data)
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertIn("access_token", data)
        self.assertIn("token_type", data)
        self.assertIn("expires_in", data)

    def test_6_logout_user(self) -> Any:
        login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
        }
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        self.assertEqual(login_response.status_code, 200)
        tokens = login_response.json()["tokens"]
        logout_data = {
            "access_token": tokens["access_token"],
            "refresh_token": tokens["refresh_token"],
        }
        response = requests.post(f"{BASE_URL}/auth/logout", json=logout_data)
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.text}",
        )
        self.assertIn("message", response.json())
        self.assertEqual(response.json()["message"], "Successfully logged out.")
        headers = {"Authorization": f"Bearer {tokens['access_token']}"}
        protected_response = requests.get(f"{BASE_URL}/users/me", headers=headers)
        self.assertEqual(
            protected_response.status_code,
            401,
            f"Expected 401 after logout, got {protected_response.status_code}: {protected_response.text}",
        )


if __name__ == "__main__":
    unittest.main()
