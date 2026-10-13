import logging
import os
import threading
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from src.core.config import config
from src.core.exceptions import CalculationError, ModelError, ValidationError
from src.services.quant_ml_bridge import ensure_quant_ml

ensure_quant_ml()

QUANT_ML_IMPORT_ERROR: Optional[Exception] = None

try:
    from data.loaders import available_symbols, load_close_prices
    from forecasting import price as forecast_module
    from forecasting import sentiment as sentiment_module
    from optimization.portfolio import (
        MARKET_COLUMN,
        AdvancedPortfolioOptimizer,
        ClassicalPortfolioOptimizer,
    )
    from settings import default_model_path
except ImportError as import_error:
    QUANT_ML_IMPORT_ERROR = import_error
    forecast_module = None
    sentiment_module = None
    available_symbols = None
    load_close_prices = None
    AdvancedPortfolioOptimizer = None
    ClassicalPortfolioOptimizer = None
    default_model_path = None
    MARKET_COLUMN = "market_index"

logger = logging.getLogger(__name__)

MAX_ROWS = 5000
MAX_ASSETS = 50
MAX_SIMULATIONS = 20000
MAX_HORIZON = 2520
MAX_FRONTIER_POINTS = 100
SIMULATION_PERCENTILES = [5, 25, 50, 75, 95]
MODEL_PATH = config.model_path or (
    str(default_model_path()) if default_model_path else None
)
AUTO_TRAIN = os.getenv("AI_AUTO_TRAIN", "true").strip().lower() not in {
    "0",
    "false",
    "no",
}


def optimizer_error(error: Exception, operation: str) -> Exception:
    if isinstance(error, (ValidationError, ModelError, CalculationError)):
        return error
    if isinstance(error, (ValueError, TypeError, KeyError)):
        return ValidationError(str(error))
    return CalculationError(f"{operation} failed: {error}", operation)


class AIOptimizationService:
    def __init__(
        self,
        model_path: Optional[str] = None,
        auto_train: Optional[bool] = None,
    ) -> None:
        if QUANT_ML_IMPORT_ERROR is not None:
            raise ModelError(
                f"quant_ml package is unavailable: {QUANT_ML_IMPORT_ERROR}",
                "quant_ml",
            )
        self.model_path = str(model_path or MODEL_PATH)
        self.auto_train = AUTO_TRAIN if auto_train is None else auto_train
        self.optimizer: Any = None
        self.mode = "unloaded"
        self.load_error: Optional[str] = None
        self.lock = threading.Lock()
        self.load_model()

    def load_model(self) -> None:
        with self.lock:
            self.load_error = None
            if os.path.exists(self.model_path):
                try:
                    self.optimizer = AdvancedPortfolioOptimizer.load_model(
                        self.model_path
                    )
                    self.mode = "ml"
                    logger.info("Loaded optimization model from %s", self.model_path)
                    return
                except Exception as error:
                    self.load_error = str(error)
                    logger.warning("Could not load model (%s)", error)
            if self.auto_train and self.train_default_model():
                return
            self.optimizer = ClassicalPortfolioOptimizer()
            self.mode = "classical"
            logger.info("Using classical optimizer")

    def train_default_model(self) -> bool:
        try:
            from training.trainer import load_training_data

            data = load_training_data()
            optimizer = AdvancedPortfolioOptimizer()
            optimizer.train_return_prediction_model(data)
        except Exception as error:
            self.load_error = f"Automatic training failed: {error}"
            logger.warning(self.load_error)
            return False
        try:
            optimizer.save_model(self.model_path)
        except OSError as error:
            logger.warning("Trained model could not be saved (%s)", error)
        self.optimizer = optimizer
        self.mode = "ml"
        return True

    def retrain(
        self,
        symbols: Optional[List[str]] = None,
        risk_tolerance: float = 5,
    ) -> Dict[str, Any]:
        try:
            from training.trainer import train_and_save

            with self.lock:
                optimizer, report, path = train_and_save(
                    self.model_path, symbols, None, risk_tolerance
                )
                self.optimizer = optimizer
                self.mode = "ml"
                self.load_error = None
        except Exception as error:
            raise optimizer_error(error, "training")
        return {
            "model_path": path,
            "prediction_metrics": report["prediction_metrics"],
            "training_summary": optimizer.training_summary,
        }

    def to_frame(self, data: Any) -> pd.DataFrame:
        if isinstance(data, pd.DataFrame):
            frame = data.copy()
        elif isinstance(data, dict):
            try:
                frame = pd.DataFrame(data)
            except ValueError as error:
                raise ValidationError(f"Market data columns are inconsistent: {error}")
        elif isinstance(data, list):
            frame = pd.DataFrame(data)
        else:
            raise ValidationError("Market data must be an object or a list of records")
        if "date" in frame.columns:
            frame = frame.set_index("date")
        frame = frame.apply(pd.to_numeric, errors="coerce")
        if frame.empty:
            raise ValidationError("Market data is empty")
        if len(frame) > MAX_ROWS:
            raise ValidationError(f"Market data exceeds {MAX_ROWS} rows")
        if len(frame.columns) > MAX_ASSETS + 1:
            raise ValidationError(f"Market data exceeds {MAX_ASSETS} assets")
        return frame

    def market_data_for_symbols(
        self, symbols: List[str], minimum_symbols: int = 2
    ) -> pd.DataFrame:
        try:
            return load_close_prices(symbols, minimum_symbols=minimum_symbols)
        except FileNotFoundError as error:
            raise ValidationError(str(error), "symbols")
        except ValueError as error:
            raise ValidationError(str(error), "symbols")

    def resolve_data(
        self,
        market_data: Any = None,
        symbols: Optional[List[str]] = None,
        minimum_symbols: int = 2,
    ) -> pd.DataFrame:
        if market_data is not None:
            return self.to_frame(market_data)
        if symbols:
            return self.market_data_for_symbols(symbols, minimum_symbols)
        raise ValidationError("Provide either market_data or symbols")

    def optimizer_for(self, risk_tolerance: Any) -> Any:
        try:
            return self.optimizer.with_risk_tolerance(risk_tolerance)
        except ValueError as error:
            raise ValidationError(str(error), "risk_tolerance")

    def optimize_portfolio(
        self,
        market_data: Any = None,
        risk_tolerance: Any = 5,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        symbols: Optional[List[str]] = None,
        method: str = "utility",
    ) -> Dict[str, Any]:
        frame = self.resolve_data(market_data, symbols)
        optimizer = self.optimizer_for(risk_tolerance)
        try:
            weights, metrics = optimizer.optimize_portfolio(
                frame, min_weight=min_weight, max_weight=max_weight, method=method
            )
        except Exception as error:
            raise optimizer_error(error, "optimization")
        return {
            "optimized_allocation": {k: float(v) for k, v in weights.items()},
            "performance_metrics": {
                "expected_return": float(metrics["expected_return"]),
                "volatility": float(metrics["volatility"]),
                "sharpe_ratio": float(metrics["sharpe_ratio"]),
            },
            "model_type": self.mode,
            "method": method,
            "risk_tolerance": float(optimizer.risk_tolerance),
        }

    def efficient_frontier(
        self,
        market_data: Any = None,
        risk_tolerance: Any = 5,
        points: int = 20,
        min_weight: float = 0.0,
        max_weight: float = 1.0,
        symbols: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        if isinstance(points, bool) or not isinstance(points, int):
            raise ValidationError("points must be an integer", "points")
        if points < 2 or points > MAX_FRONTIER_POINTS:
            raise ValidationError(
                f"points must be between 2 and {MAX_FRONTIER_POINTS}", "points"
            )
        frame = self.resolve_data(market_data, symbols)
        optimizer = self.optimizer_for(risk_tolerance)
        try:
            frontier = optimizer.efficient_frontier(
                frame, points=points, min_weight=min_weight, max_weight=max_weight
            )
        except Exception as error:
            raise optimizer_error(error, "efficient frontier")
        return {"frontier": frontier, "model_type": self.mode}

    def run_risk_simulation(
        self,
        market_data: Any = None,
        weights: Optional[Dict[str, float]] = None,
        num_simulations: int = 1000,
        time_horizon: int = 252,
        symbols: Optional[List[str]] = None,
        initial_value: float = 10000.0,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        if not isinstance(weights, dict) or not weights:
            raise ValidationError("weights must be a non-empty object", "weights")
        for name, name_value in (
            ("num_simulations", num_simulations),
            ("time_horizon", time_horizon),
        ):
            if isinstance(name_value, bool) or not isinstance(name_value, int):
                raise ValidationError(f"{name} must be an integer", name)
        if not 1 <= num_simulations <= MAX_SIMULATIONS:
            raise ValidationError(
                f"num_simulations must be between 1 and {MAX_SIMULATIONS}",
                "num_simulations",
            )
        if not 1 <= time_horizon <= MAX_HORIZON:
            raise ValidationError(
                f"time_horizon must be between 1 and {MAX_HORIZON}", "time_horizon"
            )
        if (
            isinstance(initial_value, bool)
            or not isinstance(initial_value, (int, float))
            or not np.isfinite(initial_value)
            or initial_value <= 0
        ):
            raise ValidationError("initial_value must be positive", "initial_value")
        if symbols is None and market_data is None:
            symbols = list(weights.keys())
        frame = self.resolve_data(market_data, symbols, minimum_symbols=1)
        try:
            simulation, risk_metrics = self.optimizer.monte_carlo_simulation(
                frame,
                weights,
                num_simulations,
                time_horizon,
                float(initial_value),
                seed,
            )
        except Exception as error:
            raise optimizer_error(error, "risk simulation")
        final_values = simulation.iloc[-1].to_numpy()
        percentile_values = np.percentile(final_values, SIMULATION_PERCENTILES)
        return {
            "risk_metrics": {
                "expected_final_value": float(risk_metrics["expected_final_value"]),
                "value_at_risk_95": float(risk_metrics["var_95"]),
                "value_at_risk_99": float(risk_metrics["var_99"]),
                "max_drawdown": float(risk_metrics["max_drawdown"]),
            },
            "simulation_summary": {
                "initial_value": float(initial_value),
                "time_horizon_days": time_horizon,
                "num_simulations": num_simulations,
                "percentiles": {
                    f"p{p}": float(v)
                    for p, v in zip(SIMULATION_PERCENTILES, percentile_values)
                },
            },
        }

    def forecast(
        self, ticker: str, periods: int = 30, model: str = "auto"
    ) -> Dict[str, Any]:
        try:
            return forecast_module.forecast_prices(ticker, periods, model=model)
        except FileNotFoundError as error:
            raise ValidationError(str(error), "ticker")
        except Exception as error:
            raise optimizer_error(error, "forecast")

    def analyze_sentiment(self, texts: List[str]) -> Dict[str, Any]:
        if not isinstance(texts, list) or not texts:
            raise ValidationError("texts must be a non-empty list", "texts")
        if len(texts) > sentiment_module.MAX_SENTIMENT_TEXTS:
            raise ValidationError(
                f"texts must contain at most {sentiment_module.MAX_SENTIMENT_TEXTS} items",
                "texts",
            )
        for text in texts:
            if not isinstance(text, str) or not text.strip():
                raise ValidationError("Every text must be a non-empty string", "texts")
            if len(text) > sentiment_module.MAX_TEXT_LENGTH:
                raise ValidationError(
                    f"Each text must be at most {sentiment_module.MAX_TEXT_LENGTH} characters",
                    "texts",
                )
        try:
            frame = sentiment_module.analyze_sentiment(texts)
        except sentiment_module.AnalyticsUnavailableError as error:
            raise ModelError(str(error), "sentiment")
        except Exception as error:
            raise optimizer_error(error, "sentiment analysis")
        return {
            "summary": sentiment_module.summarize_sentiment(frame),
            "items": frame.to_dict(orient="records"),
        }

    def get_model_info(self) -> Dict[str, Any]:
        summary = getattr(self.optimizer, "training_summary", {}) or {}
        return {
            "model_path": self.model_path,
            "model_file_exists": os.path.exists(self.model_path),
            "model_loaded": self.mode == "ml",
            "model_type": type(self.optimizer).__name__ if self.optimizer else None,
            "mode": self.mode,
            "training_summary": summary,
            "load_error": self.load_error,
            "available_symbols": available_symbols(),
            "market_column": MARKET_COLUMN,
        }


_service: Optional[AIOptimizationService] = None
_service_lock = threading.Lock()


def get_ai_service() -> AIOptimizationService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = AIOptimizationService()
    return _service


def reset_ai_service() -> None:
    global _service
    with _service_lock:
        _service = None
