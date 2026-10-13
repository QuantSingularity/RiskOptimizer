import numpy as np
import pytest
from risk.ml import MODEL_TYPES, MLRiskModel


@pytest.fixture(scope="module", params=MODEL_TYPES)
def fitted(request, returns_frame):
    return MLRiskModel(request.param).fit(returns_frame)


class TestFit:
    def test_state(self, fitted, returns_frame):
        assert fitted.trained
        assert fitted.asset_names == list(returns_frame.columns)
        assert fitted.metrics["train_rows"] > fitted.metrics["test_rows"] > 0
        assert len(fitted.feature_names) == 5 * 3 + 3

    def test_gbm_and_rf_expose_feature_importance(self, fitted):
        if fitted.model_type in ("gbm", "rf"):
            assert len(fitted.feature_importance) == len(fitted.feature_names)

    def test_accepts_series_and_array(self, returns_frame):
        series = returns_frame.iloc[:, 0]
        assert MLRiskModel("rf").fit(series).trained
        assert MLRiskModel("rf").fit(series.to_numpy()).trained

    def test_weights_change_the_target(self, returns_frame):
        equal = MLRiskModel("rf").fit(returns_frame)
        concentrated = MLRiskModel("rf").fit(returns_frame, weights=[1, 0, 0])
        assert not np.allclose(equal.train_target, concentrated.train_target)


class TestPredict:
    def test_var_is_positive_loss_and_es_dominates(self, fitted, returns_frame):
        var = fitted.predict_var(returns_frame, 0.95)
        es = fitted.predict_es(returns_frame, 0.95)
        assert var.shape == es.shape == (len(returns_frame) - 9,)
        assert (var >= 0).all() and np.isfinite(var).all()
        assert (es >= var - 1e-12).all()

    def test_higher_confidence_higher_var(self, fitted, returns_frame):
        assert (
            fitted.predict_var(returns_frame, 0.99).mean()
            > fitted.predict_var(returns_frame, 0.9).mean()
        )

    def test_forecast_helpers_use_latest_window(self, fitted, returns_frame):
        assert (
            fitted.forecast_var(returns_frame) == fitted.predict_var(returns_frame)[-1]
        )
        assert fitted.forecast_es(returns_frame) == fitted.predict_es(returns_frame)[-1]

    def test_latest_window_includes_most_recent_day(self, fitted, returns_frame):
        truncated = returns_frame.iloc[:-1]
        assert (
            len(fitted.predict_var(returns_frame))
            == len(fitted.predict_var(truncated)) + 1
        )

    def test_out_of_sample_coverage_is_calibrated(self, returns_frame):
        split = 600
        model = MLRiskModel("gbm").fit(returns_frame.iloc[:split])
        var = model.predict_var(returns_frame, 0.95)
        realised = -(returns_frame.to_numpy() @ np.full(3, 1 / 3))[10:]
        test = slice(split - 10, len(realised))
        coverage = np.mean(realised[test] <= var[: len(realised)][test])
        assert 0.90 <= coverage <= 0.99

    def test_extreme_inputs_do_not_explode(self, returns_frame):
        model = MLRiskModel("nn").fit(returns_frame)
        shocked = returns_frame.copy()
        shocked.iloc[-30:] *= 25
        assert model.predict_var(shocked, 0.95).max() < 2.0


class TestPersistence:
    def test_round_trip(self, fitted, returns_frame, tmp_path):
        path = str(tmp_path / "sub" / "model.joblib")
        fitted.save_model(path)
        loaded = MLRiskModel.load_model(path)
        assert np.allclose(
            fitted.predict_var(returns_frame), loaded.predict_var(returns_frame)
        )
        assert np.allclose(
            fitted.predict_es(returns_frame), loaded.predict_es(returns_frame)
        )

    def test_rejects_foreign_files(self, tmp_path):
        import joblib

        bad = tmp_path / "bad.joblib"
        joblib.dump({"model": 1}, bad)
        with pytest.raises(ValueError):
            MLRiskModel.load_model(str(bad))
        with pytest.raises(FileNotFoundError):
            MLRiskModel.load_model(str(tmp_path / "none.joblib"))

    def test_untrained_cannot_save(self, tmp_path):
        with pytest.raises(ValueError):
            MLRiskModel().save_model(str(tmp_path / "m.joblib"))


class TestValidation:
    @pytest.mark.parametrize(
        "kwargs",
        [{"model_type": "xgb"}, {"quantile": 0}, {"quantile": 0.6}, {"quantile": True}],
    )
    def test_constructor(self, kwargs):
        with pytest.raises(ValueError):
            MLRiskModel(**kwargs)

    @pytest.mark.parametrize(
        "kwargs",
        [
            {"feature_window": 2},
            {"feature_window": True},
            {"horizon": 0},
            {"test_size": 0.9},
        ],
    )
    def test_fit_arguments(self, returns_frame, kwargs):
        with pytest.raises(ValueError):
            MLRiskModel("rf").fit(returns_frame, **kwargs)

    def test_short_history(self, returns_frame):
        with pytest.raises(ValueError):
            MLRiskModel("rf").fit(returns_frame.head(40))

    def test_untrained_prediction(self, returns_frame):
        with pytest.raises(ValueError):
            MLRiskModel().predict_var(returns_frame)

    def test_mismatched_assets_and_window(self, fitted, returns_frame):
        with pytest.raises(ValueError):
            fitted.predict_var(returns_frame.iloc[:, :2])
        with pytest.raises(ValueError):
            fitted.predict_var(returns_frame, feature_window=20)

    def test_plot_feature_importance(self, returns_frame):
        import matplotlib.pyplot as plt

        figure = MLRiskModel("gbm").fit(returns_frame).plot_feature_importance(5)
        plt.close(figure)
        with pytest.raises(ValueError):
            MLRiskModel("nn").fit(returns_frame).plot_feature_importance()
