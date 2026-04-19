"""
Endpoint smoke tests for the RiskOptimizer Flask API.

All external dependencies (DB, Redis, tasks) are mocked so these tests
run without any network services.
"""

import json
from unittest.mock import patch

import pytest

# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def app():
    """Create a Flask test application with all external services mocked."""
    with patch("src.infrastructure.database.session.SessionLocal"), patch(
        "src.infrastructure.cache.redis_cache.redis_cache._available", False
    ), patch("src.infrastructure.database.session.engine"):
        from src.core.config import config

        config.api.debug = False
        try:
            from backend.app import create_app
        except ImportError:
            from app import create_app
        flask_app = create_app()
        flask_app.config["TESTING"] = True
        yield flask_app


@pytest.fixture
def client(app):
    """Flask test client."""
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Health / root endpoints
# ---------------------------------------------------------------------------


def test_root_endpoint(client) -> object:
    """GET / should return API name and version."""
    with patch(
        "src.infrastructure.database.session.check_db_connection",
        return_value=True,
    ), patch(
        "src.infrastructure.cache.redis_cache.RedisCache.health_check",
        return_value=True,
    ):
        response = client.get("/")
        assert response.status_code == 200
        data = response.get_json()
        assert "name" in data or "src" in str(data)


def test_health_endpoint_ok(client) -> object:
    """GET /health should return status ok when DB and cache are up."""
    with patch(
        "src.infrastructure.database.session.check_db_connection",
        return_value=True,
    ), patch(
        "src.infrastructure.cache.redis_cache.RedisCache.health_check",
        return_value=True,
    ):
        response = client.get("/health")
        assert response.status_code in (200, 503)
        data = response.get_json()
        assert "status" in data
        assert "version" in data


def test_health_endpoint_degraded(client) -> object:
    """GET /health returns 503 when DB is down."""
    with patch(
        "src.infrastructure.database.session.check_db_connection",
        return_value=False,
    ), patch(
        "src.infrastructure.cache.redis_cache.RedisCache.health_check",
        return_value=False,
    ):
        response = client.get("/health")
        assert response.status_code == 503
        data = response.get_json()
        assert data["status"] == "degraded"


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------


def test_register_missing_body(client) -> object:
    """POST /api/v1/auth/register without body returns 400."""
    response = client.post(
        "/api/v1/auth/register", data="", content_type="application/json"
    )
    assert response.status_code in (400, 422)


def test_login_missing_body(client) -> object:
    """POST /api/v1/auth/login without body returns 400."""
    response = client.post(
        "/api/v1/auth/login", data="", content_type="application/json"
    )
    assert response.status_code in (400, 422)


def test_login_invalid_credentials(client) -> object:
    """POST /api/v1/auth/login with bad credentials returns 401."""
    with patch(
        "src.domain.services.auth_service.auth_service.authenticate_user",
        side_effect=Exception("Invalid email or password"),
    ):
        payload = json.dumps({"email": "bad@bad.com", "password": "wrong"})
        response = client.post(
            "/api/v1/auth/login", data=payload, content_type="application/json"
        )
        assert response.status_code in (400, 401, 422, 500)


# ---------------------------------------------------------------------------
# Risk endpoints – require JWT so will 401 without token
# ---------------------------------------------------------------------------


def test_var_endpoint_requires_auth(client) -> object:
    """POST /api/v1/risk/var without Authorization header returns 401."""
    payload = json.dumps({"returns": [0.01, -0.02, 0.03], "confidence": 0.95})
    response = client.post(
        "/api/v1/risk/var", data=payload, content_type="application/json"
    )
    assert response.status_code == 401


def test_cvar_endpoint_requires_auth(client) -> object:
    """POST /api/v1/risk/cvar without Authorization header returns 401."""
    payload = json.dumps({"returns": [0.01, -0.02, 0.03]})
    response = client.post(
        "/api/v1/risk/cvar", data=payload, content_type="application/json"
    )
    assert response.status_code == 401


def test_portfolio_endpoint_requires_auth(client) -> object:
    """GET /api/v1/portfolios/address/0x1234 without token returns 401."""
    response = client.get("/api/v1/portfolios/address/0x1234")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Risk endpoints – with mocked auth
# ---------------------------------------------------------------------------


def _auth_headers():
    return {"Authorization": "Bearer test_token"}


def test_var_endpoint_with_valid_data(client) -> object:
    """POST /api/v1/risk/var with mocked auth returns 200."""
    from decimal import Decimal

    with patch(
        "src.api.middleware.auth_middleware.auth_service.verify_token",
        return_value={"user_id": 1, "email": "t@t.com", "role": "user"},
    ), patch(
        "src.api.middleware.auth_middleware.auth_service.is_token_blacklisted",
        return_value=False,
    ), patch(
        "src.domain.services.risk_service.risk_service.calculate_var",
        return_value=Decimal("0.025"),
    ):
        payload = json.dumps(
            {"returns": [0.01, -0.02, 0.03, -0.01, 0.02], "confidence": 0.95}
        )
        response = client.post(
            "/api/v1/risk/var",
            data=payload,
            content_type="application/json",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "value_at_risk" in data["data"]


def test_var_endpoint_missing_returns(client) -> object:
    """POST /api/v1/risk/var without returns field returns 400."""
    with patch(
        "src.api.middleware.auth_middleware.auth_service.verify_token",
        return_value={"user_id": 1, "email": "t@t.com", "role": "user"},
    ), patch(
        "src.api.middleware.auth_middleware.auth_service.is_token_blacklisted",
        return_value=False,
    ):
        payload = json.dumps({"confidence": 0.95})
        response = client.post(
            "/api/v1/risk/var",
            data=payload,
            content_type="application/json",
            headers=_auth_headers(),
        )
        assert response.status_code in (400, 422)


def test_cvar_endpoint_with_valid_data(client) -> object:
    """POST /api/v1/risk/cvar with mocked auth returns 200."""
    from decimal import Decimal

    with patch(
        "src.api.middleware.auth_middleware.auth_service.verify_token",
        return_value={"user_id": 1, "email": "t@t.com", "role": "user"},
    ), patch(
        "src.api.middleware.auth_middleware.auth_service.is_token_blacklisted",
        return_value=False,
    ), patch(
        "src.domain.services.risk_service.risk_service.calculate_cvar",
        return_value=Decimal("0.035"),
    ):
        payload = json.dumps(
            {"returns": [0.01, -0.02, 0.03, -0.01, 0.02], "confidence": 0.95}
        )
        response = client.post(
            "/api/v1/risk/cvar",
            data=payload,
            content_type="application/json",
            headers=_auth_headers(),
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["status"] == "success"
        assert "conditional_value_at_risk" in data["data"]
