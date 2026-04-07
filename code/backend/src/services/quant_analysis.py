from decimal import Decimal, getcontext
from typing import Any, List

import numpy as np
from scipy.stats import norm


def _decimal_to_float(values: List) -> List[float]:
    """Convert list of Decimal or other numeric types to float for numpy operations."""
    return [float(v) for v in values]


getcontext().prec = 28


class RiskMetrics:

    @staticmethod
    def calculate_var(returns: Any, confidence: Any = 0.95) -> Any:
        """
        Calculate Value at Risk (VaR) using the parametric method.
        Returns a positive Decimal representing the magnitude of potential loss.

        Args:
            returns: A list or array of portfolio returns.
            confidence: The confidence level (e.g., 0.95 for 95% VaR).

        Returns:
            Decimal: The calculated Value at Risk (positive value).
        """
        if not isinstance(returns, (list, np.ndarray)) or len(returns) == 0:
            raise ValueError("Returns must be a non-empty list or numpy array.")
        float_returns = [float(r) for r in returns]
        mean = np.mean(float_returns)
        std = np.std(float_returns)
        z_score = norm.ppf(1 - confidence)
        var = mean + z_score * std
        return Decimal(str(abs(var)))

    @staticmethod
    def calculate_cvar(returns: Any, confidence: Any = 0.95) -> Any:
        """
        Calculate Conditional Value at Risk (CVaR), also known as Expected Shortfall.
        Returns a positive Decimal representing the expected loss beyond the VaR threshold.

        Args:
            returns: A list or array of portfolio returns.
            confidence: The confidence level for CVaR calculation.

        Returns:
            Decimal: The calculated Conditional Value at Risk (positive value).
        """
        if not isinstance(returns, (list, np.ndarray)) or len(returns) == 0:
            raise ValueError("Returns must be a non-empty list or numpy array.")
        float_returns = [float(r) for r in returns]
        var_threshold = np.percentile(float_returns, (1 - confidence) * 100)
        tail_losses = [r for r in float_returns if r <= var_threshold]
        if not tail_losses:
            return Decimal(str(abs(var_threshold)))
        cvar = abs(float(np.mean(tail_losses)))
        return Decimal(str(cvar))

    @staticmethod
    def efficient_frontier(returns: Any, cov_matrix: Any) -> Any:
        """
        Calculate the optimal portfolio weights for the efficient frontier (max Sharpe ratio).
        Uses the PyPortfolioOpt library.

        Args:
            returns: A pandas Series of expected returns for each asset.
            cov_matrix: A pandas DataFrame of the covariance matrix of asset returns.

        Returns:
            dict: A dictionary of asset tickers and their optimal weights.
        """
        try:
            from pypfopt import EfficientFrontier
        except ImportError:
            raise ImportError(
                "PyPortfolioOpt is not installed. Please install it using `pip install PyPortfolioOpt`."
            )
        ef = EfficientFrontier(returns, cov_matrix)
        ef.max_sharpe()
        cleaned_weights = ef.clean_weights()
        return {asset: str(weight) for asset, weight in cleaned_weights.items()}

    @staticmethod
    def calculate_sharpe_ratio(returns: Any, risk_free_rate: Any = 0.02) -> Any:
        """
        Calculate the Sharpe Ratio of a portfolio.

        Args:
            returns: A list or array of portfolio returns.
            risk_free_rate: The risk-free rate of return.

        Returns:
            Decimal: The calculated Sharpe Ratio.
        """
        if not isinstance(returns, (list, np.ndarray)) or len(returns) < 2:
            raise ValueError(
                "Returns must be a list or numpy array with at least two elements."
            )
        float_returns = [float(r) for r in returns]
        rf = float(risk_free_rate)
        excess_returns = [r - rf for r in float_returns]
        mean_excess = float(np.mean(excess_returns))
        std_excess = float(np.std(excess_returns, ddof=1))
        if std_excess == 0:
            return Decimal("0.0")
        sharpe_ratio = mean_excess / std_excess
        return Decimal(str(sharpe_ratio))

    @staticmethod
    def calculate_max_drawdown(returns: Any) -> Any:
        """
        Calculate Maximum Drawdown of a portfolio.
        Returns a non-negative Decimal representing the magnitude of the worst drawdown.

        Args:
            returns: A list or array of portfolio returns.

        Returns:
            Decimal: The calculated Maximum Drawdown (positive value).
        """
        if not isinstance(returns, (list, np.ndarray)) or len(returns) < 2:
            raise ValueError(
                "Returns must be a list or numpy array with at least two elements."
            )
        float_returns = [float(r) for r in returns]
        cumulative = np.cumprod([1 + r for r in float_returns])
        peak = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - peak) / peak
        max_drawdown = abs(float(np.min(drawdown)))
        return Decimal(str(max_drawdown))

    @staticmethod
    def calculate_expected_return(returns: Any) -> Any:
        """
        Calculate the expected (mean) return of a portfolio.

        Args:
            returns: A list or array of portfolio returns.

        Returns:
            Decimal: The calculated expected return.
        """
        if not isinstance(returns, (list, np.ndarray)) or len(returns) == 0:
            raise ValueError("Returns must be a non-empty list or numpy array.")
        float_returns = [float(r) for r in returns]
        mean = float(np.mean(float_returns))
        return Decimal(str(mean))

    @staticmethod
    def calculate_volatility(returns: Any) -> Any:
        """
        Calculate the volatility (standard deviation) of a portfolio.

        Args:
            returns: A list or array of portfolio returns.

        Returns:
            Decimal: The calculated volatility.
        """
        if not isinstance(returns, (list, np.ndarray)) or len(returns) < 2:
            raise ValueError(
                "Returns must be a list or numpy array with at least two elements."
            )
        float_returns = [float(r) for r in returns]
        vol = float(np.std(float_returns, ddof=1))
        return Decimal(str(vol))
