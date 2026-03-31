import unittest
from decimal import Decimal, getcontext
from typing import Any
from unittest.mock import MagicMock, patch

from riskoptimizer.core.exceptions import CalculationError, ValidationError
from riskoptimizer.domain.services.risk_service import RiskService

getcontext().prec = 28


class TestRiskService(unittest.TestCase):

    def setUp(self) -> Any:
        self.risk_service = RiskService()
        self.risk_service.cache = MagicMock()

    def test_validate_returns_valid(self) -> Any:
        self.risk_service._validate_returns([1.0, 2.0, 3.0])
        self.risk_service._validate_returns([Decimal("0.01"), Decimal("0.02")])

    def test_validate_returns_invalid_type(self) -> Any:
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns("not a list")
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns([1, "not a number"])

    def test_validate_returns_too_few_elements(self) -> Any:
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns([1.0])
        with self.assertRaises(ValidationError):
            self.risk_service._validate_returns([])

    def test_validate_confidence_valid(self) -> Any:
        self.risk_service._validate_confidence(0.95)
        self.risk_service._validate_confidence(0.01)
        self.risk_service._validate_confidence(0.999)

    def test_validate_confidence_invalid_type(self) -> Any:
        with self.assertRaises(ValidationError):
            self.risk_service._validate_confidence("not a float")
        with self.assertRaises(ValidationError):
            self.risk_service._validate_confidence(1)
        with self.assertRaises(ValidationError):
            self.risk_service._validate_confidence(0)

    @patch("riskoptimizer.services.quant_analysis.RiskMetrics.calculate_var")
    def test_calculate_var_success(self, mock_calculate_var: Any) -> Any:
        mock_calculate_var.return_value = Decimal("0.02")
        returns = [0.01, 0.02, 0.03]
        confidence = 0.95
        result = self.risk_service.calculate_var(returns, confidence)
        self.assertEqual(result, Decimal("0.02"))
        mock_calculate_var.assert_called_once_with(returns, confidence)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    @patch("riskoptimizer.services.quant_analysis.RiskMetrics.calculate_cvar")
    def test_calculate_cvar_success(self, mock_calculate_cvar: Any) -> Any:
        mock_calculate_cvar.return_value = Decimal("0.03")
        returns = [0.01, 0.02, 0.03]
        confidence = 0.95
        result = self.risk_service.calculate_cvar(returns, confidence)
        self.assertEqual(result, Decimal("0.03"))
        mock_calculate_cvar.assert_called_once_with(returns, confidence)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    @patch("riskoptimizer.services.quant_analysis.RiskMetrics.calculate_sharpe_ratio")
    def test_calculate_sharpe_ratio_success(
        self, mock_calculate_sharpe_ratio: Any
    ) -> Any:
        mock_calculate_sharpe_ratio.return_value = Decimal("1.5")
        returns = [0.01, 0.02, 0.03]
        risk_free_rate = 0.01
        result = self.risk_service.calculate_sharpe_ratio(returns, risk_free_rate)
        self.assertEqual(result, Decimal("1.5"))
        mock_calculate_sharpe_ratio.assert_called_once_with(returns, risk_free_rate)
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    def test_calculate_max_drawdown_success(self) -> Any:
        returns = [0.01, -0.02, 0.03, -0.04, 0.05]
        result = self.risk_service.calculate_max_drawdown(returns)
        self.assertAlmostEqual(
            result, Decimal("-0.0399999999999999999999999999"), places=20
        )
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    @patch("riskoptimizer.domain.services.risk_service.RiskService.calculate_var")
    @patch("riskoptimizer.domain.services.risk_service.RiskService.calculate_cvar")
    @patch(
        "riskoptimizer.domain.services.risk_service.RiskService.calculate_sharpe_ratio"
    )
    @patch(
        "riskoptimizer.domain.services.risk_service.RiskService.calculate_max_drawdown"
    )
    def test_calculate_portfolio_risk_metrics_success(
        self,
        mock_max_drawdown: Any,
        mock_sharpe_ratio: Any,
        mock_cvar: Any,
        mock_var: Any,
    ) -> Any:
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
    @patch("pandas.DataFrame")
    def test_calculate_efficient_frontier_success(
        self,
        mock_dataframe: Any,
        mock_mean_historical_return: Any,
        mock_sample_cov: Any,
        mock_efficient_frontier: Any,
    ) -> Any:
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
        mock_efficient_frontier.return_value = mock_ef_instance
        returns = {"asset1": [0.01, 0.02, 0.03], "asset2": [0.02, 0.03, 0.04]}
        result = self.risk_service.calculate_efficient_frontier(returns)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["type"], "min_volatility")
        self.assertEqual(result[1]["type"], "max_sharpe")
        self.assertEqual(result[0]["expected_return"], Decimal("0.05"))
        self.assertEqual(result[1]["expected_return"], Decimal("0.08"))
        mock_dataframe.assert_called_once_with(returns)
        mock_mean_historical_return.assert_called_once()
        mock_sample_cov.assert_called_once()
        mock_efficient_frontier.assert_called()
        self.risk_service.cache.get.assert_called_once()
        self.risk_service.cache.set.assert_called_once()

    def test_calculate_efficient_frontier_invalid_returns(self) -> Any:
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_efficient_frontier({}, 0.0, 1.0, 0.0, 20)
        with self.assertRaises(ValidationError):
            self.risk_service.calculate_efficient_frontier(
                {"asset1": [0.01]}, 0.0, 1.0, 0.0, 20
            )

    def test_calculate_efficient_frontier_pypfopt_not_installed(self) -> Any:
        with patch.dict("sys.modules", {"pypfopt": None}):
            with self.assertRaises(CalculationError) as cm:
                self.risk_service.calculate_efficient_frontier(
                    {"asset1": [0.01, 0.02], "asset2": [0.03, 0.04]}
                )
            self.assertIn(
                "Required library PyPortfolioOpt not installed", str(cm.exception)
            )


if __name__ == "__main__":
    unittest.main()
