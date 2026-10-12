import json

import numpy as np
import pandas as pd
import pytest
from quant_ml.forecasting import price
from quant_ml.forecasting.price import (
    AUTO_MODELS,
    cross_validate,
    forecast_frame,
    forecast_prices,
    infer_frequency,
    select_model,
    validate_model,
    validate_periods,
)
from quant_ml.forecasting.sentiment import (
    AnalyticsUnavailableError,
    analyze_sentiment,
    summarize_sentiment,
)


def make_frame(values, freq="B", start="2020-01-01"):
    return pd.DataFrame(
        {"ds": pd.date_range(start, periods=len(values), freq=freq), "y": values}
    )


@pytest.fixture(scope="module")
def random_walk():
    rng = np.random.default_rng(3)
    return make_frame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 600))))


@pytest.fixture(scope="module")
def trending():
    rng = np.random.default_rng(4)
    steps = 0.004 + rng.normal(0, 0.0005, 600)
    return make_frame(100 * np.exp(np.cumsum(steps)))


class TestCenters:
    def test_naive_is_constant(self, random_walk):
        center = price.naive_center(random_walk, 5, "B")
        assert np.allclose(center, random_walk["y"].iloc[-1])

    def test_drift_extrapolates_trend(self, trending):
        center = price.drift_center(trending, 5, "B")
        assert (np.diff(center) > 0).all() and center[0] > trending["y"].iloc[-1]

    def test_ets_is_finite_and_positive(self, random_walk):
        center = price.ets_center(random_walk, 10, "B")
        assert len(center) == 10 and np.isfinite(center).all() and (center > 0).all()

    def test_drift_needs_data(self):
        with pytest.raises(ValueError):
            price.drift_center(make_frame([1.0, 2.0]), 3, "B")


class TestSelection:
    def test_random_walk_keeps_naive_and_says_so(self, random_walk):
        result = forecast_frame(random_walk, "RW", 10)
        assert result["model"] == "naive" and result["beats_naive"] is False
        assert result["requested_model"] == "auto"
        assert result["validation"]["windows"] >= 10

    def test_trend_selects_a_trend_model_with_evidence(self, trending):
        result = forecast_frame(trending, "TR", 10)
        validation = result["validation"]
        assert result["model"] in ("drift", "ets")
        assert result["beats_naive"] is True
        assert validation["win_rate_vs_naive"][result["model"]] >= price.MIN_WIN_RATE
        assert validation["skill_vs_naive"][result["model"]] >= price.MIN_IMPROVEMENT

    def test_auto_never_selects_prophet(self, trending):
        assert (
            "prophet" not in forecast_frame(trending, "TR", 10)["validation"]["scores"]
        )
        assert "prophet" not in AUTO_MODELS

    def test_select_model_rules(self):
        scores = {"naive": 0.04, "drift": 0.0399, "ets": 0.03}
        wins = {"naive": 0.0, "drift": 0.9, "ets": 0.5}
        validation = {"scores": scores, "win_rate_vs_naive": wins}
        assert select_model(validation) == "naive"
        wins["ets"] = 0.7
        assert select_model(validation) == "ets"
        scores["ets"] = 0.0399
        assert select_model(validation) == "naive"
        assert select_model(None) == "naive"

    def test_random_walks_rarely_get_a_trend_model(self):
        picks = []
        for seed in range(12):
            rng = np.random.default_rng(100 + seed)
            frame = make_frame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 600))))
            picks.append(forecast_frame(frame, "RW", 10)["model"])
        assert picks.count("naive") >= 11

    def test_short_history_skips_validation(self):
        frame = make_frame(
            100 * np.exp(np.cumsum(np.random.default_rng(1).normal(0, 0.01, 60)))
        )
        result = forecast_frame(frame, "S", 5)
        assert result["validation"] is None and result["model"] == "naive"
        assert result["beats_naive"] is False

    def test_failing_candidate_is_excluded_not_fatal(self, random_walk, monkeypatch):
        def broken(train, horizon, freq):
            raise RuntimeError("fit failed")

        monkeypatch.setitem(price.CENTERS, "ets", broken)
        result = forecast_frame(random_walk, "RW", 5)
        assert "ets" not in result["validation"]["scores"]
        assert "fit failed" in result["validation"]["failed"]["ets"]

    def test_explicit_model_failure_is_raised(self, random_walk, monkeypatch):
        def broken(train, horizon, freq):
            raise RuntimeError("boom")

        monkeypatch.setitem(price.CENTERS, "drift", broken)
        with pytest.raises(RuntimeError):
            forecast_frame(random_walk, "RW", 5, model="drift")

    def test_cross_validate_structure(self, random_walk):
        validation = cross_validate(random_walk, 10, "B", ["naive", "drift"], 6)
        assert validation["windows"] == 6 and validation["horizon"] == 10
        assert validation["skill_vs_naive"]["naive"] == 0.0
        assert 0.0 <= validation["win_rate_vs_naive"]["drift"] <= 1.0

    def test_validation_horizon_is_capped(self, random_walk):
        assert (
            forecast_frame(random_walk, "RW", 365)["validation"]["horizon"]
            == price.MAX_VALIDATION_HORIZON
        )


class TestForecastOutput:
    def test_bands_wrap_the_forecast_and_widen(self, random_walk):
        rows = forecast_frame(random_walk, "RW", 20)["forecast"]
        assert all(r["yhat_lower"] < r["yhat"] < r["yhat_upper"] for r in rows)
        widths = [r["yhat_upper"] - r["yhat_lower"] for r in rows]
        assert widths == sorted(widths)

    def test_dates_are_future_business_days(self, random_walk):
        result = forecast_frame(random_walk, "RW", 10)
        dates = pd.to_datetime([r["date"] for r in result["forecast"]])
        assert dates[0] > random_walk["ds"].iloc[-1]
        assert (dates.dayofweek < 5).all() and result["frequency"] == "B"

    def test_daily_frequency_for_weekend_data(self):
        rng = np.random.default_rng(2)
        frame = make_frame(100 * np.exp(np.cumsum(rng.normal(0, 0.01, 300))), freq="D")
        assert infer_frequency(frame["ds"]) == "D"
        assert forecast_frame(frame, "X", 14)["frequency"] == "D"

    def test_output_is_strict_json(self, random_walk):
        json.dumps(forecast_frame(random_walk, "RW", 10), allow_nan=False)

    def test_unsorted_input_is_handled(self, random_walk):
        shuffled = random_walk.sample(frac=1.0, random_state=1)
        assert (
            forecast_frame(shuffled, "RW", 5)["last_observed"]["date"]
            == forecast_frame(random_walk, "RW", 5)["last_observed"]["date"]
        )

    def test_explicit_models(self, random_walk):
        for model in ("naive", "drift", "ets"):
            assert forecast_frame(random_walk, "RW", 5, model=model)["model"] == model

    @pytest.mark.slow
    def test_explicit_prophet_warns_when_it_loses(self, random_walk):
        pytest.importorskip("prophet")
        result = forecast_frame(random_walk, "RW", 5, model="prophet")
        assert result["model"] == "prophet"
        assert "warning" in result and "naive" in result["warning"]


class TestValidation:
    @pytest.mark.parametrize("periods", [0, -1, 366, 1.5, True, "7"])
    def test_invalid_periods(self, periods):
        with pytest.raises(ValueError):
            validate_periods(periods)

    @pytest.mark.parametrize("model", ["arima", "", None, "Naive"])
    def test_invalid_model(self, model):
        with pytest.raises(ValueError):
            validate_model(model)

    def test_bad_frames(self):
        with pytest.raises(ValueError):
            forecast_frame(pd.DataFrame({"a": [1]}), "X", 5)
        with pytest.raises(ValueError):
            forecast_frame(make_frame(np.linspace(1, 2, 10)), "X", 5)
        with pytest.raises(ValueError):
            forecast_frame(make_frame(np.r_[np.ones(40), -1.0]), "X", 5)

    def test_unknown_ticker(self):
        with pytest.raises(FileNotFoundError):
            forecast_prices("NOPE", 5)


class TestRealData:
    @pytest.mark.parametrize(
        "ticker,frequency", [("AAPL", "B"), ("BTC_USD", "D"), ("btc", "D")]
    )
    def test_bundled_series(self, ticker, frequency):
        result = forecast_prices(ticker, 7)
        assert result["frequency"] == frequency and len(result["forecast"]) == 7
        assert result["validation"]["scores"]["naive"] > 0

    @pytest.mark.performance
    @pytest.mark.parametrize("ticker", ["AAPL", "TSLA", "BTC_USD"])
    def test_interval_coverage_is_calibrated(self, ticker):
        frame = price.load_price_data(ticker)
        horizon, hits = 10, []
        for k in range(1, 31):
            cut = len(frame) - horizon - 8 * k
            rows = forecast_frame(frame.iloc[:cut], ticker, horizon)["forecast"]
            actual = frame.iloc[cut : cut + horizon]["y"].to_numpy()
            low = np.array([r["yhat_lower"] for r in rows])
            high = np.array([r["yhat_upper"] for r in rows])
            hits.append(np.mean((actual >= low) & (actual <= high)))
        assert 0.88 <= np.mean(hits) <= 0.99


class TestSentiment:
    def test_sentiment_labels(self):
        try:
            frame = analyze_sentiment(
                [
                    "Shares surge in a record rally after strong earnings",
                    "Company files for bankruptcy as sales plunge",
                ]
            )
        except AnalyticsUnavailableError:
            pytest.skip("VADER lexicon unavailable")
        assert list(frame["sentiment"]) == ["Positive", "Negative"]
        summary = summarize_sentiment(frame)
        assert summary["count"] == 2 and summary["positive"] == 1

    def test_sentiment_rejects_non_strings(self):
        with pytest.raises(TypeError):
            analyze_sentiment(["ok", 5])

    def test_threshold_order_is_validated(self):
        with pytest.raises(ValueError):
            analyze_sentiment(["x"], positive_threshold=-0.1, negative_threshold=0.1)
