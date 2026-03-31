import unittest
from datetime import datetime
from decimal import Decimal, getcontext
from typing import Any
from unittest.mock import MagicMock

from riskoptimizer.core.exceptions import NotFoundError, ValidationError
from riskoptimizer.domain.services.portfolio_service import PortfolioService

getcontext().prec = 28


class TestPortfolioService(unittest.TestCase):

    def setUp(self) -> Any:
        self.portfolio_service = PortfolioService()
        self.portfolio_service.portfolio_repo = MagicMock()
        self.portfolio_service.user_repo = MagicMock()
        self.portfolio_service.cache = MagicMock()
        self.portfolio_service.audit_service = MagicMock()

    def test_get_portfolio_by_address_success(self) -> Any:
        user_address = "test_address"
        mock_portfolio_data = {
            "total_value": Decimal("1000.00"),
            "allocations": [
                {
                    "percentage": Decimal("50.0"),
                    "amount": Decimal("500.0"),
                    "current_price": Decimal("10.0"),
                }
            ],
        }
        self.portfolio_service.portfolio_repo.get_portfolio_with_allocations.return_value = (
            mock_portfolio_data
        )
        self.portfolio_service.cache.get.return_value = None
        result = self.portfolio_service.get_portfolio_by_address(user_address)
        self.assertEqual(result["total_value"], Decimal("1000.00"))
        self.portfolio_service.portfolio_repo.get_portfolio_with_allocations.assert_called_once()
        self.portfolio_service.cache.set.assert_called_once()

    def test_get_portfolio_by_address_from_cache(self) -> Any:
        user_address = "test_address"
        cached_portfolio_data = {
            "total_value": "1000.00",
            "allocations": [
                {"percentage": "50.0", "amount": "500.0", "current_price": "10.0"}
            ],
        }
        self.portfolio_service.cache.get.return_value = cached_portfolio_data
        result = self.portfolio_service.get_portfolio_by_address(user_address)
        self.assertEqual(result["total_value"], Decimal("1000.00"))
        self.portfolio_service.portfolio_repo.get_portfolio_with_allocations.assert_not_called()

    def test_get_portfolio_by_address_not_found(self) -> Any:
        user_address = "non_existent_address"
        self.portfolio_service.portfolio_repo.get_portfolio_with_allocations.side_effect = NotFoundError(
            "Portfolio not found"
        )
        self.portfolio_service.cache.get.return_value = None
        with self.assertRaises(NotFoundError):
            self.portfolio_service.get_portfolio_by_address(user_address)

    def test_save_portfolio_success(self) -> Any:
        user_address = "test_address"
        allocations = {"BTC": 50.0, "ETH": 50.0}
        name = "My Portfolio"
        mock_portfolio_data = {
            "portfolio_id": 1,
            "user_address": user_address,
            "name": name,
        }
        mock_user = MagicMock(id=1)
        self.portfolio_service.portfolio_repo.save_portfolio_with_allocations.return_value = (
            mock_portfolio_data
        )
        self.portfolio_service.user_repo.get_by_wallet_address.return_value = mock_user
        result = self.portfolio_service.save_portfolio(user_address, allocations, name)
        self.assertEqual(result, mock_portfolio_data)
        self.portfolio_service.portfolio_repo.save_portfolio_with_allocations.assert_called_once()
        self.portfolio_service.audit_service.log_action.assert_called_once()
        self.portfolio_service.cache.delete.assert_called_once()

    def test_create_portfolio_success(self) -> Any:
        user_id = 1
        user_address = "new_address"
        name = "New Portfolio"
        description = "A new test portfolio"
        mock_user = MagicMock(id=user_id)
        mock_portfolio = MagicMock(
            id=1,
            user_id=user_id,
            user_address=user_address,
            name=name,
            description=description,
            total_value=Decimal("0.00"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.portfolio_service.user_repo.get_by_id.return_value = mock_user
        self.portfolio_service.portfolio_repo.create.return_value = mock_portfolio
        result = self.portfolio_service.create_portfolio(
            user_id, user_address, name, description
        )
        self.assertEqual(result["id"], 1)
        self.portfolio_service.user_repo.get_by_id.assert_called_once()
        self.portfolio_service.portfolio_repo.create.assert_called_once()
        self.portfolio_service.audit_service.log_action.assert_called_once()

    def test_update_portfolio_success(self) -> Any:
        portfolio_id = 1
        data = {"name": "Updated Portfolio", "total_value": 2000.0}
        old_portfolio = MagicMock(
            id=portfolio_id,
            user_id=1,
            user_address="test_address",
            name="Old Name",
            description="Old Description",
            total_value=Decimal("1000.00"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        updated_portfolio = MagicMock(
            id=portfolio_id,
            user_id=1,
            user_address="test_address",
            name="Updated Portfolio",
            description="Old Description",
            total_value=Decimal("2000.00"),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.portfolio_service.portfolio_repo.get_by_id.return_value = old_portfolio
        self.portfolio_service.portfolio_repo.update.return_value = updated_portfolio
        result = self.portfolio_service.update_portfolio(portfolio_id, data)
        self.assertEqual(result["name"], "Updated Portfolio")
        self.assertEqual(result["total_value"], "2000.00")
        self.portfolio_service.portfolio_repo.get_by_id.assert_called_once()
        self.portfolio_service.portfolio_repo.update.assert_called_once()
        self.portfolio_service.cache.delete.assert_called_once()
        self.portfolio_service.audit_service.log_action.assert_called_once()

    def test_delete_portfolio_success(self) -> Any:
        portfolio_id = 1
        mock_portfolio = MagicMock(
            id=portfolio_id,
            user_id=1,
            user_address="test_address",
            name="Test Portfolio",
        )
        self.portfolio_service.portfolio_repo.get_by_id.return_value = mock_portfolio
        self.portfolio_service.portfolio_repo.delete.return_value = True
        result = self.portfolio_service.delete_portfolio(portfolio_id)
        self.assertTrue(result)
        self.portfolio_service.portfolio_repo.get_by_id.assert_called_once()
        self.portfolio_service.portfolio_repo.delete.assert_called_once()
        self.portfolio_service.cache.delete.assert_called_once()
        self.portfolio_service.audit_service.log_action.assert_called_once()

    def test_get_user_portfolios_success(self) -> Any:
        user_id = 1
        mock_portfolios = [
            MagicMock(
                id=1,
                user_id=user_id,
                user_address="addr1",
                name="P1",
                description="D1",
                total_value=Decimal("100"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
            MagicMock(
                id=2,
                user_id=user_id,
                user_address="addr2",
                name="P2",
                description="D2",
                total_value=Decimal("200"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            ),
        ]
        self.portfolio_service.portfolio_repo.get_by_user_id.return_value = (
            mock_portfolios
        )
        result = self.portfolio_service.get_user_portfolios(user_id)
        self.assertEqual(len(result), 2)
        self.portfolio_service.portfolio_repo.get_by_user_id.assert_called_once()

    def test_validate_portfolio_input_valid(self) -> Any:
        user_address = "test_address"
        allocations = {"BTC": 50.0, "ETH": 50.0}
        name = "Valid Portfolio"
        self.portfolio_service._validate_portfolio_input(
            user_address, allocations, name
        )

    def test_validate_portfolio_input_invalid_address(self) -> Any:
        with self.assertRaises(ValidationError):
            self.portfolio_service._validate_portfolio_input(
                None, {"BTC": 100.0}, "Name"
            )

    def test_validate_portfolio_input_invalid_allocations(self) -> Any:
        with self.assertRaises(ValidationError):
            self.portfolio_service._validate_portfolio_input("address", {}, "Name")
        with self.assertRaises(ValidationError):
            self.portfolio_service._validate_portfolio_input(
                "address", {"BTC": 120.0}, "Name"
            )

    def test_normalize_allocations(self) -> Any:
        allocations = {"BTC": 25.0, "ETH": 25.0, "ADA": 50.0}
        normalized = self.portfolio_service._normalize_allocations(allocations)
        self.assertAlmostEqual(sum(normalized.values()), Decimal("100.0"))
        self.assertAlmostEqual(normalized["BTC"], Decimal("25.0"))


if __name__ == "__main__":
    unittest.main()
