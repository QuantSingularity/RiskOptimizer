import argparse
import json
import logging
import multiprocessing as mp
import sys
import time
from typing import Any, Dict, List, Optional

import numpy as np
from quant_ml.data.loaders import available_symbols, load_close_prices
from quant_ml.forecasting.price import forecast_prices, prophet_available_flag
from quant_ml.risk.copula import COPULA_TYPES, CopulaMLRiskModel
from quant_ml.risk.engine import ParallelRiskEngine
from quant_ml.risk.evt import ExtremeValueRisk
from quant_ml.serialization import to_jsonable
from quant_ml.training.evaluate import evaluate
from scipy import stats

logger = logging.getLogger(__name__)

EVT_DEGREES = (3, 4, 6)
EVT_LEVELS = (0.99, 0.995)


def evt_accuracy(samples: int) -> List[Dict[str, Any]]:
    rows = []
    for df in EVT_DEGREES:
        data = stats.t.rvs(df, size=samples, random_state=df) * 0.01
        model = ExtremeValueRisk().fit_pot(data, threshold_quantile=0.05)
        for level in EVT_LEVELS:
            truth = -stats.t.ppf(1 - level, df) * 0.01
            estimate = model.calculate_var(level)
            rows.append(
                {
                    "degrees_of_freedom": df,
                    "confidence": level,
                    "true_var": float(truth),
                    "estimated_var": float(estimate),
                    "relative_error": float(estimate / truth - 1.0),
                }
            )
    return rows


def copula_fit(returns: Any, scenarios: int) -> Dict[str, Any]:
    weights = np.full(returns.shape[1], 1.0 / returns.shape[1])
    series = returns.to_numpy() @ weights
    empirical = {
        "std": float(series.std()),
        "var_95": float(-np.quantile(series, 0.05)),
        "var_99": float(-np.quantile(series, 0.01)),
    }
    models = {}
    for copula in COPULA_TYPES:
        metrics = (
            CopulaMLRiskModel(copula, scenarios, seed=1)
            .fit(returns)
            .calculate_risk_metrics(weights)
        )
        models[copula] = {
            key: float(metrics[key]) for key in ("std", "var_95", "var_99")
        }
    return {"empirical": empirical, "models": models}


def timed(function: Any, *arguments: Any) -> float:
    start = time.perf_counter()
    function(*arguments)
    return time.perf_counter() - start


def engine_timing(returns: Any, quick: bool) -> List[Dict[str, Any]]:
    scenarios = 20_000 if quick else 100_000
    portfolios = 2_000 if quick else 10_000
    model = CopulaMLRiskModel("t", 1000, seed=1).fit(returns)
    rows = []
    for jobs in sorted({1, min(4, mp.cpu_count())}):
        engine = ParallelRiskEngine(n_jobs=jobs, seed=1)
        rows.append(
            {
                "n_jobs": jobs,
                "monte_carlo": {
                    "scenarios": scenarios,
                    "seconds": timed(
                        engine.parallel_monte_carlo, model, None, scenarios
                    ),
                },
                "portfolio_search": {
                    "portfolios": portfolios,
                    "seconds": timed(
                        engine.parallel_portfolio_optimization,
                        returns,
                        "markowitz",
                        portfolios,
                    ),
                },
                "backtest": {"seconds": timed(engine.parallel_backtest, returns)},
            }
        )
    return rows


def prophet_comparison(symbols: List[str]) -> Dict[str, Any]:
    if not prophet_available_flag():
        return {"available": False}
    rows = {}
    for symbol in symbols:
        result = forecast_prices(symbol, 10, model="prophet")
        validation = result["validation"] or {}
        rows[symbol] = {
            "skill_vs_naive": validation.get("skill_vs_naive", {}).get("prophet"),
            "win_rate_vs_naive": validation.get("win_rate_vs_naive", {}).get("prophet"),
            "warning": result.get("warning"),
        }
    return {"available": True, "results": rows}


def benchmark(
    symbols: Optional[List[str]] = None, quick: bool = False
) -> Dict[str, Any]:
    selected = symbols or available_symbols()
    prices = load_close_prices(selected)
    returns = prices.pct_change().dropna()
    return {
        "quick": quick,
        "evaluation": evaluate(selected),
        "evt_accuracy": evt_accuracy(40_000 if quick else 150_000),
        "copula_fit": copula_fit(returns, 20_000 if quick else 100_000),
        "engine_timing": engine_timing(returns, quick),
        "prophet_comparison": prophet_comparison(selected[:2] if quick else selected),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Benchmark quant_ml models on historical data"
    )
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--quick", action="store_true")
    parser.add_argument("--output", default=None)
    arguments = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO)
    text = json.dumps(
        to_jsonable(benchmark(arguments.symbols, arguments.quick)),
        indent=2,
        allow_nan=False,
    )
    if arguments.output:
        with open(arguments.output, "w", encoding="utf-8") as handle:
            handle.write(text)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
