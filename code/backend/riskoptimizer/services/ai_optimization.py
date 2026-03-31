"""
AI Optimization Service for RiskOptimizer Backend

This service integrates the advanced portfolio optimization models with the backend API.
It provides methods for:
1. Loading the trained model
2. Processing market data
3. Generating optimized portfolios based on user risk tolerance
4. Running risk simulations
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from typing import Any

import numpy as np
import pandas as pd
from ai_models.optimization_model import AdvancedPortfolioOptimizer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

MODEL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "ai_models",
)
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "trained_model.joblib")


class AIOptimizationService:
    """Service for AI-driven portfolio optimization"""

    def __init__(self, model_path: Any = None) -> None:
        """
        Initialize the optimization service

        Args:
            model_path: Path to the trained model file (optional)
        """
        self.model_path = model_path or DEFAULT_MODEL_PATH
        self.optimizer = None
        self.load_model()

    def load_model(self) -> Any:
        """Load the trained model"""
        try:
            if os.path.exists(self.model_path):
                self.optimizer = AdvancedPortfolioOptimizer.load_model(self.model_path)
                logger.info(f"Loaded optimization model from {self.model_path}")
            else:
                logger.info(
                    f"Model file not found at {self.model_path}. Creating new model."
                )
                self.optimizer = AdvancedPortfolioOptimizer()
        except Exception as e:
            logger.info(f"Error loading model: {e}")
            self.optimizer = AdvancedPortfolioOptimizer()

    def process_market_data(self, data: Any) -> Any:
        """
        Process market data for optimization

        Args:
            data: Dictionary or DataFrame with market data

        Returns:
            Processed DataFrame
        """
        if isinstance(data, dict):
            df = pd.DataFrame(data)
        else:
            df = data.copy()
        if "date" in df.columns:
            df.set_index("date", inplace=True)
        return df

    def optimize_portfolio(self, market_data: Any, risk_tolerance: Any = 5) -> Any:
        """
        Generate optimized portfolio allocation

        Args:
            market_data: Dictionary or DataFrame with market data
            risk_tolerance: User's risk tolerance (1-10)

        Returns:
            Dictionary with optimized weights and performance metrics
        """
        df = self.process_market_data(market_data)
        self.optimizer.risk_tolerance = risk_tolerance
        weights, metrics = self.optimizer.optimize_portfolio(df)
        result = {
            "optimized_allocation": {k: float(v) for k, v in weights.items()},
            "performance_metrics": {
                "expected_return": float(metrics["expected_return"]),
                "volatility": float(metrics["volatility"]),
                "sharpe_ratio": float(metrics["sharpe_ratio"]),
            },
        }
        return result

    def run_risk_simulation(
        self,
        market_data: Any,
        weights: Any,
        num_simulations: Any = 1000,
        time_horizon: Any = 252,
    ) -> Any:
        """
        Run Monte Carlo simulation for risk assessment

        Args:
            market_data: Dictionary or DataFrame with market data
            weights: Dictionary of portfolio weights
            num_simulations: Number of simulations to run
            time_horizon: Time horizon in trading days

        Returns:
            Dictionary with risk metrics and simulation summary
        """
        df = self.process_market_data(market_data)
        simulation, risk_metrics = self.optimizer.monte_carlo_simulation(
            df, weights, num_simulations, time_horizon
        )
        percentiles = [5, 25, 50, 75, 95]
        percentile_values = np.percentile(simulation.iloc[-1], percentiles)
        result = {
            "risk_metrics": {
                "expected_final_value": float(risk_metrics["expected_final_value"]),
                "value_at_risk_95": float(risk_metrics["var_95"]),
                "value_at_risk_99": float(risk_metrics["var_99"]),
                "max_drawdown": float(risk_metrics["max_drawdown"]),
            },
            "simulation_summary": {
                "initial_value": 10000,
                "time_horizon_days": time_horizon,
                "percentiles": {
                    f"p{p}": float(val)
                    for p, val in zip(percentiles, percentile_values)
                },
            },
        }
        return result

    def get_market_data(
        self, symbols: Any, start_date: Any = None, end_date: Any = None
    ) -> Any:
        """
        Get historical market data for specified symbols

        In production, this would fetch from a market data API
        For demonstration, we generate synthetic data

        Args:
            symbols: List of asset symbols
            start_date: Start date for historical data
            end_date: End date for historical data

        Returns:
            DataFrame with historical price data
        """
        if end_date is None:
            end_date = datetime.now()
        if start_date is None:
            start_date = end_date - timedelta(days=365 * 3)
        dates = pd.date_range(start=start_date, end=end_date, freq="B")
        df = pd.DataFrame(index=dates)
        np.random.seed(42)
        for symbol in symbols:
            if symbol in ["BTC", "ETH"]:
                base_price = 10000 if symbol == "BTC" else 1000
                volatility = 0.03
            else:
                base_price = 100
                volatility = 0.015
            prices = [base_price]
            for _ in range(1, len(dates)):
                daily_return = np.random.normal(0.0005, volatility)
                new_price = prices[-1] * (1 + daily_return)
                prices.append(new_price)
            df[symbol] = prices
        market_returns = np.random.normal(0.0004, 0.01, size=len(dates))
        market_prices = 100 * np.cumprod(1 + market_returns)
        df["market_index"] = market_prices
        return df

    def train_model_if_needed(self, market_data: Any = None) -> Any:
        """
        Train the model if it hasn't been trained

        Args:
            market_data: Optional market data for training

        Returns:
            True if training was successful, False otherwise
        """
        if not hasattr(self.optimizer, "trained") or not self.optimizer.trained:
            try:
                if market_data is None:
                    symbols = [
                        "BTC",
                        "ETH",
                        "AAPL",
                        "MSFT",
                        "GOOGL",
                        "AMZN",
                        "TSLA",
                        "SPY",
                    ]
                    market_data = self.get_market_data(symbols)
                self.optimizer.train_return_prediction_model(market_data)
                self.optimizer.save_model(self.model_path)
                return True
            except Exception as e:
                logger.info(f"Error training model: {e}")
                return False
        return True


optimization_service = AIOptimizationService()
