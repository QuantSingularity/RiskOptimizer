import logging
import os
from typing import Any, Dict, Optional, Tuple

import pandas as pd
from data.loaders import available_symbols, load_close_prices
from optimization.portfolio import (
    MIN_TRAINING_ROWS,
    AdvancedPortfolioOptimizer,
    resolve_model_path,
)

logger = logging.getLogger(__name__)

TEST_FRACTION = 0.2


def load_training_data(
    symbols: Optional[list] = None, data_dir: Optional[os.PathLike] = None
) -> pd.DataFrame:
    selected = symbols or available_symbols(data_dir)
    if len(selected) < 2:
        raise ValueError("At least two symbols with historical data are required")
    return load_close_prices(selected, data_dir)


def train_and_evaluate(
    data: pd.DataFrame, risk_tolerance: float = 5
) -> Tuple[AdvancedPortfolioOptimizer, Dict[str, Any]]:
    split = int(len(data) * (1.0 - TEST_FRACTION))
    if split < MIN_TRAINING_ROWS + 1 or len(data) - split < MIN_TRAINING_ROWS:
        raise ValueError("Not enough history for a chronological train and test split")
    train_data = data.iloc[:split]
    test_data = data.iloc[split:]
    optimizer = AdvancedPortfolioOptimizer(risk_tolerance=risk_tolerance)
    optimizer.train_return_prediction_model(train_data)
    prediction_metrics = optimizer.evaluate(test_data)
    weights, portfolio_metrics = optimizer.optimize_portfolio(test_data)
    _, risk_metrics = optimizer.monte_carlo_simulation(test_data, weights, seed=42)
    optimizer.training_summary.update(
        {
            "train_rows": int(len(train_data)),
            "test_rows": int(len(test_data)),
            "assets": list(weights.keys()),
            "prediction_metrics": prediction_metrics,
        }
    )
    return optimizer, {
        "prediction_metrics": prediction_metrics,
        "portfolio_weights": weights,
        "portfolio_metrics": portfolio_metrics,
        "risk_metrics": risk_metrics,
    }


def train_and_save(
    model_path: Optional[os.PathLike] = None,
    symbols: Optional[list] = None,
    data_dir: Optional[os.PathLike] = None,
    risk_tolerance: float = 5,
) -> Tuple[AdvancedPortfolioOptimizer, Dict[str, Any], str]:
    data = load_training_data(symbols, data_dir)
    optimizer, report = train_and_evaluate(data, risk_tolerance)
    final = AdvancedPortfolioOptimizer(risk_tolerance=risk_tolerance)
    final.train_return_prediction_model(data)
    final.training_summary.update(optimizer.training_summary)
    final.training_summary["samples"] = int(len(data))
    path = resolve_model_path(model_path)
    final.save_model(path)
    logger.info("Trained model saved to %s", path)
    return final, report, path
