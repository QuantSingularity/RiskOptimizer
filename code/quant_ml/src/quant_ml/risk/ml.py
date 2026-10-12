import logging
import os
from typing import Dict, Optional

import joblib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from quant_ml.risk.common import as_frame, validate_confidence, weight_vector
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODEL_TYPES = ("gbm", "rf", "nn")
MODEL_FORMAT_VERSION = 2
MIN_WINDOW = 5
MIN_TRAIN_ROWS = 60
EPSILON = 1e-12
FEATURE_CLIP = 5.0
ES_LEVELS = 5


def pinball_loss(actual: np.ndarray, predicted: np.ndarray, level: float) -> float:
    errors = actual - predicted
    return float(np.mean(np.where(errors >= 0, level * errors, (level - 1.0) * errors)))


class MLRiskModel:
    def __init__(
        self, model_type: str = "gbm", quantile: float = 0.05, random_state: int = 42
    ) -> None:
        if model_type not in MODEL_TYPES:
            raise ValueError(f"Unsupported model type: {model_type}")
        if isinstance(quantile, bool) or not 0.0 < float(quantile) < 0.5:
            raise ValueError("quantile must be between 0 and 0.5")
        self.model_type = model_type
        self.quantile = float(quantile)
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = None
        self.quantile_models: Dict[float, GradientBoostingRegressor] = {}
        self.residuals: Optional[np.ndarray] = None
        self.feature_names: Optional[list] = None
        self.feature_importance: Optional[pd.DataFrame] = None
        self.asset_names: Optional[list] = None
        self.weights: Optional[np.ndarray] = None
        self.feature_window: Optional[int] = None
        self.horizon: int = 1
        self.target_scale: float = 1.0
        self.metrics: Dict[str, float] = {}
        self.train_features: Optional[np.ndarray] = None
        self.train_target: Optional[np.ndarray] = None
        self.trained = False

    def new_quantile_model(self, level: float) -> GradientBoostingRegressor:
        return GradientBoostingRegressor(
            loss="quantile",
            alpha=level,
            n_estimators=100,
            max_depth=3,
            learning_rate=0.07,
            subsample=0.8,
            max_features=0.5,
            random_state=self.random_state,
        )

    def new_mean_model(self):
        if self.model_type == "rf":
            return RandomForestRegressor(
                n_estimators=150,
                max_depth=6,
                min_samples_leaf=5,
                oob_score=True,
                n_jobs=1,
                random_state=self.random_state,
            )
        return MLPRegressor(
            hidden_layer_sizes=(32, 16),
            alpha=1e-3,
            max_iter=500,
            early_stopping=True,
            random_state=self.random_state,
        )

    def build_features(self, frame: pd.DataFrame, window: int) -> np.ndarray:
        columns = []
        names = []
        series_map = {column: frame[column] for column in frame.columns}
        if frame.shape[1] > 1:
            series_map["market"] = pd.Series(
                frame.to_numpy() @ self.weights, index=frame.index
            )
        for name, series in series_map.items():
            roll = series.rolling(window)
            std = roll.std(ddof=0)
            parts = {
                "mean": roll.mean(),
                "std": std,
                "norm_min": roll.min() / (std + EPSILON),
            }
            if name != "market":
                parts["skew"] = roll.skew()
                parts["kurt"] = roll.kurt()
            for part, values in parts.items():
                columns.append(values.to_numpy())
                names.append(f"{name}_{part}")
        matrix = np.column_stack(columns)[window - 1 :]
        if self.feature_names is None:
            self.feature_names = names
        return np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)

    def build_targets(
        self, frame: pd.DataFrame, window: int, horizon: int
    ) -> np.ndarray:
        portfolio = frame.to_numpy() @ self.weights
        n_rows = len(portfolio) - window - horizon + 1
        if n_rows < 1:
            raise ValueError(
                "Not enough observations for the requested window and horizon"
            )
        future = np.lib.stride_tricks.sliding_window_view(portfolio[window:], horizon)
        return -future.min(axis=1)[:n_rows]

    def fit(
        self,
        returns,
        feature_window: int = 10,
        horizon: int = 1,
        test_size: float = 0.2,
        weights=None,
    ) -> "MLRiskModel":
        if (
            isinstance(feature_window, bool)
            or not isinstance(feature_window, (int, np.integer))
            or feature_window < MIN_WINDOW
        ):
            raise ValueError(
                f"feature_window must be an integer of at least {MIN_WINDOW}"
            )
        if (
            isinstance(horizon, bool)
            or not isinstance(horizon, (int, np.integer))
            or horizon < 1
        ):
            raise ValueError("horizon must be a positive integer")
        if not 0.05 <= float(test_size) <= 0.5:
            raise ValueError("test_size must be between 0.05 and 0.5")
        frame = as_frame(returns, min_rows=feature_window + horizon + MIN_TRAIN_ROWS)
        self.asset_names = list(frame.columns)
        self.weights = weight_vector(weights, self.asset_names)
        self.feature_window = int(feature_window)
        self.horizon = int(horizon)
        self.feature_names = None
        features = self.build_features(frame, self.feature_window)
        target = self.build_targets(frame, self.feature_window, self.horizon)
        features = features[: len(target)]
        split = int(len(target) * (1.0 - test_size))
        if split < MIN_TRAIN_ROWS or len(target) - split < 10:
            raise ValueError("Not enough observations for a train and test split")
        x_train = self.transform(features[:split], fit=True)
        x_test = self.transform(features[split:])
        y_train, y_test = target[:split], target[split:]
        self.train_features = np.vstack([x_train, x_test])
        self.train_target = target
        self.quantile_models = {}
        level = 1.0 - self.quantile
        if self.model_type == "gbm":
            model = self.new_quantile_model(level)
            model.fit(x_train, y_train)
            self.model = model
            self.quantile_models[round(level, 6)] = model
            test_prediction = model.predict(x_test)
            self.residuals = y_train - model.predict(x_train)
        else:
            model = self.new_mean_model()
            self.target_scale = float(np.std(y_train)) or 1.0
            model.fit(x_train, y_train / self.target_scale)
            self.model = model
            test_prediction = model.predict(x_test) * self.target_scale
            if self.model_type == "rf":
                self.residuals = y_train - model.oob_prediction_ * self.target_scale
            else:
                self.residuals = y_test - test_prediction
        self.metrics = {
            "test_pinball_loss": pinball_loss(y_test, test_prediction, level),
            "test_coverage": (
                float(np.mean(y_test <= test_prediction))
                if self.model_type == "gbm"
                else float(np.nan)
            ),
            "train_rows": int(split),
            "test_rows": int(len(y_test)),
        }
        if hasattr(model, "feature_importances_"):
            self.feature_importance = pd.DataFrame(
                {
                    "feature": self.feature_names,
                    "importance": model.feature_importances_,
                }
            ).sort_values("importance", ascending=False)
        self.trained = True
        logger.info("MLRiskModel (%s) trained on %d rows", self.model_type, split)
        return self

    def transform(self, features: np.ndarray, fit: bool = False) -> np.ndarray:
        scaled = (
            self.scaler.fit_transform(features)
            if fit
            else self.scaler.transform(features)
        )
        return np.clip(scaled, -FEATURE_CLIP, FEATURE_CLIP)

    def require_trained(self) -> None:
        if not self.trained:
            raise ValueError("Model must be trained before prediction")

    def prepare(self, returns, feature_window: Optional[int]) -> np.ndarray:
        self.require_trained()
        if feature_window is not None and feature_window != self.feature_window:
            raise ValueError(
                f"feature_window must match the trained window of {self.feature_window}"
            )
        frame = as_frame(returns, min_rows=self.feature_window)
        if list(frame.columns) != self.asset_names and frame.shape[1] == len(
            self.asset_names
        ):
            frame.columns = self.asset_names
        if list(frame.columns) != self.asset_names:
            raise ValueError(
                f"returns must contain the trained assets: {self.asset_names}"
            )
        features = self.build_features(frame, self.feature_window)
        return self.transform(features)

    def quantile_prediction(self, features: np.ndarray, level: float) -> np.ndarray:
        key = round(level, 6)
        if key not in self.quantile_models:
            model = self.new_quantile_model(level)
            model.fit(self.train_features, self.train_target)
            self.quantile_models[key] = model
        return self.quantile_models[key].predict(features)

    def mean_prediction(self, features: np.ndarray) -> np.ndarray:
        return self.model.predict(features) * self.target_scale

    def predict_var(
        self, returns, confidence: float = 0.95, feature_window: Optional[int] = None
    ) -> np.ndarray:
        confidence = validate_confidence(confidence)
        features = self.prepare(returns, feature_window)
        if self.model_type == "gbm":
            prediction = self.quantile_prediction(features, confidence)
        else:
            prediction = self.mean_prediction(features) + float(
                np.quantile(self.residuals, confidence)
            )
        return np.maximum(prediction, 0.0)

    def predict_es(
        self,
        returns,
        confidence: float = 0.95,
        feature_window: Optional[int] = None,
        n_samples: Optional[int] = None,
    ) -> np.ndarray:
        confidence = validate_confidence(confidence)
        features = self.prepare(returns, feature_window)
        var = self.predict_var(returns, confidence, feature_window)
        if self.model_type == "gbm":
            levels = np.linspace(
                confidence,
                min(0.9995, confidence + (1.0 - confidence) * 0.95),
                ES_LEVELS,
            )
            ladder = np.vstack(
                [self.quantile_prediction(features, float(level)) for level in levels]
            )
            es = np.sort(ladder, axis=0).mean(axis=0)
        else:
            cutoff = np.quantile(self.residuals, confidence)
            tail = self.residuals[self.residuals >= cutoff]
            es = self.mean_prediction(features) + float(tail.mean())
        return np.maximum(es, var)

    def forecast_var(self, returns, confidence: float = 0.95) -> float:
        return float(self.predict_var(returns, confidence)[-1])

    def forecast_es(self, returns, confidence: float = 0.95) -> float:
        return float(self.predict_es(returns, confidence)[-1])

    def plot_feature_importance(self, top_n: int = 10) -> plt.Figure:
        if not self.trained or self.feature_importance is None:
            raise ValueError(
                "Model must be trained with a model that supports feature importance"
            )
        top = self.feature_importance.head(top_n)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.barh(top["feature"], top["importance"])
        ax.set_xlabel("Importance")
        ax.set_ylabel("Feature")
        ax.set_title(f"Top {top_n} Feature Importance")
        fig.tight_layout()
        return fig

    def save_model(self, filepath: str) -> None:
        self.require_trained()
        directory = os.path.dirname(os.path.abspath(filepath))
        os.makedirs(directory, exist_ok=True)
        temporary = f"{filepath}.tmp"
        joblib.dump(
            {"format_version": MODEL_FORMAT_VERSION, "state": self.__dict__}, temporary
        )
        os.replace(temporary, filepath)
        logger.info("Model saved to %s", filepath)

    @classmethod
    def load_model(cls, filepath: str) -> "MLRiskModel":
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Model file not found: {filepath}")
        saved = joblib.load(filepath)
        if (
            not isinstance(saved, dict)
            or saved.get("format_version") != MODEL_FORMAT_VERSION
        ):
            raise ValueError(f"Unsupported model file format: {filepath}")
        instance = cls(saved["state"]["model_type"], saved["state"]["quantile"])
        instance.__dict__.update(saved["state"])
        return instance
