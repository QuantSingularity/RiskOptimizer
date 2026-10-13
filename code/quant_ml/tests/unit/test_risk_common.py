import numpy as np
import pandas as pd
import pytest
from risk.common import (
    as_frame,
    as_vector,
    historical_var_es,
    level_key,
    portfolio_returns,
    spawn_seeds,
    tail_metrics,
    validate_confidence,
    weight_vector,
)


class TestLevelKey:
    @pytest.mark.parametrize(
        "level,key",
        [
            (0.95, "95"),
            (0.99, "99"),
            (0.57, "57"),
            (0.29, "29"),
            (0.995, "99_5"),
            (0.999, "99_9"),
        ],
    )
    def test_keys_do_not_truncate_floats(self, level, key):
        assert level_key(level) == key


class TestValidation:
    @pytest.mark.parametrize(
        "value", [0, 1, -0.1, 1.5, float("nan"), True, "0.9", None]
    )
    def test_invalid_confidence(self, value):
        with pytest.raises(ValueError):
            validate_confidence(value)

    def test_valid_confidence(self):
        assert validate_confidence(0.95) == 0.95


class TestAsFrame:
    def test_accepts_series_array_list(self):
        assert as_frame(pd.Series([0.1, 0.2, 0.3])).shape == (3, 1)
        assert as_frame(np.array([0.1, 0.2, 0.3])).shape == (3, 1)
        assert as_frame([[0.1, 0.2], [0.3, 0.4]]).shape == (2, 2)

    def test_drops_non_finite_rows(self):
        frame = as_frame(pd.DataFrame({"a": [0.1, np.nan, 0.2, np.inf, 0.3]}))
        assert len(frame) == 3

    def test_minimum_rows_enforced(self):
        with pytest.raises(ValueError):
            as_frame([0.1], min_rows=2)

    def test_as_vector_flattens_and_filters(self):
        assert (
            len(
                as_vector(pd.DataFrame({"a": [1.0, np.nan, 2.0], "b": [3.0, 4.0, 5.0]}))
            )
            == 5
        )


class TestWeights:
    def test_default_equal(self):
        assert np.allclose(weight_vector(None, ["a", "b", "c", "d"]), 0.25)

    def test_dict_by_name(self):
        assert np.allclose(weight_vector({"b": 0.7, "a": 0.3}, ["a", "b"]), [0.3, 0.7])

    def test_unknown_asset_rejected(self):
        with pytest.raises(ValueError):
            weight_vector({"zzz": 1.0}, ["a", "b"])

    @pytest.mark.parametrize("weights", [[0.5], [np.nan, 1.0], [0.0, 0.0]])
    def test_invalid_vectors_rejected(self, weights):
        with pytest.raises(ValueError):
            weight_vector(weights, ["a", "b"])

    def test_normalize(self):
        assert np.allclose(weight_vector([2.0, 2.0], ["a", "b"], normalize=True), 0.5)

    def test_portfolio_returns(self):
        frame = pd.DataFrame({"a": [0.1, 0.2], "b": [0.3, 0.4]})
        assert np.allclose(portfolio_returns(frame, [0.5, 0.5]), [0.2, 0.3])


class TestTailMetrics:
    def test_es_not_below_var_and_nonnegative(self):
        values = np.random.default_rng(0).normal(0, 0.01, 5000)
        var, es = historical_var_es(values, 0.95)
        assert 0 < var <= es

    def test_all_gains_gives_zero_var(self):
        var, es = historical_var_es(np.full(100, 0.01), 0.95)
        assert var == 0.0 and es == 0.0

    def test_keys_for_levels(self):
        metrics = tail_metrics(np.linspace(-0.05, 0.05, 1000), [0.95, 0.995])
        assert set(metrics) == {"var_95", "es_95", "var_99_5", "es_99_5"}


class TestSeeds:
    def test_deterministic_and_distinct(self):
        first = spawn_seeds(5, 6)
        assert first == spawn_seeds(5, 6)
        assert len(set(first)) == 6
