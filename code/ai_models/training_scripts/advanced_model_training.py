"""
Advanced Model Training Script for RiskOptimizer

This script trains the advanced portfolio optimization model using historical market data.
It demonstrates how to:
1. Load and preprocess market data
2. Train the machine learning return prediction model
3. Save the trained model for production use
4. Validate model performance
"""

import logging
import os
import sys
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from optimization_model import AdvancedPortfolioOptimizer
from sklearn.metrics import mean_squared_error, r2_score

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_sample_data() -> Any:
    """
    Load sample market data for training
    In production, this would load from a database or API
    """
    np.random.seed(42)
    dates = pd.date_range(start="2020-01-01", end="2023-12-31", freq="B")
    assets = ["BTC", "ETH", "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "SPY"]
    data = pd.DataFrame(index=dates)
    for asset in assets:
        if asset in ["BTC", "ETH"]:
            base_price = 10000 if asset == "BTC" else 1000
            volatility = 0.03
        else:
            base_price = 100
            volatility = 0.015
        prices = [base_price]
        for _ in range(1, len(dates)):
            daily_return = np.random.normal(0.0005, volatility)
            if prices[-1] > prices[0]:
                daily_return += 0.0001
            else:
                daily_return -= 0.0001
            new_price = prices[-1] * (1 + daily_return)
            prices.append(new_price)
        data[asset] = prices
    market_returns = np.random.normal(0.0004, 0.01, size=len(dates))
    market_prices = 100 * np.cumprod(1 + market_returns)
    data["market_index"] = market_prices
    return data


def train_and_evaluate_model(data: Any, risk_tolerance: Any = 5) -> Any:
    """
    Train the model and evaluate its performance

    Args:
        data: DataFrame with historical price data
        risk_tolerance: Risk tolerance level (1-10)

    Returns:
        Trained model and evaluation metrics
    """
    logger.info("Training advanced portfolio optimization model...")
    optimizer = AdvancedPortfolioOptimizer(risk_tolerance=risk_tolerance)
    train_data = data.iloc[: int(len(data) * 0.8)]
    test_data = data.iloc[int(len(data) * 0.8) :]
    optimizer.train_return_prediction_model(train_data)
    X_test, y_test = optimizer.preprocess_data(test_data)
    y_pred = optimizer.return_model.predict(X_test)
    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)
    logger.info("Model evaluation metrics:")
    logger.info(f"Mean Squared Error: {mse:.6f}")
    logger.info(f"R² Score: {r2:.4f}")
    weights, metrics = optimizer.optimize_portfolio(test_data)
    logger.info("\nOptimal portfolio weights:")
    for asset, weight in weights.items():
        logger.info(f"  {asset}: {weight:.4f}")
    logger.info("\nPortfolio performance metrics:")
    logger.info(f"  Expected Return: {metrics['expected_return']:.4f}")
    logger.info(f"  Volatility: {metrics['volatility']:.4f}")
    logger.info(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.4f}")
    logger.info("\nRunning Monte Carlo simulation...")
    simulation, risk_metrics = optimizer.monte_carlo_simulation(test_data, weights)
    logger.info("Risk assessment metrics:")
    logger.info(f"  Expected Final Value: ${risk_metrics['expected_final_value']:.2f}")
    logger.info(f"  95% Value at Risk: ${risk_metrics['var_95']:.2f}")
    logger.info(f"  99% Value at Risk: ${risk_metrics['var_99']:.2f}")
    logger.info(f"  Average Max Drawdown: {risk_metrics['max_drawdown']:.4f}")
    return (
        optimizer,
        {
            "prediction_metrics": {"mse": mse, "r2": r2},
            "portfolio_metrics": metrics,
            "risk_metrics": risk_metrics,
        },
    )


def save_model_visualization(data: Any, optimizer: Any, output_dir: Any) -> Any:
    """
    Generate and save visualizations of model performance

    Args:
        data: DataFrame with historical price data
        optimizer: Trained optimizer instance
        output_dir: Directory to save visualizations
    """
    os.makedirs(output_dir, exist_ok=True)
    returns = data.pct_change().dropna()
    num_portfolios = 1000
    results = np.zeros((3, num_portfolios))
    weights_record = []
    assets = [col for col in data.columns if col != "market_index"]
    n_assets = len(assets)
    for i in range(num_portfolios):
        weights = np.random.random(n_assets)
        weights /= np.sum(weights)
        weights_record.append(weights)
        portfolio_return = np.sum(returns.mean() * weights) * 252
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(returns.cov() * 252, weights)))
        sharpe_ratio = portfolio_return / portfolio_vol
        results[0, i] = portfolio_return
        results[1, i] = portfolio_vol
        results[2, i] = sharpe_ratio
    optimized_weights, metrics = optimizer.optimize_portfolio(data)
    opt_return = metrics["expected_return"]
    opt_vol = metrics["volatility"]
    plt.figure(figsize=(10, 6))
    plt.scatter(
        results[1, :],
        results[0, :],
        c=results[2, :],
        cmap="viridis",
        marker="o",
        s=10,
        alpha=0.3,
    )
    plt.colorbar(label="Sharpe ratio")
    plt.scatter(
        opt_vol, opt_return, color="red", marker="*", s=300, label="Optimized Portfolio"
    )
    plt.title("Portfolio Optimization: Efficient Frontier")
    plt.xlabel("Volatility")
    plt.ylabel("Expected Return")
    plt.legend()
    plt.savefig(os.path.join(output_dir, "efficient_frontier.png"))
    weights = {
        asset: weight
        for asset, weight in zip(assets, weights_record[np.argmax(results[2, :])])
    }
    simulation, _ = optimizer.monte_carlo_simulation(data, optimized_weights)
    plt.figure(figsize=(10, 6))
    plt.plot(simulation.iloc[:, :100])
    plt.title("Monte Carlo Simulation: Portfolio Value Over Time")
    plt.xlabel("Trading Days")
    plt.ylabel("Portfolio Value ($)")
    plt.savefig(os.path.join(output_dir, "monte_carlo_simulation.png"))
    logger.info(f"Visualizations saved to {output_dir}")


def main() -> Any:
    """Main function to train and save the model"""
    logger.info("Starting advanced model training for RiskOptimizer...")
    data = load_sample_data()
    logger.info(f"Loaded data with {len(data)} rows and {len(data.columns)} columns")
    optimizer, metrics = train_and_evaluate_model(data)
    model_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    model_path = os.path.join(model_dir, "trained_model.joblib")
    optimizer.save_model(model_path)
    vis_dir = os.path.join(model_dir, "visualizations")
    save_model_visualization(data, optimizer, vis_dir)
    logger.info(f"\nTraining complete. Model saved to {model_path}")
    logger.info(
        "Run this model in production by importing AdvancedPortfolioOptimizer and loading the saved model."
    )


if __name__ == "__main__":
    main()
