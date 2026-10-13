import copy
import logging
import math
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from scipy.optimize import minimize
from settings import RISK_FREE_RATE, TRADING_DAYS, default_model_path
from sklearn.covariance import LedoitWolf
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

PRIOR_ANNUAL_RETURN = 0.05
MARKET_COLUMN = "market_index"
MIN_OBSERVATIONS = 30
MIN_TRAINING_ROWS = 30
MODEL_FORMAT_VERSION = 2
OPTIMIZATION_METHODS = ("utility", "max_sharpe", "min_variance")
FEATURE_NAMES = (
    "lag_0",
    "lag_1",
    "lag_2",
    "mean_5d",
    "volatility_5d",
    "volatility_20d",
    "market_return",
)


def resolve_model_path(path: Optional[os.PathLike] = None) -> str:
    if path:
        return str(path)
    return str(default_model_path())


def validate_risk_tolerance(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float, np.number)):
        raise ValueError("risk_tolerance must be a number between 1 and 10")
    number = float(value)
    if not math.isfinite(number) or number < 1 or number > 10:
        raise ValueError("risk_tolerance must be between 1 and 10")
    return number


def asset_columns(data: pd.DataFrame) -> List[str]:
    return [column for column in data.columns if column != MARKET_COLUMN]


def clean_prices(data: pd.DataFrame) -> pd.DataFrame:
    if not isinstance(data, pd.DataFrame):
        raise TypeError("Market data must be a pandas DataFrame")
    if data.empty:
        raise ValueError("Market data is empty")
    frame = data.apply(pd.to_numeric, errors="coerce")
    frame = frame.replace([np.inf, -np.inf], np.nan)
    frame = frame.dropna(axis=1, how="all").ffill().dropna()
    if frame.empty:
        raise ValueError("Market data has no usable rows")
    if (frame <= 0).any().any():
        raise ValueError("Market data must contain strictly positive prices")
    return frame


def validate_weight_bounds(
    n_assets: int, min_weight: float, max_weight: float
) -> Tuple[float, float]:
    lower = float(min_weight)
    upper = float(max_weight)
    if not (math.isfinite(lower) and math.isfinite(upper)):
        raise ValueError("Weight bounds must be finite numbers")
    if lower < 0 or upper > 1 or lower > upper:
        raise ValueError(
            "Weight bounds must satisfy 0 <= min_weight <= max_weight <= 1"
        )
    if n_assets * lower > 1 + 1e-9 or n_assets * upper < 1 - 1e-9:
        raise ValueError(
            f"Weight bounds are infeasible for {n_assets} assets: "
            f"min_weight={lower}, max_weight={upper}"
        )
    return lower, upper


class PortfolioOptimizerBase:
    model_type = "base"

    def __init__(self, risk_tolerance: float = 5) -> None:
        self.risk_tolerance = risk_tolerance

    @property
    def risk_tolerance(self) -> float:
        return self._risk_tolerance

    @risk_tolerance.setter
    def risk_tolerance(self, value: float) -> None:
        self._risk_tolerance = validate_risk_tolerance(value)

    def with_risk_tolerance(self, value: float) -> "PortfolioOptimizerBase":
        clone = copy.copy(self)
        clone.risk_tolerance = value
        return clone

    @property
    def risk_aversion(self) -> float:
        return 1.0 + (10.0 - self._risk_tolerance) * 1.5

    def prepare(
        self, historical_data: pd.DataFrame
    ) -> Tuple[pd.DataFrame, List[str], pd.DataFrame]:
        prices = clean_prices(historical_data)
        assets = asset_columns(prices)
        if not assets:
            raise ValueError("Market data contains no tradable assets")
        returns = prices.pct_change().dropna()
        if len(returns) < MIN_OBSERVATIONS:
            raise ValueError(
                f"At least {MIN_OBSERVATIONS + 1} price observations are required"
            )
        return prices, assets, returns

    def expected_returns(self, historical_data: pd.DataFrame) -> pd.Series:
        raise NotImplementedError

    def annual_covariance(self, asset_returns: pd.DataFrame) -> pd.DataFrame:
        values = asset_returns.to_numpy(dtype=float)
        try:
            covariance = LedoitWolf().fit(values).covariance_
        except Exception as error:
            logger.warning("Shrinkage covariance failed (%s); using sample", error)
            covariance = np.cov(values, rowvar=False)
        covariance = np.atleast_2d(covariance) * TRADING_DAYS
        return pd.DataFrame(
            covariance, index=asset_returns.columns, columns=asset_returns.columns
        )

    def solve(
        self,
        mu: np.ndarray,
        covariance: np.ndarray,
        gamma: float,
        min_weight: float,
        max_weight: float,
        target_return: Optional[float] = None,
        variance_only: bool = False,
    ) -> np.ndarray:
        n_assets = len(mu)
        bounds = [(min_weight, max_weight)] * n_assets
        constraints: List[Dict[str, Any]] = [
            {
                "type": "eq",
                "fun": lambda w: float(np.sum(w) - 1.0),
                "jac": lambda w: np.ones(n_assets),
            }
        ]
        if target_return is not None:
            constraints.append(
                {
                    "type": "eq",
                    "fun": lambda w: float(mu @ w - target_return),
                    "jac": lambda w: mu,
                }
            )
        if variance_only:

            def objective(w: np.ndarray) -> float:
                return float(0.5 * w @ covariance @ w)

            def gradient(w: np.ndarray) -> np.ndarray:
                return covariance @ w

        else:

            def objective(w: np.ndarray) -> float:
                return float(-(mu @ w) + 0.5 * gamma * (w @ covariance @ w))

            def gradient(w: np.ndarray) -> np.ndarray:
                return -mu + gamma * (covariance @ w)

        starts = [np.full(n_assets, 1.0 / n_assets)]
        rng = np.random.default_rng(0)
        starts.append(rng.dirichlet(np.ones(n_assets)))
        best: Optional[np.ndarray] = None
        best_value = math.inf
        for start in starts:
            start = np.clip(start, min_weight, max_weight)
            start = start / start.sum()
            result = minimize(
                objective,
                start,
                jac=gradient,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 500, "ftol": 1e-10},
            )
            if result.success and result.fun < best_value:
                best, best_value = result.x, result.fun
                break
        if best is None:
            raise ArithmeticError("Portfolio optimization did not converge")
        weights = np.clip(best, min_weight, max_weight)
        weights = np.where(weights < 1e-8, 0.0, weights)
        return weights / weights.sum()

    def portfolio_metrics(
        self, weights: np.ndarray, mu: np.ndarray, covariance: np.ndarray
    ) -> Dict[str, float]:
        expected_return = float(mu @ weights)
        volatility = float(math.sqrt(max(float(weights @ covariance @ weights), 0.0)))
        sharpe = (expected_return - RISK_FREE_RATE) / (volatility + 1e-12)
        return {
            "expected_return": expected_return,
            "volatility": volatility,
            "sharpe_ratio": float(sharpe),
        }

    def solve_max_sharpe(
        self,
        mu: np.ndarray,
        covariance: np.ndarray,
        min_weight: float,
        max_weight: float,
    ) -> np.ndarray:
        n_assets = len(mu)

        def objective(w: np.ndarray) -> float:
            variance = max(float(w @ covariance @ w), 1e-14)
            return float(-(mu @ w - RISK_FREE_RATE) / math.sqrt(variance))

        constraints = [{"type": "eq", "fun": lambda w: float(np.sum(w) - 1.0)}]
        bounds = [(min_weight, max_weight)] * n_assets
        rng = np.random.default_rng(0)
        starts = [np.full(n_assets, 1.0 / n_assets)]
        starts.extend(rng.dirichlet(np.ones(n_assets)) for _ in range(4))
        best: Optional[np.ndarray] = None
        best_value = math.inf
        for start in starts:
            start = np.clip(start, min_weight, max_weight)
            start = start / start.sum()
            result = minimize(
                objective,
                start,
                method="SLSQP",
                bounds=bounds,
                constraints=constraints,
                options={"maxiter": 500, "ftol": 1e-12},
            )
            if result.success and result.fun < best_value:
                best, best_value = result.x, result.fun
        if best is None:
            raise ArithmeticError("Portfolio optimization did not converge")
        weights = np.clip(best, min_weight, max_weight)
        weights = np.where(weights < 1e-8, 0.0, weights)
        return weights / weights.sum()

    def optimize_portfolio(
        self,
        historical_data: pd.DataFrame,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        method: str = "utility",
    ) -> Tuple[Dict[str, float], Dict[str, float]]:
        if method not in OPTIMIZATION_METHODS:
            raise ValueError(f"method must be one of {', '.join(OPTIMIZATION_METHODS)}")
        prices, assets, returns = self.prepare(historical_data)
        if len(assets) < 2:
            raise ValueError("At least two assets are required for optimization")
        lower, upper = validate_weight_bounds(len(assets), min_weight, max_weight)
        mu = self.expected_returns(prices).reindex(assets).to_numpy(dtype=float)
        covariance = self.annual_covariance(returns[assets]).to_numpy(dtype=float)
        if method == "max_sharpe":
            weights = self.solve_max_sharpe(mu, covariance, lower, upper)
        elif method == "min_variance":
            weights = self.solve(mu, covariance, 1.0, lower, upper, variance_only=True)
        else:
            weights = self.solve(mu, covariance, self.risk_aversion, lower, upper)
        metrics = self.portfolio_metrics(weights, mu, covariance)
        return {
            asset: float(w) for asset, w in zip(assets, weights, strict=False)
        }, metrics

    def efficient_frontier(
        self,
        historical_data: pd.DataFrame,
        points: int = 20,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
    ) -> List[Dict[str, Any]]:
        prices, assets, returns = self.prepare(historical_data)
        if len(assets) < 2:
            raise ValueError("At least two assets are required for the frontier")
        if int(points) < 2:
            raise ValueError("points must be at least 2")
        lower, upper = validate_weight_bounds(len(assets), min_weight, max_weight)
        mu = self.expected_returns(prices).reindex(assets).to_numpy(dtype=float)
        covariance = self.annual_covariance(returns[assets]).to_numpy(dtype=float)
        min_variance = self.solve(mu, covariance, 1.0, lower, upper, variance_only=True)
        max_return = self.solve(mu, covariance, 0.0, lower, upper)
        low_target = float(mu @ min_variance)
        high_target = max(float(mu @ max_return), low_target)
        frontier: List[Dict[str, Any]] = []
        for target in np.linspace(low_target, high_target, int(points)):
            try:
                weights = self.solve(
                    mu,
                    covariance,
                    1.0,
                    lower,
                    upper,
                    target_return=float(target),
                    variance_only=True,
                )
            except ArithmeticError:
                continue
            metrics = self.portfolio_metrics(weights, mu, covariance)
            metrics["weights"] = {
                a: float(w) for a, w in zip(assets, weights, strict=False)
            }
            frontier.append(metrics)
        if not frontier:
            raise ArithmeticError("Efficient frontier could not be computed")
        return frontier

    def monte_carlo_simulation(
        self,
        historical_data: pd.DataFrame,
        optimal_weights: Dict[str, float],
        num_simulations: int = 1000,
        time_horizon: int = 252,
        initial_value: float = 10000.0,
        seed: Optional[int] = None,
    ) -> Tuple[pd.DataFrame, Dict[str, float]]:
        _, assets, returns = self.prepare(historical_data)
        if int(num_simulations) < 1 or int(time_horizon) < 1:
            raise ValueError("num_simulations and time_horizon must be positive")
        unknown = [name for name in optimal_weights if name not in assets]
        if unknown:
            raise ValueError(f"Weights reference unknown assets: {sorted(unknown)}")
        weights = np.array([float(optimal_weights.get(a, 0.0)) for a in assets])
        if (weights < 0).any() or not np.isfinite(weights).all():
            raise ValueError("Weights must be finite and non-negative")
        total = weights.sum()
        if total <= 0:
            raise ValueError("Weights must sum to a positive value")
        weights = weights / total
        portfolio_returns = returns[assets].to_numpy(dtype=float) @ weights
        mean = float(portfolio_returns.mean())
        sigma = float(portfolio_returns.std(ddof=1))
        rng = np.random.default_rng(seed)
        draws = rng.normal(mean, sigma, size=(int(time_horizon), int(num_simulations)))
        draws = np.clip(draws, -0.99, None)
        paths = initial_value * np.cumprod(1.0 + draws, axis=0)
        final_values = paths[-1]
        running_max = np.maximum.accumulate(
            np.vstack([np.full(paths.shape[1], initial_value), paths]), axis=0
        )[1:]
        drawdowns = paths / running_max - 1.0
        risk_metrics = {
            "expected_final_value": float(final_values.mean()),
            "var_95": float(max(initial_value - np.percentile(final_values, 5), 0.0)),
            "var_99": float(max(initial_value - np.percentile(final_values, 1), 0.0)),
            "max_drawdown": float(abs(drawdowns.min(axis=0).mean())),
        }
        return pd.DataFrame(paths), risk_metrics


class ClassicalPortfolioOptimizer(PortfolioOptimizerBase):
    model_type = "classical"
    trained = True

    def expected_returns(self, historical_data: pd.DataFrame) -> pd.Series:
        prices = clean_prices(historical_data)
        assets = asset_columns(prices)
        returns = prices[assets].pct_change().dropna()
        return returns.mean() * TRADING_DAYS


class AdvancedPortfolioOptimizer(PortfolioOptimizerBase):
    model_type = "ml"

    def __init__(
        self,
        risk_tolerance: float = 5,
        n_estimators: int = 100,
        max_depth: int = 5,
        random_state: int = 42,
    ) -> None:
        super().__init__(risk_tolerance)
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.return_model: Optional[RandomForestRegressor] = None
        self.feature_names: List[str] = list(FEATURE_NAMES)
        self.training_summary: Dict[str, Any] = {}
        self.trained = False

    def feature_frame(self, prices: pd.DataFrame) -> pd.DataFrame:
        assets = asset_columns(prices)
        returns = prices[assets].pct_change()
        mean_return = returns.mean(axis=1)
        if MARKET_COLUMN in prices.columns:
            market_return = prices[MARKET_COLUMN].pct_change()
        else:
            market_return = mean_return
        features = pd.DataFrame(index=returns.index)
        features["lag_0"] = mean_return
        features["lag_1"] = mean_return.shift(1)
        features["lag_2"] = mean_return.shift(2)
        features["mean_5d"] = mean_return.rolling(5).mean()
        features["volatility_5d"] = returns.rolling(5).std().mean(axis=1)
        features["volatility_20d"] = returns.rolling(20).std().mean(axis=1)
        features["market_return"] = market_return
        return features[list(FEATURE_NAMES)]

    def preprocess_data(
        self, historical_data: pd.DataFrame, fit: bool = True
    ) -> Tuple[np.ndarray, pd.Series]:
        prices = clean_prices(historical_data)
        assets = asset_columns(prices)
        if not assets:
            raise ValueError("Market data contains no tradable assets")
        features = self.feature_frame(prices)
        target = prices[assets].pct_change().mean(axis=1).shift(-1).rename("target")
        dataset = features.join(target).dropna()
        if len(dataset) < MIN_TRAINING_ROWS:
            raise ValueError(
                f"At least {MIN_TRAINING_ROWS} usable training rows are required, "
                f"got {len(dataset)}"
            )
        matrix = dataset[self.feature_names]
        if fit:
            scaled = self.scaler.fit_transform(matrix)
        else:
            scaled = self.scaler.transform(matrix)
        return scaled, dataset["target"]

    def train_return_prediction_model(
        self, historical_data: pd.DataFrame
    ) -> RandomForestRegressor:
        X, y = self.preprocess_data(historical_data, fit=True)
        model = RandomForestRegressor(
            n_estimators=self.n_estimators,
            max_depth=self.max_depth,
            random_state=self.random_state,
            n_jobs=1,
        )
        model.fit(X, y)
        self.return_model = model
        self.trained = True
        self.training_summary = {
            "samples": int(len(y)),
            "features": list(self.feature_names),
            "trained_at": datetime.now(timezone.utc).isoformat(),
        }
        return model

    def evaluate(self, historical_data: pd.DataFrame) -> Dict[str, float]:
        if not self.trained or self.return_model is None:
            raise ValueError("Model must be trained before evaluation")
        X, y = self.preprocess_data(historical_data, fit=False)
        predictions = self.return_model.predict(X)
        r2 = float(r2_score(y, predictions)) if len(y) > 1 else float("nan")
        return {
            "mse": float(mean_squared_error(y, predictions)),
            "r2": r2 if math.isfinite(r2) else 0.0,
            "samples": int(len(y)),
        }

    def predict_returns(self, historical_data: pd.DataFrame) -> Dict[str, float]:
        if not self.trained or self.return_model is None:
            self.train_return_prediction_model(historical_data)
        prices = clean_prices(historical_data)
        assets = asset_columns(prices)
        features = self.feature_frame(prices).dropna()
        if features.empty:
            raise ValueError("Not enough history to build prediction features")
        latest = self.scaler.transform(features[self.feature_names].iloc[[-1]])
        predicted_daily = float(self.return_model.predict(latest)[0])
        market_annual = predicted_daily * TRADING_DAYS
        returns = prices.pct_change().dropna()
        if MARKET_COLUMN in returns.columns:
            market_returns = returns[MARKET_COLUMN]
        else:
            market_returns = returns[assets].mean(axis=1)
        market_variance = float(market_returns.var())
        predictions: Dict[str, float] = {}
        for asset in assets:
            if market_variance > 1e-14:
                beta = float(returns[asset].cov(market_returns) / market_variance)
            else:
                beta = 1.0
            predictions[asset] = RISK_FREE_RATE + beta * (
                market_annual - RISK_FREE_RATE
            )
        return predictions

    def calculate_risk_adjusted_returns(
        self, historical_data: pd.DataFrame
    ) -> Dict[str, float]:
        predicted = self.predict_returns(historical_data)
        confidence = float(
            np.clip(0.5 + (self.risk_tolerance - 5.0) / 10.0, 0.05, 0.95)
        )
        return {
            asset: (1.0 - confidence) * PRIOR_ANNUAL_RETURN + confidence * value
            for asset, value in predicted.items()
        }

    def expected_returns(self, historical_data: pd.DataFrame) -> pd.Series:
        return pd.Series(self.calculate_risk_adjusted_returns(historical_data))

    def save_model(self, filepath: str) -> None:
        if not self.trained or self.return_model is None:
            raise ValueError("Model must be trained before saving")
        directory = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(directory, exist_ok=True)
        temporary = f"{filepath}.tmp"
        joblib.dump(
            {
                "format_version": MODEL_FORMAT_VERSION,
                "model": self.return_model,
                "scaler": self.scaler,
                "risk_tolerance": self.risk_tolerance,
                "feature_names": list(self.feature_names),
                "training_summary": self.training_summary,
            },
            temporary,
        )
        os.replace(temporary, filepath)
        logger.info("Model saved to %s", filepath)

    @classmethod
    def load_model(cls, filepath: str) -> "AdvancedPortfolioOptimizer":
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        saved = joblib.load(filepath)
        required = {"model", "scaler", "risk_tolerance", "feature_names"}
        if (
            not isinstance(saved, dict)
            or saved.get("format_version") != MODEL_FORMAT_VERSION
            or not required.issubset(saved)
        ):
            raise ValueError(f"Unsupported model file format: {filepath}")
        if list(saved["feature_names"]) != list(FEATURE_NAMES):
            raise ValueError(
                f"Model features do not match the current code: {filepath}"
            )
        instance = cls(risk_tolerance=saved["risk_tolerance"])
        instance.return_model = saved["model"]
        instance.scaler = saved["scaler"]
        instance.feature_names = list(saved["feature_names"])
        instance.training_summary = dict(saved.get("training_summary", {}))
        instance.trained = True
        return instance
