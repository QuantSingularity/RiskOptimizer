import logging
import os
from typing import Any

import pandas as pd
from pypfopt import expected_returns, risk_models
from pypfopt.discrete_allocation import DiscreteAllocation, get_latest_prices
from pypfopt.efficient_frontier import EfficientFrontier

logger = logging.getLogger(__name__)
DATA_DIR = "data"
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "BTC-USD", "ETH-USD"]


def load_prices(tickers: list, data_dir: str = DATA_DIR) -> pd.DataFrame:
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
    prices = pd.DataFrame(all_data).ffill().dropna()
    return prices


def mean_variance_optimization(prices: pd.DataFrame, target_risk: float = 0.2) -> dict:
    """
    Performs Markowitz Mean-Variance Optimization to find the portfolio
    with the maximum Sharpe ratio and the minimum volatility.
    """
    logger.info("\n--- Mean-Variance Optimization (Markowitz) ---")
    mu = expected_returns.mean_historical_return(prices)
    S = risk_models.sample_cov(prices)
    ef = EfficientFrontier(mu, S)
    ef.max_sharpe()
    cleaned_weights_max_sharpe = ef.clean_weights()
    logger.info("\nMax Sharpe Ratio Portfolio Weights:")
    logger.info(cleaned_weights_max_sharpe)
    performance_max_sharpe = ef.portfolio_performance(verbose=True)
    ef_min_vol = EfficientFrontier(mu, S)
    ef_min_vol.min_volatility()
    cleaned_weights_min_vol = ef_min_vol.clean_weights()
    logger.info("\nMin Volatility Portfolio Weights:")
    logger.info(cleaned_weights_min_vol)
    performance_min_vol = ef_min_vol.portfolio_performance(verbose=True)
    return {
        "max_sharpe_weights": cleaned_weights_max_sharpe,
        "max_sharpe_performance": performance_max_sharpe,
        "min_vol_weights": cleaned_weights_min_vol,
        "min_vol_performance": performance_min_vol,
    }


def discrete_allocation_suggestion(
    prices: pd.DataFrame, weights: dict, total_portfolio_value: float = 100000.0
) -> dict:
    """
    Calculates the number of shares to purchase for a given set of weights.
    """
    logger.info(
        f"\n--- Discrete Allocation Suggestion (Total Value: ${total_portfolio_value:,.2f}) ---"
    )
    latest_prices = get_latest_prices(prices)
    da = DiscreteAllocation(
        weights, latest_prices, total_portfolio_value=total_portfolio_value
    )
    allocation, leftover = da.lp_portfolio()
    logger.info("Discrete Allocation:")
    logger.info(allocation)
    logger.info(f"Funds remaining: ${leftover:,.2f}")
    return {"allocation": allocation, "leftover": leftover}


def run_portfolio_optimization() -> Any:
    """Main function to run all portfolio optimization components."""
    try:
        prices = load_prices(TICKERS)
        optimization_results = mean_variance_optimization(prices)
        discrete_allocation_suggestion(
            prices, optimization_results["max_sharpe_weights"]
        )
        logger.info("\n--- Portfolio Rebalancing Suggestion ---")
        logger.info(
            "A rebalancing suggestion would compare the current portfolio weights (from a user's database) with the newly calculated optimal weights."
        )
        logger.info(
            "For example, if current AAPL weight is 10% and optimal is 15%, the suggestion would be to 'BUY' more AAPL."
        )
        logger.info(
            "Since we don't have a current portfolio, we'll use the Max Sharpe weights as the target for a mock rebalance."
        )
    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        logger.info(
            "Please ensure the data ingestion script (data_ingestion.py) has been run successfully."
        )
    except Exception as e:
        logger.error(f"An unexpected error occurred during portfolio optimization: {e}")


if __name__ == "__main__":
    run_portfolio_optimization()
