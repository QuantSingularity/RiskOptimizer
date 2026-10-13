import datetime
import json

import numpy as np
import pandas as pd
import settings
from serialization import to_jsonable


class TestSerialization:
    def test_numpy_and_pandas_types(self):
        payload = {
            "a": np.float64(1.5),
            "b": np.int64(3),
            "c": np.array([1.0, np.nan, np.inf]),
            "d": pd.Series({"x": 1.0}),
            "e": pd.DataFrame({"k": [1, 2]}),
            "f": np.bool_(True),
            "g": pd.Timestamp("2024-01-02"),
            "h": datetime.date(2024, 1, 2),
            "i": (1, 2),
        }
        converted = to_jsonable(payload)
        assert json.dumps(converted)
        assert converted["c"] == [1.0, None, None]
        assert converted["e"] == [{"k": 1}, {"k": 2}]
        assert converted["g"].startswith("2024-01-02")
        assert converted["f"] is True

    def test_nan_float_becomes_none(self):
        assert to_jsonable(float("nan")) is None
        assert to_jsonable(float("-inf")) is None

    def test_unknown_objects_are_stringified(self):
        assert to_jsonable(object()).startswith("<object")


class TestSettings:
    def test_defaults_resolve(self, monkeypatch):
        for name in (
            "QUANT_ML_DATA_DIR",
            "QUANT_ML_ARTIFACT_DIR",
            "QUANT_ML_REPORT_DIR",
            "MODEL_PATH",
        ):
            monkeypatch.delenv(name, raising=False)
        assert settings.data_dir().is_dir()
        assert settings.default_model_path().name == settings.MODEL_FILE_NAME
        assert settings.report_dir().parent == settings.artifact_dir()

    def test_environment_overrides(self, monkeypatch, tmp_path):
        monkeypatch.setenv("QUANT_ML_ARTIFACT_DIR", str(tmp_path / "art"))
        assert settings.artifact_dir() == tmp_path / "art"
        assert settings.report_dir() == tmp_path / "art" / "reports"
        monkeypatch.setenv("MODEL_PATH", str(tmp_path / "m.joblib"))
        assert settings.default_model_path() == tmp_path / "m.joblib"
        monkeypatch.setenv("QUANT_ML_DATA_DIR", str(tmp_path))
        assert settings.data_dir() == tmp_path
