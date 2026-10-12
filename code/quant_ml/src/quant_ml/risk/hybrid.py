import logging
from typing import Dict, Optional, Sequence

import numpy as np
from quant_ml.risk.common import as_frame, level_key, validate_confidence, weight_vector
from quant_ml.risk.copula import CopulaMLRiskModel
from quant_ml.risk.ml import MLRiskModel

logger = logging.getLogger(__name__)


class HybridRiskModel:
    def __init__(
        self,
        traditional_weight: float = 0.5,
        ml_model_type: str = "gbm",
        copula_type: str = "gaussian",
        seed: Optional[int] = None,
    ) -> None:
        if (
            isinstance(traditional_weight, bool)
            or not 0.0 <= float(traditional_weight) <= 1.0
        ):
            raise ValueError("traditional_weight must be between 0 and 1")
        self.traditional_weight = float(traditional_weight)
        self.ml_weight = 1.0 - self.traditional_weight
        self.ml_model = MLRiskModel(model_type=ml_model_type)
        self.copula_model = CopulaMLRiskModel(copula_type=copula_type, seed=seed)
        self.weights: Optional[np.ndarray] = None
        self.trained = False

    def fit(
        self,
        returns,
        feature_window: int = 10,
        horizon: int = 1,
        weights=None,
    ) -> "HybridRiskModel":
        frame = as_frame(returns, min_rows=feature_window + horizon + 60)
        self.weights = weight_vector(weights, list(frame.columns))
        self.ml_model.fit(frame, feature_window, horizon, weights=self.weights)
        self.copula_model.fit(frame)
        self.trained = True
        logger.info(
            "Hybrid model fitted with traditional weight %s", self.traditional_weight
        )
        return self

    def require_trained(self, action: str) -> None:
        if not self.trained:
            raise ValueError(f"Model must be trained before {action}")

    def components(
        self, returns, weights, confidence: float, feature_window: Optional[int]
    ) -> Dict[str, float]:
        confidence = validate_confidence(confidence)
        if returns is None and weights is None:
            raise ValueError("Either returns or weights must be provided")
        parts: Dict[str, float] = {}
        if returns is not None:
            parts["ml_var"] = float(
                self.ml_model.predict_var(returns, confidence, feature_window)[-1]
            )
            parts["ml_es"] = float(
                self.ml_model.predict_es(returns, confidence, feature_window)[-1]
            )
        if weights is not None:
            values = self.copula_model.portfolio_scenarios(weights)
            from quant_ml.risk.common import historical_var_es

            parts["copula_var"], parts["copula_es"] = historical_var_es(
                values, confidence
            )
        return parts

    def blend(self, parts: Dict[str, float]) -> Dict[str, float]:
        if "ml_var" in parts and "copula_var" in parts:
            var = (
                self.traditional_weight * parts["copula_var"]
                + self.ml_weight * parts["ml_var"]
            )
            es = (
                self.traditional_weight * parts["copula_es"]
                + self.ml_weight * parts["ml_es"]
            )
        elif "ml_var" in parts:
            var, es = parts["ml_var"], parts["ml_es"]
        else:
            var, es = parts["copula_var"], parts["copula_es"]
        return {"var": var, "es": max(es, var)}

    def calculate_var(
        self,
        returns=None,
        weights=None,
        confidence: float = 0.95,
        feature_window: Optional[int] = None,
    ) -> float:
        self.require_trained("calculating VaR")
        return self.blend(
            self.components(returns, weights, confidence, feature_window)
        )["var"]

    def calculate_es(
        self,
        returns=None,
        weights=None,
        confidence: float = 0.95,
        feature_window: Optional[int] = None,
    ) -> float:
        self.require_trained("calculating ES")
        return self.blend(
            self.components(returns, weights, confidence, feature_window)
        )["es"]

    def calculate_risk_metrics(
        self,
        returns=None,
        weights=None,
        confidence_levels: Sequence[float] = (0.95, 0.99),
        feature_window: Optional[int] = None,
    ) -> dict:
        self.require_trained("calculating risk metrics")
        metrics: dict = {}
        for confidence in confidence_levels:
            blended = self.blend(
                self.components(returns, weights, confidence, feature_window)
            )
            key = level_key(confidence)
            metrics[f"var_{key}"] = blended["var"]
            metrics[f"es_{key}"] = blended["es"]
        if weights is not None:
            copula_metrics = self.copula_model.calculate_risk_metrics(
                weights, confidence_levels
            )
            for key in ("mean", "std", "skewness", "kurtosis"):
                metrics[key] = copula_metrics[key]
        return metrics
