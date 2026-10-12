from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from src.core.exceptions import NotFoundError
from src.domain.services.portfolio_service import PortfolioService

TOKEN = {"Authorization": "Bearer test-token"}
BASE = "/api/v1/portfolios"


@pytest.fixture
def client(make_client):
    return make_client("user")


class TestRoutes:
    def test_requires_authentication(self, client):
        assert client.get(BASE).status_code == 401
        assert client.get(f"{BASE}/1").status_code == 401

    def test_list_is_scoped_to_the_authenticated_user(self, client):
        rows = [
            {
                "id": 3,
                "name": "Growth",
                "description": "d",
                "total_value": "1500.50",
                "created_at": "2024-01-01",
                "updated_at": "2024-01-02",
            },
        ]
        with patch(
            "src.domain.services.portfolio_service.portfolio_service.get_user_portfolios",
            return_value=rows,
        ) as service:
            response = client.get(BASE, headers=TOKEN)
        service.assert_called_once_with(1)
        item = response.get_json()["data"]["portfolios"][0]
        assert response.status_code == 200
        assert (
            item["total_value"] == 1500.5
            and item["currency"] == "USD"
            and item["risk_score"] is None
        )

    def test_detail_returns_assets(self, client):
        details = {
            "id": 3,
            "name": "Growth",
            "assets": [{"symbol": "AAPL"}],
            "risk_score": 0.21,
        }
        with patch(
            "src.domain.services.portfolio_service.portfolio_service.get_portfolio_details",
            return_value=details,
        ) as service:
            response = client.get(f"{BASE}/3", headers=TOKEN)
        service.assert_called_once_with(3, 1)
        assert (
            response.status_code == 200
            and response.get_json()["data"]["assets"][0]["symbol"] == "AAPL"
        )

    def test_missing_or_foreign_portfolio_is_404(self, client):
        with patch(
            "src.domain.services.portfolio_service.portfolio_service.get_portfolio_details",
            side_effect=NotFoundError("Portfolio not found", "portfolio", 9),
        ):
            response = client.get(f"{BASE}/9", headers=TOKEN)
        assert response.status_code == 404 and response.get_json()["status"] == "error"

    def test_non_integer_id_is_not_routed(self, client):
        assert client.get(f"{BASE}/abc", headers=TOKEN).status_code in (404, 405)


class TestServiceDetails:
    def make_portfolio(self, owner=1):
        allocations = [
            MagicMock(
                id=1,
                asset_symbol="AAPL",
                asset_name="Apple",
                percentage=60,
                amount=6000,
                current_price=150,
            ),
            MagicMock(
                id=2,
                asset_symbol="MSFT",
                asset_name=None,
                percentage=40,
                amount=None,
                current_price=None,
            ),
        ]
        return MagicMock(
            id=5,
            user_id=owner,
            name="P",
            description="d",
            total_value=10000,
            allocations=allocations,
            created_at=datetime(2024, 1, 1),
            updated_at=datetime(2024, 1, 2),
        )

    def service(self, portfolio):
        service = PortfolioService()
        service.portfolio_repo = MagicMock()
        service.portfolio_repo.get_by_id.return_value = portfolio
        return service

    def run(self, portfolio, user_id=1, volatility=0.25):
        with patch(
            "src.domain.services.portfolio_service.get_db_session"
        ) as session, patch.object(
            PortfolioService, "annualized_volatility", return_value=volatility
        ):
            session.return_value.__enter__.return_value = MagicMock()
            return self.service(portfolio).get_portfolio_details(5, user_id)

    def test_assets_and_values(self):
        details = self.run(self.make_portfolio())
        first, second = details["assets"]
        assert (
            first["value"] == 6000
            and first["quantity"] == pytest.approx(40)
            and first["allocation_percentage"] == 60
        )
        assert (
            second["value"] == pytest.approx(4000)
            and second["quantity"] is None
            and second["name"] == "MSFT"
        )
        assert (
            details["total_value"] == 10000
            and details["risk_score"] == 0.25
            and details["currency"] == "USD"
        )

    def test_other_users_portfolio_looks_like_not_found(self):
        with pytest.raises(NotFoundError):
            self.run(self.make_portfolio(owner=2), user_id=1)
        with pytest.raises(NotFoundError):
            self.run(None)

    def test_type_validation(self):
        from src.core.exceptions import ValidationError

        with pytest.raises(ValidationError):
            self.service(None).get_portfolio_details("5", 1)

    def test_risk_score_degrades_to_none(self):
        with patch(
            "src.tasks.quant_adapter.load_portfolio_returns",
            side_effect=ValueError("no data"),
        ):
            assert PortfolioService.annualized_volatility(5) is None
        import pandas as pd

        with patch(
            "src.tasks.quant_adapter.load_portfolio_returns",
            return_value=pd.Series([0.01, -0.01] * 30),
        ):
            assert PortfolioService.annualized_volatility(5) == pytest.approx(
                0.01 * (252**0.5) * (60 / 59) ** 0.5
            )
