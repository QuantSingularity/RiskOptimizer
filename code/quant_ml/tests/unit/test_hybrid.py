import numpy as np
import pytest
from risk.hybrid import HybridRiskModel


@pytest.fixture(scope="module")
def hybrid(returns_frame):
    return HybridRiskModel(0.5, "rf", seed=1).fit(
        returns_frame, weights=[0.5, 0.3, 0.2]
    )


class TestHybrid:
    def test_blend_lies_between_components(self, hybrid, returns_frame):
        weights = [0.5, 0.3, 0.2]
        parts = hybrid.components(returns_frame, weights, 0.95, None)
        low, high = sorted([parts["ml_var"], parts["copula_var"]])
        assert (
            low - 1e-12
            <= hybrid.calculate_var(returns_frame, weights, 0.95)
            <= high + 1e-12
        )

    def test_traditional_weight_extremes(self, returns_frame):
        weights = [0.5, 0.3, 0.2]
        copula_only = HybridRiskModel(1.0, "rf", seed=1).fit(
            returns_frame, weights=weights
        )
        parts = copula_only.components(returns_frame, weights, 0.95, None)
        assert copula_only.calculate_var(returns_frame, weights, 0.95) == pytest.approx(
            parts["copula_var"]
        )
        ml_only = HybridRiskModel(0.0, "rf", seed=1).fit(returns_frame, weights=weights)
        parts = ml_only.components(returns_frame, weights, 0.95, None)
        assert ml_only.calculate_var(returns_frame, weights, 0.95) == pytest.approx(
            parts["ml_var"]
        )

    def test_es_dominates_var(self, hybrid, returns_frame):
        weights = [0.5, 0.3, 0.2]
        assert hybrid.calculate_es(
            returns_frame, weights, 0.95
        ) >= hybrid.calculate_var(returns_frame, weights, 0.95)

    def test_single_source_modes(self, hybrid, returns_frame):
        assert hybrid.calculate_var(returns=None, weights=[0.5, 0.3, 0.2]) > 0
        assert hybrid.calculate_var(returns=returns_frame) > 0

    def test_metrics_keys_do_not_truncate(self, hybrid, returns_frame):
        metrics = hybrid.calculate_risk_metrics(
            returns_frame, [0.5, 0.3, 0.2], [0.57, 0.975]
        )
        assert {"var_57", "es_57", "var_97_5", "es_97_5", "mean", "std"} <= set(metrics)

    def test_ml_target_uses_the_same_weights_as_the_copula(self, hybrid):
        assert np.allclose(hybrid.ml_model.weights, [0.5, 0.3, 0.2])

    def test_validation(self, returns_frame):
        with pytest.raises(ValueError):
            HybridRiskModel(1.5)
        with pytest.raises(ValueError):
            HybridRiskModel().calculate_var(returns_frame)
        with pytest.raises(ValueError):
            HybridRiskModel(0.5, "rf").fit(returns_frame).calculate_var()
