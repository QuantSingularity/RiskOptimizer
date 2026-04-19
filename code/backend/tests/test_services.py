from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from src.services.quant_analysis import RiskMetrics


def test_calculate_var() -> object:
    """Test the Value at Risk calculation returns a positive Decimal."""
    returns = [0.01, -0.02, 0.03, -0.01, 0.02, 0.005, -0.005]
    var_95 = RiskMetrics.calculate_var(returns, confidence=0.95)
    var_99 = RiskMetrics.calculate_var(returns, confidence=0.99)
    # VaR should be positive (represents magnitude of loss)
    assert float(var_95) > 0, "VaR at 95% should be positive"
    assert float(var_99) > float(var_95), "VaR at 99% should be larger than at 95%"


def test_calculate_var_empty_returns() -> object:
    """Test VaR calculation with empty returns raises ValueError."""
    with pytest.raises(ValueError):
        RiskMetrics.calculate_var([])


def test_calculate_cvar_gt_var() -> object:
    """Test CVaR is always >= VaR."""
    returns = [0.01, -0.02, 0.03, -0.04, 0.02, 0.005, -0.005, -0.03, 0.01, -0.015]
    var = RiskMetrics.calculate_var(returns, confidence=0.95)
    cvar = RiskMetrics.calculate_cvar(returns, confidence=0.95)
    assert float(cvar) >= float(var), "CVaR should be >= VaR"


def test_calculate_sharpe_ratio() -> object:
    """Test Sharpe ratio calculation returns a numeric value."""
    returns = [0.01, 0.02, -0.005, 0.015, -0.01, 0.008, 0.012]
    sharpe = RiskMetrics.calculate_sharpe_ratio(returns, risk_free_rate=0.0)
    assert sharpe is not None


def test_calculate_max_drawdown() -> object:
    """Test max drawdown returns a non-negative Decimal."""
    returns = [0.01, -0.02, 0.03, -0.05, 0.02, -0.01, 0.015]
    mdd = RiskMetrics.calculate_max_drawdown(returns)
    assert float(mdd) >= 0, "Max drawdown should be non-negative"


def test_calculate_expected_return() -> object:
    """Test expected return calculation."""
    returns = [0.01, 0.02, -0.005, 0.015, -0.01]
    expected = RiskMetrics.calculate_expected_return(returns)
    assert expected is not None
    # Mean of the list
    import numpy as np

    assert abs(float(expected) - float(np.mean(returns))) < 1e-10


def test_calculate_volatility() -> object:
    """Test volatility is positive."""
    returns = [0.01, 0.02, -0.005, 0.015, -0.01, 0.008]
    vol = RiskMetrics.calculate_volatility(returns)
    assert float(vol) > 0


def test_efficient_frontier_delegates_correctly() -> object:
    """Test the efficient frontier calculation delegates to PyPortfolioOpt."""
    mock_returns = pd.Series([0.1, 0.2], index=["A", "B"])
    mock_cov = pd.DataFrame(
        [[0.1, 0.05], [0.05, 0.2]], index=["A", "B"], columns=["A", "B"]
    )

    mock_ef_instance = MagicMock()
    mock_ef_instance.max_sharpe.return_value = None
    mock_ef_instance.clean_weights.return_value = {"A": 0.6, "B": 0.4}

    try:
        with patch("pypfopt.EfficientFrontier", return_value=mock_ef_instance):
            weights = RiskMetrics.efficient_frontier(mock_returns, mock_cov)
            assert isinstance(weights, dict)
    except ImportError:
        pytest.skip("PyPortfolioOpt not available")
