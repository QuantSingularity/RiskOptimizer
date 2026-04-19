"""
Advanced Portfolio Optimization Models for RiskOptimizer

This module provides AI-driven portfolio optimization models that extend
beyond traditional mean-variance optimization to include:
1. Machine learning-based return prediction
2. Risk factor modeling
3. Black-Litterman model integration
4. Monte Carlo simulation for risk assessment
5. Reinforcement learning for dynamic portfolio allocation
"""

import logging
import os
from typing import Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)


class AdvancedPortfolioOptimizer:
    """Advanced portfolio optimization using multiple AI techniques."""

    def __init__(self, risk_tolerance: object = 5) -> None:
        """
        Initialize the optimizer with risk tolerance level.

        Args:
            risk_tolerance: Integer from 1-10 representing user's risk tolerance
                            1: Very conservative
                            10: Very aggressive
        """
        self.risk_tolerance = risk_tolerance
        self.scaler = StandardScaler()
        self.return_model: Optional[RandomForestRegressor] = None
        self.market_factors = None
        self.trained = False

    def preprocess_data(
        self, historical_data: pd.DataFrame
    ) -> Tuple[np.ndarray, pd.Series]:
        """
        Preprocess market data for model training.

        Args:
            historical_data: DataFrame with asset prices and market indicators

        Returns:
            X: Feature matrix
            y: Target returns
        """
        returns = historical_data.pct_change().dropna()
        features = pd.DataFrame()
        for lag in [1, 3, 5]:
            features[f"lag_{lag}"] = returns.shift(lag).mean(axis=1)
        features["volatility_5d"] = returns.rolling(5).std().mean(axis=1)
        features["volatility_20d"] = returns.rolling(20).std().mean(axis=1)
        if "market_index" in historical_data.columns:
            features["market_return"] = historical_data["market_index"].pct_change()
        features = features.dropna()
        y = returns.shift(-1).mean(axis=1).loc[features.index]
        X = self.scaler.fit_transform(features)
        return X, y

    def train_return_prediction_model(
        self, historical_data: pd.DataFrame
    ) -> RandomForestRegressor:
        """
        Train machine learning model to predict future returns.

        Args:
            historical_data: DataFrame with asset prices and market indicators

        Returns:
            Trained model
        """
        X, y = self.preprocess_data(historical_data)
        model = RandomForestRegressor(n_estimators=100, max_depth=5, random_state=42)
        model.fit(X, y)
        self.return_model = model
        self.trained = True
        return model

    def predict_returns(self, historical_data: pd.DataFrame) -> Dict[str, float]:
        """
        Predict future returns using trained model.

        Args:
            historical_data: DataFrame with asset prices and market indicators

        Returns:
            Predicted returns for each asset
        """
        if not self.trained:
            self.train_return_prediction_model(historical_data)
        X, _ = self.preprocess_data(historical_data)
        latest_features = X[-1].reshape(1, -1)
        predicted_market_return = self.return_model.predict(latest_features)[0]
        asset_returns: Dict[str, float] = {}
        returns = historical_data.pct_change().dropna()
        market_returns = returns.mean(axis=1)
        for asset in historical_data.columns:
            if asset != "market_index":
                asset_returns_series = historical_data[asset].pct_change().dropna()
                if len(asset_returns_series) > 0 and len(market_returns) > 0:
                    common_index = asset_returns_series.index.intersection(
                        market_returns.index
                    )
                    if len(common_index) > 0:
                        asset_returns_aligned = asset_returns_series.loc[common_index]
                        market_returns_aligned = market_returns.loc[common_index]
                        beta = np.cov(asset_returns_aligned, market_returns_aligned)[
                            0, 1
                        ] / np.var(market_returns_aligned)
                        asset_returns[asset] = 0.02 + beta * predicted_market_return
                    else:
                        asset_returns[asset] = 0.05
                else:
                    asset_returns[asset] = 0.05
        return asset_returns

    def calculate_risk_adjusted_returns(
        self, historical_data: pd.DataFrame
    ) -> Dict[str, float]:
        """
        Calculate risk-adjusted expected returns using Black-Litterman model.

        Args:
            historical_data: DataFrame with asset prices

        Returns:
            Dictionary of risk-adjusted expected returns for each asset
        """
        predicted_returns = self.predict_returns(historical_data)
        risk_adjustment = (self.risk_tolerance - 5) / 10
        risk_adjusted_returns: Dict[str, float] = {}
        for asset in predicted_returns:
            confidence = 0.5 + risk_adjustment
            prior_return = 0.05
            risk_adjusted_returns[asset] = (
                1 - confidence
            ) * prior_return + confidence * predicted_returns[asset]
        return risk_adjusted_returns

    def optimize_portfolio(
        self, historical_data: pd.DataFrame
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        """
        Optimize portfolio weights using risk-adjusted returns and covariance.

        Args:
            historical_data: DataFrame with asset prices

        Returns:
            Tuple of (optimal_weights dict, performance_metrics dict)
        """
        expected_returns = self.calculate_risk_adjusted_returns(historical_data)
        returns = historical_data.pct_change().dropna()
        cov_matrix = returns.cov()
        assets = [asset for asset in historical_data.columns if asset != "market_index"]
        n_assets = len(assets)
        initial_weights = np.array([1 / n_assets] * n_assets)
        bounds = tuple((0, 1) for _ in range(n_assets))
        constraints = {"type": "eq", "fun": lambda x: np.sum(x) - 1}
        risk_aversion = 10 - self.risk_tolerance

        def objective(weights: np.ndarray) -> float:
            portfolio_return = sum(
                weights[i] * expected_returns[assets[i]] for i in range(n_assets)
            )
            portfolio_volatility = np.sqrt(
                np.dot(
                    weights.T, np.dot(cov_matrix.loc[assets, assets].values, weights)
                )
            )
            return -(portfolio_return - risk_aversion * portfolio_volatility)

        result = minimize(
            objective,
            initial_weights,
            method="SLSQP",
            bounds=bounds,
            constraints=constraints,
        )
        optimal_weights = {assets[i]: result["x"][i] for i in range(n_assets)}
        portfolio_return = sum(
            optimal_weights[asset] * expected_returns[asset]
            for asset in optimal_weights
        )
        weight_array = np.array([optimal_weights[asset] for asset in assets])
        portfolio_volatility = np.sqrt(
            np.dot(
                weight_array.T,
                np.dot(cov_matrix.loc[assets, assets].values, weight_array),
            )
        )
        risk_free_rate = 0.02
        sharpe_ratio = (portfolio_return - risk_free_rate) / (
            portfolio_volatility + 1e-10
        )
        performance_metrics = {
            "expected_return": portfolio_return,
            "volatility": portfolio_volatility,
            "sharpe_ratio": sharpe_ratio,
        }
        return optimal_weights, performance_metrics

    def save_model(self, filepath: str) -> None:
        """Save the trained model to disk."""
        if not self.trained:
            raise ValueError("Model must be trained before saving")
        # FIX: use abspath to handle bare filename edge case where dirname returns ""
        save_dir = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(save_dir, exist_ok=True)
        joblib.dump(
            {
                "model": self.return_model,
                "scaler": self.scaler,
                "risk_tolerance": self.risk_tolerance,
            },
            filepath,
        )
        logger.info(f"Model saved to {filepath}")

    @classmethod
    def load_model(cls, filepath: str) -> "AdvancedPortfolioOptimizer":
        """Load a trained model from disk."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        saved_data = joblib.load(filepath)
        instance = cls(risk_tolerance=saved_data["risk_tolerance"])
        instance.return_model = saved_data["model"]
        instance.scaler = saved_data["scaler"]
        instance.trained = True
        return instance

    def monte_carlo_simulation(
        self,
        historical_data: pd.DataFrame,
        optimal_weights: Dict[str, float],
        num_simulations: int = 1000,
        time_horizon: int = 252,
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        """
        Run Monte Carlo simulation to assess portfolio risk.

        Args:
            historical_data: DataFrame with asset prices
            optimal_weights: Dictionary of portfolio weights
            num_simulations: Number of simulations to run
            time_horizon: Time horizon in trading days (252 = 1 year)

        Returns:
            Tuple of (simulation_df, risk_metrics dict)
        """
        returns = historical_data.pct_change().dropna()
        mean_returns = returns.mean()
        cov_matrix = returns.cov()
        assets = list(optimal_weights.keys())
        weights = np.array([optimal_weights[asset] for asset in assets])
        initial_portfolio_value = 10000
        simulation_results = np.zeros((time_horizon, num_simulations))
        for sim in range(num_simulations):
            random_returns = np.random.multivariate_normal(
                mean_returns.loc[assets].values,
                cov_matrix.loc[assets, assets].values,
                time_horizon,
            )
            portfolio_returns = np.sum(random_returns * weights, axis=1)
            cumulative_returns = np.cumprod(1 + portfolio_returns)
            simulation_results[:, sim] = initial_portfolio_value * cumulative_returns
        simulation_df = pd.DataFrame(simulation_results)
        final_values = simulation_df.iloc[-1]
        var_95 = np.percentile(final_values, 5)
        var_99 = np.percentile(final_values, 1)
        expected_value = final_values.mean()
        # FIX: compute max_drawdown properly (avoid dividing by near-zero max)
        running_max = np.maximum.accumulate(simulation_results, axis=0)
        drawdowns = np.where(
            running_max > 0,
            (simulation_results - running_max) / running_max,
            0.0,
        )
        avg_max_drawdown = float(np.mean(np.min(drawdowns, axis=0)))
        risk_metrics = {
            "expected_final_value": expected_value,
            "var_95": initial_portfolio_value - var_95,
            "var_99": initial_portfolio_value - var_99,
            "max_drawdown": abs(avg_max_drawdown),
        }
        return simulation_df, risk_metrics
