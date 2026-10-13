import argparse
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from optimization.portfolio import (
    TRADING_DAYS,
    AdvancedPortfolioOptimizer,
    asset_columns,
    clean_prices,
)
from training.trainer import load_training_data, train_and_evaluate, train_and_save

logger = logging.getLogger(__name__)


def save_model_visualization(
    data: pd.DataFrame, optimizer: AdvancedPortfolioOptimizer, output_dir: str
) -> None:
    os.makedirs(output_dir, exist_ok=True)
    prices = clean_prices(data)
    assets = asset_columns(prices)
    returns = prices[assets].pct_change().dropna()
    mean_returns = returns.mean().to_numpy() * TRADING_DAYS
    covariance = returns.cov().to_numpy() * TRADING_DAYS
    rng = np.random.default_rng(42)
    weights = rng.dirichlet(np.ones(len(assets)), size=1000)
    port_returns = weights @ mean_returns
    port_vols = np.sqrt(np.einsum("ij,jk,ik->i", weights, covariance, weights))
    sharpe = port_returns / (port_vols + 1e-12)
    optimized, metrics = optimizer.optimize_portfolio(data)
    figure = plt.figure(figsize=(10, 6))
    plt.scatter(port_vols, port_returns, c=sharpe, cmap="viridis", s=10, alpha=0.3)
    plt.colorbar(label="Sharpe ratio")
    plt.scatter(
        metrics["volatility"],
        metrics["expected_return"],
        color="red",
        marker="*",
        s=300,
        label="Optimized portfolio",
    )
    plt.title("Portfolio Optimization: Efficient Frontier")
    plt.xlabel("Volatility")
    plt.ylabel("Expected return")
    plt.legend()
    figure.savefig(os.path.join(output_dir, "efficient_frontier.png"))
    plt.close(figure)
    simulation, _ = optimizer.monte_carlo_simulation(data, optimized, seed=42)
    figure = plt.figure(figsize=(10, 6))
    plt.plot(simulation.iloc[:, :100])
    plt.title("Monte Carlo Simulation: Portfolio Value Over Time")
    plt.xlabel("Trading days")
    plt.ylabel("Portfolio value")
    figure.savefig(os.path.join(output_dir, "monte_carlo_simulation.png"))
    plt.close(figure)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Train the portfolio optimizer")
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--model-path", default=None)
    parser.add_argument("--risk-tolerance", type=float, default=5)
    parser.add_argument("--visualize", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    data = load_training_data(args.symbols, args.data_dir)
    logger.info("Loaded %d rows and %d assets", len(data), len(data.columns))
    _, report = train_and_evaluate(data, args.risk_tolerance)
    pm = report["prediction_metrics"]
    logger.info("Hold-out MSE %.6f R2 %.4f", pm["mse"], pm["r2"])
    for asset, weight in report["portfolio_weights"].items():
        logger.info("  %s: %.4f", asset, weight)
    optimizer, _, path = train_and_save(
        args.model_path, args.symbols, args.data_dir, args.risk_tolerance
    )
    if args.visualize:
        target = Path(path).resolve().parent / "visualizations"
        save_model_visualization(data, optimizer, str(target))
    logger.info("Training complete. Model saved to %s", path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
