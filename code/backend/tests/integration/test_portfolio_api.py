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


class TestPortfolioAPI(unittest.TestCase):

    def setUp(self) -> Any:
        try:
            requests.get(f"{BASE_URL}/health")
        except requests.exceptions.ConnectionError:
            self.fail(
                "Backend not running. Please start the backend server before running integration tests."
            )
        self.test_user_email = "portfolio_test@example.com"
        self.test_user_username = "portfolio_test_user"
        self.test_user_password = "SecurePortfolio123!"
        self.access_token = None
        self.refresh_token = None
        self.user_id = None
        self.user_address = "0xPortfolioTestAddress"
        self._register_and_login_user()

    def tearDown(self) -> Any:
        self._logout_user()
        self._cleanup_test_user()

    def _register_and_login_user(self) -> Any:
        register_data = {
            "email": self.test_user_email,
            "username": self.test_user_username,
            "password": self.test_user_password,
        }
        register_response = requests.post(
            f"{BASE_URL}/auth/register", json=register_data
        )
        if register_response.status_code == 409:
            logger.info(
                f"User {self.test_user_email} already exists, proceeding to login."
            )
        elif register_response.status_code != 201:
            self.fail(
                f"Failed to register user: {register_response.status_code} - {register_response.text}"
            )
        login_data = {
            "email": self.test_user_email,
            "password": self.test_user_password,
        }
        login_response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
        self.assertEqual(
            login_response.status_code,
            200,
            f"Failed to login user: {login_response.status_code} - {login_response.text}",
        )
        data = login_response.json()
        self.access_token = data["tokens"]["access_token"]
        self.refresh_token = data["tokens"]["refresh_token"]
        self.user_id = data["user"]["id"]

    def _logout_user(self) -> Any:
        if self.access_token and self.refresh_token:
            logout_data = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
            }
            requests.post(f"{BASE_URL}/auth/logout", json=logout_data)

    def _cleanup_test_user(self) -> Any:
        pass

    def get_auth_headers(self) -> Any:
        return {"Authorization": f"Bearer {self.access_token}"}

    def test_1_create_portfolio(self) -> Any:
        create_data = {
            "user_id": self.user_id,
            "user_address": self.user_address,
            "name": "My First Portfolio",
            "description": "A test portfolio for integration testing",
        }
        response = requests.post(
            f"{BASE_URL}/portfolios", json=create_data, headers=self.get_auth_headers()
        )
        self.assertEqual(
            response.status_code,
            201,
            f"Expected 201, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertIn("id", data)
        self.assertEqual(data["name"], "My First Portfolio")
        self.portfolio_id = data["id"]

    def test_2_save_portfolio_allocations(self) -> Any:
        self.test_1_create_portfolio()
        save_data = {
            "user_address": self.user_address,
            "allocations": {"BTC": 60.0, "ETH": 40.0},
            "name": "Updated Portfolio with Allocations",
        }
        response = requests.post(
            f"{BASE_URL}/portfolios/save",
            json=save_data,
            headers=self.get_auth_headers(),
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertIn("allocations", data)
        self.assertEqual(len(data["allocations"]), 2)
        self.assertEqual(data["name"], "Updated Portfolio with Allocations")

    def test_3_get_portfolio_by_address(self) -> Any:
        self.test_2_save_portfolio_allocations()
        response = requests.get(
            f"{BASE_URL}/portfolios/address/{self.user_address}",
            headers=self.get_auth_headers(),
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertIn("total_value", data)
        self.assertIn("allocations", data)
        self.assertEqual(len(data["allocations"]), 2)

    def test_4_update_portfolio(self) -> Any:
        self.test_1_create_portfolio()
        update_data = {
            "description": "A much better description",
            "total_value": 5000.0,
        }
        response = requests.put(
            f"{BASE_URL}/portfolios/{self.portfolio_id}",
            json=update_data,
            headers=self.get_auth_headers(),
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertEqual(data["description"], "A much better description")
        self.assertEqual(data["total_value"], "5000.00")

    def test_5_get_user_portfolios(self) -> Any:
        self.test_1_create_portfolio()
        create_data_2 = {
            "user_id": self.user_id,
            "user_address": "0xAnotherPortfolioAddress",
            "name": "My Second Portfolio",
            "description": "Another test portfolio",
        }
        requests.post(
            f"{BASE_URL}/portfolios",
            json=create_data_2,
            headers=self.get_auth_headers(),
        )
        response = requests.get(
            f"{BASE_URL}/portfolios/user/{self.user_id}",
            headers=self.get_auth_headers(),
        )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.text}",
        )
        data = response.json()
        self.assertGreaterEqual(len(data), 2)
        self.assertTrue(any((p["name"] == "My First Portfolio" for p in data)))
        self.assertTrue(any((p["name"] == "My Second Portfolio" for p in data)))

    def test_6_delete_portfolio(self) -> Any:
        self.test_1_create_portfolio()
        response = requests.delete(
            f"{BASE_URL}/portfolios/{self.portfolio_id}",
            headers=self.get_auth_headers(),
        )
        self.assertEqual(
            response.status_code,
            204,
            f"Expected 204, got {response.status_code}: {response.text}",
        )
        get_response = requests.get(
            f"{BASE_URL}/portfolios/address/{self.user_address}",
            headers=self.get_auth_headers(),
        )
        self.assertEqual(
            get_response.status_code,
            404,
            f"Expected 404 after deletion, got {get_response.status_code}: {get_response.text}",
        )


if __name__ == "__main__":
    unittest.main()
