"""
Risk analysis utilities for RiskOptimizer.

Provides historical VaR, Monte Carlo VaR, GARCH volatility forecasting,
correlation analysis, and stress testing — all with proper type annotations.
"""

import logging
import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from arch import arch_model

logger = logging.getLogger(__name__)
DATA_DIR = "data"
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "BTC-USD", "ETH-USD"]


def load_data(tickers: List[str], data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Load historical 'Close' prices and return log-return DataFrame."""
    all_data: Dict[str, pd.Series] = {}
    for ticker in tickers:
        file_name = f"{ticker.replace('-', '_')}_historical.csv"
        file_path = os.path.join(data_dir, file_name)
        if os.path.exists(file_path):
            df = pd.read_csv(file_path, index_col=0, parse_dates=True)
            all_data[ticker] = df["Close"]
        else:
            logger.info(f"Warning: Data file not found for {ticker} at {file_path}")
    if not all_data:
        raise FileNotFoundError(
            "No data files were loaded. Run data_ingestion.py first."
        )
    data = pd.DataFrame(all_data).ffill().dropna()
    returns = np.log(data / data.shift(1)).dropna()
    return returns


def calculate_correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    """Return the pairwise correlation matrix of asset returns."""
    logger.info("--- Correlation Matrix ---")
    corr_matrix = returns.corr()
    logger.info(str(corr_matrix))
    return corr_matrix


def historical_var(
    returns: pd.DataFrame,
    confidence_level: float = 0.99,
    horizon: int = 1,
) -> pd.Series:
    """
    Historical-simulation VaR for each asset.

    Args:
        returns: DataFrame of daily asset returns.
        confidence_level: Confidence level (e.g. 0.95 for 95 % VaR).
        horizon: Holding period in days.

    Returns:
        Series of VaR values (negative = loss).
    """
    logger.info(
        f"--- Historical VaR ({confidence_level * 100:.0f}%, {horizon}-day) ---"
    )
    alpha = 1 - confidence_level
    var_values: pd.Series = returns.quantile(alpha) * np.sqrt(horizon)
    logger.info(str(var_values))
    return var_values


def monte_carlo_var(
    returns: pd.DataFrame,
    confidence_level: float = 0.99,
    horizon: int = 1,
    n_simulations: int = 10_000,
    seed: Optional[int] = None,
) -> pd.Series:
    """
    Monte Carlo VaR under a Normal return assumption.

    Args:
        returns: DataFrame of daily asset returns.
        confidence_level: Confidence level (e.g. 0.95).
        horizon: Holding period in days.
        n_simulations: Number of Monte Carlo paths.
        seed: Optional RNG seed for reproducibility.

    Returns:
        Series of VaR values (negative = loss).
    """
    logger.info(
        f"--- Monte Carlo VaR ({confidence_level * 100:.0f}%, {horizon}-day, "
        f"{n_simulations:,} sims) ---"
    )
    rng = np.random.default_rng(seed)
    mu = returns.mean()
    sigma = returns.std()
    alpha = 1 - confidence_level
    var_values: Dict[str, float] = {}
    for ticker in returns.columns:
        simulated = rng.normal(
            mu[ticker] * horizon,
            sigma[ticker] * np.sqrt(horizon),
            n_simulations,
        )
        var_values[ticker] = float(np.percentile(simulated, alpha * 100))
    var_series = pd.Series(var_values)
    logger.info(str(var_series))
    return var_series


def garch_volatility_forecast(returns: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """
    GARCH(1,1) annualised volatility forecasts for each asset.

    Args:
        returns: DataFrame of daily asset returns.
        horizon: Forecast horizon in trading days.

    Returns:
        Series of annualised volatility forecasts.
    """
    logger.info(f"--- GARCH(1,1) Volatility Forecast ({horizon}-day) ---")
    forecasts: Dict[str, float] = {}
    for ticker in returns.columns:
        am = arch_model(returns[ticker] * 100, vol="Garch", p=1, q=1, rescale=False)
        res = am.fit(disp="off")
        forecast = res.forecast(horizon=horizon)
        vol_forecast = float(np.sqrt(forecast.variance.iloc[-1].sum())) / 100
        forecasts[ticker] = vol_forecast * np.sqrt(252)
    forecast_series = pd.Series(forecasts)
    logger.info(str(forecast_series))
    return forecast_series


def stress_test(returns: pd.DataFrame, scenario_multiplier: float = 3.0) -> pd.Series:
    """
    Stress test: estimate per-asset loss under an extreme shock of
    ``scenario_multiplier`` standard deviations.

    Args:
        returns: DataFrame of daily asset returns.
        scenario_multiplier: Number of σ for the stress scenario.

    Returns:
        Series of simulated losses (negative values).
    """
    logger.info(f"--- Stress Test (Extreme Shock: {scenario_multiplier}× Std Dev) ---")
    shock = returns.std() * scenario_multiplier
    simulated_loss: pd.Series = -shock
    logger.info(str(simulated_loss))
    return simulated_loss


def run_risk_analysis() -> None:
    """CLI entry point: run all risk analysis components."""
    try:
        returns = load_data(TICKERS)
        calculate_correlation_matrix(returns)
        historical_var(returns, confidence_level=0.99, horizon=1)
        monte_carlo_var(returns, confidence_level=0.95, horizon=5)
        garch_volatility_forecast(returns, horizon=5)
        stress_test(returns, scenario_multiplier=4.0)
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during risk analysis: {e}")


if __name__ == "__main__":
    run_risk_analysis()
