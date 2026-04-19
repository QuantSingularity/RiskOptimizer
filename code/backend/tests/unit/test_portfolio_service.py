import unittest
from datetime import datetime, timezone
from decimal import Decimal, getcontext
from unittest.mock import MagicMock

from src.core.exceptions import NotFoundError, ValidationError
from src.domain.services.portfolio_service import PortfolioService

getcontext().prec = 28


def _now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class TestPortfolioService(unittest.TestCase):

    def setUp(self) -> None:
        self.portfolio_service = PortfolioService()
        self.portfolio_service.portfolio_repo = MagicMock()
        self.portfolio_service.user_repo = MagicMock()
        self.portfolio_service.cache = MagicMock()
        self.portfolio_service.audit_service = MagicMock()
        self.portfolio_service.cache.get.return_value = None
        self.portfolio_service.cache.set.return_value = True
        self.portfolio_service.cache.delete.return_value = True

    def test_get_portfolio_by_address_success(self) -> None:
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
        result = self.portfolio_service.get_portfolio_by_address(user_address)
        self.assertEqual(result["total_value"], Decimal("1000.00"))
        self.portfolio_service.portfolio_repo.get_portfolio_with_allocations.assert_called_once()
        self.portfolio_service.cache.set.assert_called_once()

    def test_get_portfolio_by_address_from_cache(self) -> None:
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

    def test_get_portfolio_by_address_not_found(self) -> None:
        user_address = "non_existent_address"
        self.portfolio_service.portfolio_repo.get_portfolio_with_allocations.side_effect = NotFoundError(
            "Portfolio not found"
        )
        with self.assertRaises(NotFoundError):
            self.portfolio_service.get_portfolio_by_address(user_address)

    def test_save_portfolio_success(self) -> None:
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

    def test_create_portfolio_success(self) -> None:
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
            created_at=_now(),
            updated_at=_now(),
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

    def test_update_portfolio_success(self) -> None:
        portfolio_id = 1
        data = {"name": "Updated Portfolio", "total_value": 2000.0}
        old_portfolio = MagicMock()
        old_portfolio.id = portfolio_id
        old_portfolio.user_id = 1
        old_portfolio.user_address = "test_address"
        old_portfolio.name = "Old Name"
        old_portfolio.description = "Old Description"
        old_portfolio.total_value = Decimal("1000.00")
        old_portfolio.created_at = _now()
        old_portfolio.updated_at = _now()

        updated_portfolio = MagicMock()
        updated_portfolio.id = portfolio_id
        updated_portfolio.user_id = 1
        updated_portfolio.user_address = "test_address"
        updated_portfolio.name = "Updated Portfolio"
        updated_portfolio.description = "Old Description"
        updated_portfolio.total_value = Decimal("2000.00")
        updated_portfolio.created_at = _now()
        updated_portfolio.updated_at = _now()
        self.portfolio_service.portfolio_repo.get_by_id.return_value = old_portfolio
        self.portfolio_service.portfolio_repo.update.return_value = updated_portfolio
        result = self.portfolio_service.update_portfolio(portfolio_id, data)
        self.assertEqual(result["name"], "Updated Portfolio")
        self.assertEqual(result["total_value"], "2000.00")
        self.portfolio_service.portfolio_repo.get_by_id.assert_called_once()
        self.portfolio_service.portfolio_repo.update.assert_called_once()
        self.portfolio_service.cache.delete.assert_called_once()
        self.portfolio_service.audit_service.log_action.assert_called_once()

    def test_delete_portfolio_success(self) -> None:
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

    def test_get_user_portfolios_success(self) -> None:
        user_id = 1
        mock_portfolios = [
            MagicMock(
                id=1,
                user_id=user_id,
                user_address="addr1",
                name="P1",
                description="D1",
                total_value=Decimal("100"),
                created_at=_now(),
                updated_at=_now(),
            ),
            MagicMock(
                id=2,
                user_id=user_id,
                user_address="addr2",
                name="P2",
                description="D2",
                total_value=Decimal("200"),
                created_at=_now(),
                updated_at=_now(),
            ),
        ]
        self.portfolio_service.portfolio_repo.get_by_user_id.return_value = (
            mock_portfolios
        )
        result = self.portfolio_service.get_user_portfolios(user_id)
        self.assertEqual(len(result), 2)
        self.portfolio_service.portfolio_repo.get_by_user_id.assert_called_once()

    def test_validate_portfolio_input_valid(self) -> None:
        user_address = "test_address"
        allocations = {"BTC": 50.0, "ETH": 50.0}
        name = "Valid Portfolio"
        self.portfolio_service._validate_portfolio_input(
            user_address, allocations, name
        )

    def test_validate_portfolio_input_invalid_address(self) -> None:
        with self.assertRaises(ValidationError):
            self.portfolio_service._validate_portfolio_input(
                None, {"BTC": 100.0}, "Name"
            )

    def test_validate_portfolio_input_invalid_allocations(self) -> None:
        with self.assertRaises(ValidationError):
            self.portfolio_service._validate_portfolio_input("address", {}, "Name")
        with self.assertRaises(ValidationError):
            self.portfolio_service._validate_portfolio_input(
                "address", {"BTC": 120.0}, "Name"
            )

    def test_normalize_allocations(self) -> None:
        allocations = {"BTC": 25.0, "ETH": 25.0, "ADA": 50.0}
        normalized = self.portfolio_service._normalize_allocations(allocations)
        self.assertAlmostEqual(sum(normalized.values()), 100.0, places=5)
        self.assertAlmostEqual(normalized["BTC"], 25.0, places=5)

    def test_get_portfolio_by_address_invalid_input(self) -> None:
        with self.assertRaises(ValidationError):
            self.portfolio_service.get_portfolio_by_address("")
        with self.assertRaises(ValidationError):
            self.portfolio_service.get_portfolio_by_address(None)

    def test_create_portfolio_user_not_found(self) -> None:
        self.portfolio_service.user_repo.get_by_id.return_value = None
        with self.assertRaises(NotFoundError):
            self.portfolio_service.create_portfolio(1, "address", "name")

    def test_update_portfolio_not_found(self) -> None:
        self.portfolio_service.portfolio_repo.get_by_id.return_value = None
        with self.assertRaises(NotFoundError):
            self.portfolio_service.update_portfolio(999, {"name": "x"})

    def test_update_portfolio_invalid_field(self) -> None:
        old_portfolio = MagicMock()
        self.portfolio_service.portfolio_repo.get_by_id.return_value = old_portfolio
        with self.assertRaises(ValidationError):
            self.portfolio_service.update_portfolio(1, {"invalid_field": "value"})

    def test_normalize_allocations_zero_total(self) -> None:
        with self.assertRaises(ValidationError):
            self.portfolio_service._normalize_allocations({"BTC": 0.0, "ETH": 0.0})


if __name__ == "__main__":
    unittest.main()
