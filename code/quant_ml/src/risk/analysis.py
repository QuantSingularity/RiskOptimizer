import logging
from typing import Any, Dict, Optional, Sequence

import numpy as np
import pandas as pd
from arch import arch_model
from data.loaders import available_symbols, load_close_prices
from risk.common import validate_confidence
from settings import TRADING_DAYS

logger = logging.getLogger(__name__)

MAX_HORIZON = 252
MAX_SIMULATIONS = 1_000_000
MIN_GARCH_OBSERVATIONS = 100


def load_returns(
    tickers: Optional[Sequence[str]] = None, data_dir: Optional[str] = None
) -> pd.DataFrame:
    selected = list(tickers) if tickers else available_symbols(data_dir)
    prices = load_close_prices(selected, data_dir, minimum_symbols=1)
    return np.log(prices / prices.shift(1)).dropna()


def validate_horizon(horizon: Any) -> int:
    if isinstance(horizon, bool) or not isinstance(horizon, (int, np.integer)):
        raise ValueError("horizon must be an integer")
    if not 1 <= horizon <= MAX_HORIZON:
        raise ValueError(f"horizon must be between 1 and {MAX_HORIZON}")
    return int(horizon)


def calculate_correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.corr()


def historical_var(
    returns: pd.DataFrame, confidence_level: float = 0.99, horizon: int = 1
) -> pd.Series:
    confidence_level = validate_confidence(confidence_level)
    horizon = validate_horizon(horizon)
    losses = -returns.quantile(1.0 - confidence_level) * np.sqrt(horizon)
    return losses.clip(lower=0.0)


def monte_carlo_var(
    returns: pd.DataFrame,
    confidence_level: float = 0.99,
    horizon: int = 1,
    n_simulations: int = 10_000,
    seed: Optional[int] = None,
) -> pd.Series:
    confidence_level = validate_confidence(confidence_level)
    horizon = validate_horizon(horizon)
    if (
        isinstance(n_simulations, bool)
        or not isinstance(n_simulations, (int, np.integer))
        or not 1 <= n_simulations <= MAX_SIMULATIONS
    ):
        raise ValueError(f"n_simulations must be between 1 and {MAX_SIMULATIONS}")
    rng = np.random.default_rng(seed)
    mu = returns.mean()
    sigma = returns.std()
    values: Dict[str, float] = {}
    for ticker in returns.columns:
        simulated = rng.normal(
            mu[ticker] * horizon, sigma[ticker] * np.sqrt(horizon), n_simulations
        )
        values[ticker] = max(
            -float(np.percentile(simulated, (1.0 - confidence_level) * 100)), 0.0
        )
    return pd.Series(values)


def garch_volatility_forecast(returns: pd.DataFrame, horizon: int = 5) -> pd.Series:
    horizon = validate_horizon(horizon)
    forecasts: Dict[str, float] = {}
    for ticker in returns.columns:
        series = returns[ticker].dropna()
        if len(series) < MIN_GARCH_OBSERVATIONS:
            forecasts[ticker] = float("nan")
            continue
        try:
            fitted = arch_model(series * 100, vol="Garch", p=1, q=1, rescale=False).fit(
                disp="off"
            )
            variance = fitted.forecast(horizon=horizon).variance.iloc[-1]
            daily_volatility = float(np.sqrt(variance.mean())) / 100.0
            forecasts[ticker] = daily_volatility * np.sqrt(TRADING_DAYS)
        except Exception as error:
            logger.warning("GARCH fit failed for %s: %s", ticker, error)
            forecasts[ticker] = float("nan")
    return pd.Series(forecasts)


def stress_test(returns: pd.DataFrame, scenario_multiplier: float = 3.0) -> pd.Series:
    if (
        isinstance(scenario_multiplier, bool)
        or not isinstance(scenario_multiplier, (int, float))
        or not 0 < scenario_multiplier <= 20
    ):
        raise ValueError("scenario_multiplier must be a number between 0 and 20")
    return returns.std() * float(scenario_multiplier)


def run_risk_analysis(
    tickers: Optional[Sequence[str]] = None,
    var_confidence: float = 0.99,
    horizon: int = 5,
    stress_multiplier: float = 4.0,
    n_simulations: int = 10_000,
    seed: Optional[int] = None,
    returns: Optional[pd.DataFrame] = None,
) -> Dict[str, Any]:
    frame = returns if returns is not None else load_returns(tickers)
    return {
        "correlation_matrix": calculate_correlation_matrix(frame),
        "historical_var": historical_var(frame, var_confidence, 1),
        "monte_carlo_var": monte_carlo_var(
            frame, var_confidence, horizon, n_simulations, seed
        ),
        "garch_volatility": garch_volatility_forecast(frame, horizon),
        "stress_loss": stress_test(frame, stress_multiplier),
    }
