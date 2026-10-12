from typing import Any, Dict, Optional, Tuple

import numpy as np
from quant_ml.risk.common import as_vector, historical_var_es
from quant_ml.settings import RISK_FREE_RATE, TRADING_DAYS

MIN_OBSERVATIONS = 5


def drawdown_profile(returns: np.ndarray) -> Tuple[float, int]:
    wealth = np.cumprod(1.0 + returns)
    peak = np.maximum.accumulate(np.concatenate([[1.0], wealth]))[1:]
    drawdowns = wealth / peak - 1.0
    longest = current = 0
    for in_drawdown in drawdowns < 0:
        current = current + 1 if in_drawdown else 0
        longest = max(longest, current)
    return float(drawdowns.min()), int(longest)


def downside_deviation(
    returns: np.ndarray, target: float = 0.0, periods: int = TRADING_DAYS
) -> float:
    shortfall = np.minimum(returns - target, 0.0)
    return float(np.sqrt(np.mean(shortfall**2)) * np.sqrt(periods))


def annualised(total_return: float, count: int, periods: int) -> float:
    return float((1.0 + total_return) ** (periods / count) - 1.0)


def performance_summary(
    returns: Any,
    benchmark: Optional[Any] = None,
    risk_free_rate: float = RISK_FREE_RATE,
    periods_per_year: int = TRADING_DAYS,
) -> Dict[str, Any]:
    series = as_vector(returns, min_size=MIN_OBSERVATIONS)
    if (series <= -1.0).any():
        raise ValueError("Returns must be greater than -100%")
    total = float(np.prod(1.0 + series) - 1.0)
    annual_return = annualised(total, len(series), periods_per_year)
    volatility = float(series.std(ddof=1) * np.sqrt(periods_per_year))
    depth, duration = drawdown_profile(series)
    downside = downside_deviation(series, 0.0, periods_per_year)
    var95, es95 = historical_var_es(series, 0.95)
    var99, es99 = historical_var_es(series, 0.99)
    summary: Dict[str, Any] = {
        "performance_summary": {
            "total_return": total,
            "annualized_return": annual_return,
            "volatility": volatility,
            "sharpe_ratio": (
                (annual_return - risk_free_rate) / volatility if volatility > 0 else 0.0
            ),
            "sortino_ratio": (
                (annual_return - risk_free_rate) / downside if downside > 0 else 0.0
            ),
            "calmar_ratio": annual_return / abs(depth) if depth < 0 else 0.0,
            "max_drawdown": depth,
            "max_drawdown_duration_days": duration,
            "win_rate": float(np.mean(series > 0)),
        },
        "risk_metrics": {
            "var_95": var95,
            "var_99": var99,
            "es_95": es95,
            "es_99": es99,
            "downside_deviation": downside,
            "sortino_ratio": (
                (annual_return - risk_free_rate) / downside if downside > 0 else 0.0
            ),
        },
        "observations": int(len(series)),
    }
    if benchmark is not None:
        bench = as_vector(benchmark, min_size=MIN_OBSERVATIONS)
        count = min(len(series), len(bench))
        if count < MIN_OBSERVATIONS:
            raise ValueError("Portfolio and benchmark need overlapping observations")
        port, bench = series[-count:], bench[-count:]
        bench_total = float(np.prod(1.0 + bench) - 1.0)
        bench_annual = annualised(bench_total, count, periods_per_year)
        bench_vol = float(bench.std(ddof=1) * np.sqrt(periods_per_year))
        excess = port - bench
        tracking_error = float(excess.std(ddof=1) * np.sqrt(periods_per_year))
        variance = float(np.var(bench, ddof=1))
        beta = (
            float(np.cov(port, bench, ddof=1)[0, 1] / variance) if variance > 0 else 1.0
        )
        port_annual = annualised(
            float(np.prod(1.0 + port) - 1.0), count, periods_per_year
        )
        summary["benchmark_comparison"] = {
            "benchmark_total_return": bench_total,
            "benchmark_annualized_return": bench_annual,
            "benchmark_volatility": bench_vol,
            "benchmark_sharpe": (
                (bench_annual - risk_free_rate) / bench_vol if bench_vol > 0 else 0.0
            ),
            "excess_return": port_annual - bench_annual,
            "tracking_error": tracking_error,
            "information_ratio": (
                float(excess.mean() * periods_per_year / tracking_error)
                if tracking_error > 0
                else 0.0
            ),
            "beta": beta,
            "alpha": port_annual
            - (risk_free_rate + beta * (bench_annual - risk_free_rate)),
            "treynor_ratio": (
                (port_annual - risk_free_rate) / beta if abs(beta) > 1e-9 else 0.0
            ),
            "overlapping_observations": int(count),
        }
    return summary
