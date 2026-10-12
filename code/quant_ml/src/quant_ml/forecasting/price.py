import importlib.util
import logging
import os
import warnings
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd
from quant_ml.data.loaders import load_close_series

logger = logging.getLogger(__name__)

MAX_FORECAST_PERIODS = 365
MODELS = ("naive", "drift", "ets", "prophet")
AUTO_MODELS = ("naive", "drift", "ets")
MODEL_CHOICES = ("auto",) + MODELS
MIN_OBSERVATIONS = 30
MIN_TRAIN_ROWS = 120
DRIFT_WINDOW = 252
ETS_WINDOW = 500
PROPHET_HISTORY = 1000
VOLATILITY_WINDOWS = (252, 63)
AUTO_VALIDATION_WINDOWS = 24
EXPLICIT_VALIDATION_WINDOWS = 12
MAX_VALIDATION_HORIZON = 60
MIN_IMPROVEMENT = 0.01
MIN_WIN_RATE = 0.65
BAND_Z = 1.96


def load_price_data(
    ticker: str, data_dir: Optional[os.PathLike] = None
) -> pd.DataFrame:
    series = load_close_series(ticker, data_dir)
    frame = series.reset_index()
    frame.columns = ["ds", "y"]
    frame["ds"] = pd.to_datetime(frame["ds"])
    logger.info("Loaded %d rows for %s", len(frame), ticker)
    return frame


def infer_frequency(dates: pd.Series) -> str:
    weekdays = pd.to_datetime(dates).dt.dayofweek
    return "D" if float((weekdays >= 5).mean()) > 0.1 else "B"


def validate_periods(periods: Any) -> int:
    if isinstance(periods, bool) or not isinstance(periods, (int, np.integer)):
        raise ValueError("periods must be an integer")
    if periods < 1 or periods > MAX_FORECAST_PERIODS:
        raise ValueError(f"periods must be between 1 and {MAX_FORECAST_PERIODS}")
    return int(periods)


def validate_model(model: Any) -> str:
    if model not in MODEL_CHOICES:
        raise ValueError(f"model must be one of {', '.join(MODEL_CHOICES)}")
    return model


def naive_center(train: pd.DataFrame, horizon: int, freq: str) -> np.ndarray:
    return np.full(horizon, float(train["y"].iloc[-1]))


def drift_center(train: pd.DataFrame, horizon: int, freq: str) -> np.ndarray:
    log_prices = np.log(train["y"].to_numpy(dtype=float)[-DRIFT_WINDOW:])
    if len(log_prices) < 3:
        raise ValueError("At least three observations are required to forecast")
    slope = float(np.polyfit(np.arange(len(log_prices)), log_prices, 1)[0])
    return np.exp(log_prices[-1] + slope * np.arange(1, horizon + 1))


def ets_center(train: pd.DataFrame, horizon: int, freq: str) -> np.ndarray:
    from statsmodels.tsa.holtwinters import ExponentialSmoothing

    log_prices = np.log(train["y"].to_numpy(dtype=float)[-ETS_WINDOW:])
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        fitted = ExponentialSmoothing(
            log_prices,
            trend="add",
            damped_trend=True,
            initialization_method="estimated",
        ).fit()
        return np.exp(np.asarray(fitted.forecast(horizon), dtype=float))


def fit_prophet(train: pd.DataFrame, horizon: int, freq: str) -> np.ndarray:
    from prophet import Prophet

    logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
    logging.getLogger("prophet").setLevel(logging.WARNING)
    model = Prophet(
        daily_seasonality=False,
        weekly_seasonality=freq == "D",
        yearly_seasonality=False,
        changepoint_prior_scale=0.5,
        changepoint_range=0.98,
    )
    model.fit(train.tail(PROPHET_HISTORY))
    future = model.make_future_dataframe(
        periods=horizon, freq=freq, include_history=False
    )
    return model.predict(future)["yhat"].to_numpy(dtype=float)


CENTERS: Dict[str, Callable[[pd.DataFrame, int, str], np.ndarray]] = {
    "naive": naive_center,
    "drift": drift_center,
    "ets": ets_center,
    "prophet": fit_prophet,
}


def prophet_available_flag() -> bool:
    return importlib.util.find_spec("prophet") is not None


def volatility(log_prices: np.ndarray) -> float:
    returns = np.diff(log_prices)
    variances = [
        float(np.var(returns[-window:], ddof=1))
        for window in VOLATILITY_WINDOWS
        if len(returns) >= 3
    ]
    if not variances:
        raise ValueError(
            "At least four observations are required to estimate volatility"
        )
    return float(np.sqrt(np.mean(variances)))


def cross_validate(
    df: pd.DataFrame, horizon: int, freq: str, models: List[str], max_windows: int
) -> Optional[Dict[str, Any]]:
    horizon = min(horizon, MAX_VALIDATION_HORIZON)
    windows = min(max_windows, (len(df) - MIN_TRAIN_ROWS) // horizon)
    if windows < 2:
        return None
    errors: Dict[str, List[float]] = {name: [] for name in models}
    failed: Dict[str, str] = {}
    for k in range(1, windows + 1):
        cut = len(df) - k * horizon
        train, test = df.iloc[:cut], df.iloc[cut : cut + horizon]
        actual = test["y"].to_numpy(dtype=float)
        for name in list(errors):
            try:
                predicted = CENTERS[name](train, horizon, freq)[: len(actual)]
                errors[name].append(float(np.mean(np.abs(predicted - actual) / actual)))
            except Exception as error:
                failed[name] = str(error)
                errors.pop(name)
    if "naive" not in errors or not errors["naive"]:
        return None
    baseline = np.array(errors["naive"])
    scores = {name: float(np.mean(values)) for name, values in errors.items()}
    return {
        "metric": "mean absolute percentage error",
        "horizon": horizon,
        "windows": windows,
        "scores": scores,
        "skill_vs_naive": {
            name: 1.0 - score / scores["naive"] for name, score in scores.items()
        },
        "win_rate_vs_naive": {
            name: float(np.mean(np.array(values) < baseline))
            for name, values in errors.items()
        },
        "failed": failed,
    }


def select_model(validation: Optional[Dict[str, Any]]) -> str:
    if validation is None:
        return "naive"
    scores = validation["scores"]
    best = min(scores, key=scores.get)
    if best == "naive":
        return "naive"
    improved = scores[best] <= scores["naive"] * (1.0 - MIN_IMPROVEMENT)
    consistent = validation["win_rate_vs_naive"][best] >= MIN_WIN_RATE
    return best if improved and consistent else "naive"


def forecast_frame(
    df: pd.DataFrame, ticker: str, periods: int = 30, model: str = "auto"
) -> Dict[str, Any]:
    periods = validate_periods(periods)
    model = validate_model(model)
    if not {"ds", "y"}.issubset(df.columns):
        raise ValueError("DataFrame must contain 'ds' and 'y' columns")
    df = df[["ds", "y"]].dropna().sort_values("ds").reset_index(drop=True)
    if len(df) < MIN_OBSERVATIONS:
        raise ValueError(
            f"At least {MIN_OBSERVATIONS} observations are required to forecast"
        )
    if (df["y"] <= 0).any():
        raise ValueError("Prices must be strictly positive")
    freq = infer_frequency(df["ds"])
    validation: Optional[Dict[str, Any]] = None
    warning: Optional[str] = None
    if model == "auto":
        validation = cross_validate(
            df, periods, freq, list(AUTO_MODELS), AUTO_VALIDATION_WINDOWS
        )
        selected = select_model(validation)
    else:
        selected = model
        compared = ["naive", selected] if selected != "naive" else ["naive"]
        validation = cross_validate(
            df, periods, freq, compared, EXPLICIT_VALIDATION_WINDOWS
        )
        if validation and selected != "naive" and selected in validation["scores"]:
            skill = validation["skill_vs_naive"][selected]
            win_rate = validation["win_rate_vs_naive"][selected]
            if skill <= 0 or win_rate < MIN_WIN_RATE:
                warning = (
                    f"{selected} did not consistently beat the naive baseline in validation "
                    f"(skill {skill:.1%}, win rate {win_rate:.0%})"
                )
    try:
        center = CENTERS[selected](df, periods, freq)
    except Exception as error:
        if model != "auto":
            raise
        logger.warning("Model %s failed (%s); using naive", selected, error)
        selected, center = "naive", naive_center(df, periods, freq)
    log_prices = np.log(df["y"].to_numpy(dtype=float))
    sigma = volatility(log_prices)
    steps = np.arange(1, periods + 1)
    band = BAND_Z * sigma * np.sqrt(steps)
    log_center = np.log(np.asarray(center, dtype=float))
    dates = pd.date_range(
        start=pd.to_datetime(df["ds"].iloc[-1]), periods=periods + 1, freq=freq
    )[1:]
    result: Dict[str, Any] = {
        "ticker": ticker,
        "model": selected,
        "requested_model": model,
        "periods": periods,
        "frequency": freq,
        "last_observed": {
            "date": pd.to_datetime(df["ds"].iloc[-1]).date().isoformat(),
            "price": float(df["y"].iloc[-1]),
        },
        "daily_volatility": sigma,
        "validation": validation,
        "beats_naive": bool(
            validation and validation["skill_vs_naive"].get(selected, 0.0) > 0.0
        ),
        "forecast": [
            {
                "date": date.date().isoformat(),
                "yhat": float(np.exp(c)),
                "yhat_lower": float(np.exp(c - b)),
                "yhat_upper": float(np.exp(c + b)),
            }
            for date, c, b in zip(dates, log_center, band, strict=True)
        ],
    }
    if warning:
        result["warning"] = warning
    return result


def forecast_prices(
    ticker: str,
    periods: int = 30,
    data_dir: Optional[os.PathLike] = None,
    model: str = "auto",
) -> Dict[str, Any]:
    frame = load_price_data(ticker, data_dir)
    return forecast_frame(frame, ticker.strip().upper(), periods, model)
