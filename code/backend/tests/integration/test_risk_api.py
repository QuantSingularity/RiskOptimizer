"""
Integration tests for Risk API.

Uses Flask's built-in test client and mocks all external dependencies
so no live server or database is required.
"""

import logging
import unittest
from decimal import Decimal
from unittest.mock import MagicMock, patch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

SAMPLE_RETURNS = [0.01, 0.02, -0.03, 0.04, -0.05]


def _infra_patches():
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


class TestRiskAPI(unittest.TestCase):

    def setUp(self):
        self._patches = _infra_patches()
        self.app, self.client = _make_test_client(self._patches)
        self.access_token = "mock_access_token"

        # Mock JWT verify_token to always pass (patching at the verification level
        # since the @jwt_required() decorator is already bound at import time)
        self._jwt_patch = patch(
            "src.domain.services.auth_service.auth_service.verify_token",
            return_value={"user_id": 1, "email": "test@example.com", "role": "user"},
        )
        self._jwt_patch.start()
        self._patches.append(self._jwt_patch)

    def tearDown(self):
        for p in self._patches:
            try:
                p.stop()
            except RuntimeError:
                pass

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.access_token}"}

    # ------------------------------------------------------------------
    # tests
    # ------------------------------------------------------------------

    def test_1_calculate_var(self):
        """POST /risk/var → 200 with value_at_risk field."""
        with patch(
            "src.domain.services.risk_service.risk_service.calculate_var",
            return_value=Decimal("0.045"),
        ):
            response = self.client.post(
                "/api/v1/risk/var",
                json={"returns": SAMPLE_RETURNS, "confidence": 0.95},
                headers=self._auth_headers(),
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        self.assertIn("value_at_risk", payload)
        self.assertIsInstance(float(payload["value_at_risk"]), float)

    def test_2_calculate_cvar(self):
        """POST /risk/cvar → 200 with conditional_value_at_risk field."""
        with patch(
            "src.domain.services.risk_service.risk_service.calculate_cvar",
            return_value=Decimal("0.055"),
        ):
            response = self.client.post(
                "/api/v1/risk/cvar",
                json={"returns": SAMPLE_RETURNS, "confidence": 0.95},
                headers=self._auth_headers(),
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        self.assertIn("conditional_value_at_risk", payload)
        self.assertIsInstance(float(payload["conditional_value_at_risk"]), float)

    def test_3_calculate_sharpe_ratio(self):
        """POST /risk/sharpe-ratio → 200 with sharpe_ratio field."""
        with patch(
            "src.domain.services.risk_service.risk_service.calculate_sharpe_ratio",
            return_value=Decimal("1.23"),
        ):
            response = self.client.post(
                "/api/v1/risk/sharpe-ratio",
                json={
                    "returns": [0.01, 0.02, 0.03, 0.04, 0.05],
                    "risk_free_rate": 0.01,
                },
                headers=self._auth_headers(),
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        self.assertIn("sharpe_ratio", payload)
        self.assertIsInstance(float(payload["sharpe_ratio"]), float)

    def test_4_calculate_max_drawdown(self):
        """POST /risk/max-drawdown → 200 with max_drawdown field."""
        with patch(
            "src.domain.services.risk_service.risk_service.calculate_max_drawdown",
            return_value=Decimal("0.04"),
        ):
            response = self.client.post(
                "/api/v1/risk/max-drawdown",
                json={"returns": [0.01, -0.02, 0.03, -0.04, 0.05]},
                headers=self._auth_headers(),
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        self.assertIn("max_drawdown", payload)
        self.assertIsInstance(float(payload["max_drawdown"]), float)

    def test_5_calculate_portfolio_risk_metrics(self):
        """POST /risk/portfolio-metrics → 200 with full metrics bundle."""
        mock_metrics = {
            "expected_return": Decimal("0.006"),
            "volatility": Decimal("0.03"),
            "value_at_risk": Decimal("0.045"),
            "conditional_var": Decimal("0.055"),
            "sharpe_ratio": Decimal("1.2"),
            "max_drawdown": Decimal("0.02"),
        }
        with patch(
            "src.domain.services.risk_service.risk_service.calculate_portfolio_risk_metrics",
            return_value=mock_metrics,
        ):
            response = self.client.post(
                "/api/v1/risk/portfolio-metrics",
                json={
                    "returns": SAMPLE_RETURNS,
                    "confidence": 0.95,
                    "risk_free_rate": 0.01,
                },
                headers=self._auth_headers(),
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        payload = response.get_json().get("data", response.get_json())
        for field in [
            "expected_return",
            "volatility",
            "value_at_risk",
            "conditional_var",
            "sharpe_ratio",
            "max_drawdown",
        ]:
            self.assertIn(field, payload, f"Missing field: {field}")
        self.assertIsInstance(float(payload["expected_return"]), float)

    def test_6_calculate_efficient_frontier(self):
        """POST /risk/efficient-frontier → 200 with list of frontier points."""
        frontier_points = [
            {
                "expected_return": 0.05 + i * 0.01,
                "volatility": 0.10 + i * 0.005,
                "sharpe_ratio": 0.8 + i * 0.02,
                "weights": {"asset1": 0.6, "asset2": 0.4},
            }
            for i in range(10)
        ]
        with patch(
            "src.domain.services.risk_service.risk_service.calculate_efficient_frontier",
            return_value=frontier_points,
        ):
            response = self.client.post(
                "/api/v1/risk/efficient-frontier",
                json={
                    "returns": {
                        "asset1": [0.01, 0.02, 0.03, 0.04, 0.05],
                        "asset2": [0.005, 0.015, 0.025, 0.035, 0.045],
                    },
                    "min_weight": 0.1,
                    "max_weight": 0.9,
                    "risk_free_rate": 0.01,
                    "points": 10,
                },
                headers=self._auth_headers(),
            )
        self.assertEqual(
            response.status_code,
            200,
            f"Expected 200, got {response.status_code}: {response.data}",
        )
        data = response.get_json().get("data", response.get_json())
        result = data if isinstance(data, list) else data.get("items", [data])
        self.assertGreater(len(result), 0)
        self.assertIn("expected_return", result[0])
        self.assertIn("volatility", result[0])
        self.assertIn("sharpe_ratio", result[0])
        self.assertIn("weights", result[0])


if __name__ == "__main__":
    unittest.main()
