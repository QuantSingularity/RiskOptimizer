import math
from typing import Any
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from services.quant_analysis import RiskMetrics


def test_calculate_var() -> Any:
    """Test the Value at Risk calculation."""
    returns = [0.01, -0.02, 0.03, -0.01, 0.02, 0.005, -0.005]
    expected_var_95 = -0.02224716
    expected_var_99 = -0.03324024
    var_95 = RiskMetrics.calculate_var(returns, confidence=0.95)
    var_99 = RiskMetrics.calculate_var(returns, confidence=0.99)
    assert isinstance(var_95, float)
    assert var_95 == pytest.approx(expected_var_95, abs=0.0001)
    assert var_99 == pytest.approx(expected_var_99, abs=1e-05)


def test_calculate_var_empty_returns() -> Any:
    """Test VaR calculation with empty returns list should return NaN."""
    with pytest.warns(RuntimeWarning):
        result = RiskMetrics.calculate_var([])
        assert math.isnan(result)


@patch("pypfopt.EfficientFrontier")
def test_efficient_frontier(mock_ef: Any) -> Any:
    """Test the efficient frontier calculation delegates correctly."""
    mock_returns = pd.Series([0.1, 0.2], index=["A", "B"])
    mock_cov = pd.DataFrame(
        [[0.1, 0.05], [0.05, 0.2]], index=["A", "B"], columns=["A", "B"]
    )
    mock_ef_instance = MagicMock()
    mock_ef_instance.max_sharpe.return_value = None
    mock_ef_instance.clean_weights.return_value = {"A": 0.6, "B": 0.4}
    mock_ef.return_value = mock_ef_instance
    weights = RiskMetrics.efficient_frontier(mock_returns, mock_cov)
    assert weights == {"A": 0.6, "B": 0.4}
    mock_ef.assert_called_once_with(mock_returns, mock_cov)
    mock_ef_instance.max_sharpe.assert_called_once()
    mock_ef_instance.clean_weights.assert_called_once()
