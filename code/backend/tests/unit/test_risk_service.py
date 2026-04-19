import unittest
from decimal import Decimal, getcontext
from unittest.mock import MagicMock, patch

from src.core.exceptions import CalculationError, ValidationError
from src.domain.services.risk_service import RiskService

getcontext().prec = 28


class TestRiskService(unittest.TestCase):

    def setUp(self) -> None:
        self.risk_service = RiskService()
        self.risk_service.cache = MagicMock()
        self.risk_service.cache.get.return_value = None
        self.risk_service.cache.set.return_value = True
        self.risk_service.cache.exists.return_value = False

    def test_validate_returns_valid(self) -> None:
        self.risk_service._validate_returns([1.0, 2.0, 3.0])
        self.risk_service._validate_returns([Decimal("0.01"), Decimal("0.02")])

    def test_validate_returns_invalid_type(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns("not a list")
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns([1, "not a number"])

    def test_validate_returns_too_few_elements(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns([1.0])
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns([])

    def test_validate_confidence_valid(self) -> None:
        self.risk_service._validate_confidence(0.95)
        self.risk_service._validate_confidence(0.01)
        self.risk_service._validate_confidence(0.999)

    def test_validate_confidence_invalid_type(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service._validate_confidence("not a float")
        with self.assertRaises(ValidationError):
            self.risk_service._validate_confidence(1)
        with self.assertRaises(ValidationError):
            self.risk_service._validate_confidence(0)

    @patch("src.services.quant_analysis.RiskMetrics.calculate_var")
    def test_calculate_var_success(self, mock_calculate_var: "MagicMock") -> None:
        mock_calculate_var.return_value = Decimal("0.02")
        returns = [0.01, 0.02, 0.03]
        confidence = 0.95
        result = self.risk_service.calculate_var(returns, confidence)
        self.assertEqual(result, Decimal("0.02"))
        mock_calculate_var.assert_called_once_with(returns, confidence)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    @patch("src.services.quant_analysis.RiskMetrics.calculate_cvar")
    def test_calculate_cvar_success(self, mock_calculate_cvar: "MagicMock") -> None:
        mock_calculate_cvar.return_value = Decimal("0.03")
        returns = [0.01, 0.02, 0.03]
        confidence = 0.95
        result = self.risk_service.calculate_cvar(returns, confidence)
        self.assertEqual(result, Decimal("0.03"))
        mock_calculate_cvar.assert_called_once_with(returns, confidence)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    @patch("src.services.quant_analysis.RiskMetrics.calculate_sharpe_ratio")
    def test_calculate_sharpe_ratio_success(
        self, mock_calculate_sharpe_ratio: "MagicMock"
    ) -> object:
        mock_calculate_sharpe_ratio.return_value = Decimal("1.5")
        returns = [0.01, 0.02, 0.03]
        risk_free_rate = 0.01
        result = self.risk_service.calculate_sharpe_ratio(returns, risk_free_rate)
        self.assertEqual(result, Decimal("1.5"))
        mock_calculate_sharpe_ratio.assert_called_once_with(returns, risk_free_rate)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    def test_calculate_max_drawdown_success(self) -> None:
        returns = [0.01, -0.02, 0.03, -0.04, 0.05]
        result = self.risk_service.calculate_max_drawdown(returns)
        self.assertLess(result, Decimal("0"), "Max drawdown should be negative")
        self.assertAlmostEqual(float(result), -0.04, places=2)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    @patch("src.domain.services.risk_service.RiskService.calculate_var")
    @patch("src.domain.services.risk_service.RiskService.calculate_cvar")
    @patch("src.domain.services.risk_service.RiskService.calculate_sharpe_ratio")
    @patch("src.domain.services.risk_service.RiskService.calculate_max_drawdown")
    def test_calculate_portfolio_risk_metrics_success(
        self,
        mock_max_drawdown: "MagicMock",
        mock_sharpe_ratio: "MagicMock",
        mock_cvar: "MagicMock",
        mock_var: "MagicMock",
    ) -> object:
        mock_var.return_value = Decimal("0.02")
        mock_cvar.return_value = Decimal("0.03")
        mock_sharpe_ratio.return_value = Decimal("1.5")
        mock_max_drawdown.return_value = Decimal("-0.04")
        returns = [0.01, 0.02, 0.03]
        confidence = 0.95
        risk_free_rate = 0.01
        metrics = self.risk_service.calculate_portfolio_risk_metrics(
            returns, confidence, risk_free_rate
        )
        self.assertIn("expected_return", metrics)
        self.assertIn("volatility", metrics)
        self.assertIn("value_at_risk", metrics)
        self.assertIn("conditional_var", metrics)
        self.assertIn("sharpe_ratio", metrics)
        self.assertIn("max_drawdown", metrics)
        self.assertEqual(metrics["value_at_risk"], Decimal("0.02"))
        self.assertEqual(metrics["conditional_var"], Decimal("0.03"))
        self.assertEqual(metrics["sharpe_ratio"], Decimal("1.5"))
        self.assertEqual(metrics["max_drawdown"], Decimal("-0.04"))
        mock_var.assert_called_once_with(returns, confidence)
        mock_cvar.assert_called_once_with(returns, confidence)
        mock_sharpe_ratio.assert_called_once_with(returns, risk_free_rate)
        mock_max_drawdown.assert_called_once_with(returns)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    @patch("pypfopt.EfficientFrontier")
    @patch("pypfopt.risk_models.sample_cov")
    @patch("pypfopt.expected_returns.mean_historical_return")
    def test_calculate_efficient_frontier_success(
        self,
        mock_mean_historical_return: "MagicMock",
        mock_sample_cov: "MagicMock",
        mock_ef_cls: "MagicMock",
    ) -> object:
        mock_mean_historical_return.return_value = MagicMock()
        mock_sample_cov.return_value = MagicMock()
        mock_ef_instance = MagicMock()
        mock_ef_instance.clean_weights.side_effect = [
            {"asset1": 0.6, "asset2": 0.4},
            {"asset1": 0.7, "asset2": 0.3},
        ]
        mock_ef_instance.portfolio_performance.side_effect = [
            (0.05, 0.1, 0.5),
            (0.08, 0.12, 0.6),
        ]
        mock_ef_cls.return_value = mock_ef_instance
        returns = {"asset1": [0.01, 0.02, 0.03], "asset2": [0.02, 0.03, 0.04]}
        result = self.risk_service.calculate_efficient_frontier(returns)
        self.assertGreaterEqual(len(result), 2)
        types = [p["type"] for p in result]
        self.assertIn("min_volatility", types)
        self.assertIn("max_sharpe", types)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    def test_calculate_efficient_frontier_invalid_returns(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_efficient_frontier({}, 0.0, 1.0, 0.0, 20)
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_efficient_frontier(
                {"asset1": [0.01]}, 0.0, 1.0, 0.0, 20
            )

    def test_calculate_efficient_frontier_pypfopt_not_installed(self) -> None:
        with patch.dict("sys.modules", {"pypfopt": None}):
            with self.assertRaises(CalculationError) as cm:
                self.risk_service.calculate_efficient_frontier(
                    {"asset1": [0.01, 0.02], "asset2": [0.03, 0.04]}
                )
            self.assertIn(
                "Required library PyPortfolioOpt not installed", str(cm.exception)
            )

    def test_calculate_var_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_var([], 0.95)
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_var([0.01, 0.02], 1.5)

    def test_calculate_cvar_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_cvar([], 0.95)

    def test_calculate_sharpe_ratio_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_sharpe_ratio([0.01], 0.0)

    def test_calculate_max_drawdown_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_max_drawdown([0.01])

    def test_calculate_portfolio_risk_metrics_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_portfolio_risk_metrics([], 0.95)
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_portfolio_risk_metrics([0.01, 0.02], 1.5)


if __name__ == "__main__":
    unittest.main()
