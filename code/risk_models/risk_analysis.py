import logging
import os
from typing import Any

import numpy as np
import pandas as pd
from arch import arch_model

logger = logging.getLogger(__name__)
DATA_DIR = "data"
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "BTC-USD", "ETH-USD"]


def load_data(tickers: list, data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Loads historical 'Close' price data for a list of tickers."""
    all_data = {}
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
    """Computes the correlation matrix of asset returns."""
    logger.info("\n--- Correlation Matrix ---")
    corr_matrix = returns.corr()
    logger.info(corr_matrix)
    return corr_matrix


def historical_var(
    returns: pd.DataFrame, confidence_level: float = 0.99, horizon: int = 1
) -> pd.Series:
    """
    Calculates Value-at-Risk (VaR) using the historical simulation method.

    :param returns: DataFrame of asset returns.
    :param confidence_level: The confidence level (e.g., 0.99 for 99% VaR).
    :param horizon: The time horizon in days (e.g., 1 for 1-day VaR).
    :return: Series of VaR values for each asset.
    """
    logger.info(
        f"\n--- Historical VaR ({confidence_level * 100:.0f}%, {horizon}-day) ---"
    )
    alpha = 1 - confidence_level
    var_values = returns.quantile(alpha) * np.sqrt(horizon)
    logger.info(var_values)
    return var_values


def monte_carlo_var(
    returns: pd.DataFrame,
    confidence_level: float = 0.99,
    horizon: int = 1,
    n_simulations: int = 10000,
) -> pd.Series:
    """
    Calculates Value-at-Risk (VaR) using Monte Carlo simulation (assuming Normal distribution).

    :param returns: DataFrame of asset returns.
    :param confidence_level: The confidence level (e.g., 0.99 for 99% VaR).
    :param horizon: The time horizon in days (e.g., 1 for 1-day VaR).
    :param n_simulations: Number of Monte Carlo paths to simulate.
    :return: Series of VaR values for each asset.
    """
    logger.info(
        f"\n--- Monte Carlo VaR ({confidence_level * 100:.0f}%, {horizon}-day) ---"
    )
    mu = returns.mean()
    sigma = returns.std()
    alpha = 1 - confidence_level
    var_values = {}
    for ticker in returns.columns:
        simulated_returns = np.random.normal(
            mu[ticker] * horizon, sigma[ticker] * np.sqrt(horizon), n_simulations
        )
        var = np.percentile(simulated_returns, alpha * 100)
        var_values[ticker] = var
    var_series = pd.Series(var_values)
    logger.info(var_series)
    return var_series


def garch_volatility_forecast(returns: pd.DataFrame, horizon: int = 5) -> pd.Series:
    """
    Forecasts volatility for each asset using a GARCH(1,1) model.

    :param returns: DataFrame of asset returns.
    :param horizon: The number of days to forecast volatility.
    :return: Series of annualized volatility forecasts.
    """
    logger.info(f"\n--- GARCH(1,1) Volatility Forecast ({horizon}-day) ---")
    forecasts = {}
    for ticker in returns.columns:
        am = arch_model(returns[ticker] * 100, vol="Garch", p=1, q=1, rescale=False)
        res = am.fit(disp="off")
        forecast = res.forecast(horizon=horizon)
        volatility_forecast = np.sqrt(forecast.variance.iloc[-1].sum()) / 100
        annualized_vol = volatility_forecast * np.sqrt(252)
        forecasts[ticker] = annualized_vol
    forecast_series = pd.Series(forecasts)
    logger.info(forecast_series)
    return forecast_series


def stress_test(returns: pd.DataFrame, scenario_multiplier: float = 3.0) -> pd.Series:
    """
    Performs a simple stress test by simulating an extreme market shock.

    :param returns: DataFrame of asset returns.
    :param scenario_multiplier: Multiplier for the standard deviation to define the shock.
    :return: Series of simulated loss for each asset.
    """
    logger.info(
        f"\n--- Stress Test (Extreme Shock: {scenario_multiplier}x Std Dev) ---"
    )
    shock = returns.std() * scenario_multiplier
    simulated_loss = -shock
    logger.info(simulated_loss)
    return simulated_loss


def run_risk_analysis() -> Any:
    """Main function to run all risk analysis components."""
    try:
        returns = load_data(TICKERS)
        calculate_correlation_matrix(returns)
        historical_var(returns, confidence_level=0.99, horizon=1)
        monte_carlo_var(returns, confidence_level=0.95, horizon=5)
        garch_volatility_forecast(returns, horizon=5)
        stress_test(returns, scenario_multiplier=4.0)
    except FileNotFoundError as e:
        logger.info(f"Error: {e}")
        logger.info(
            "Please ensure the data ingestion script (data_ingestion.py) has been run successfully."
        )
    except Exception as e:
        logger.info(f"An unexpected error occurred during risk analysis: {e}")


if __name__ == "__main__":
    run_risk_analysis()
