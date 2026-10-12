import argparse
import json
import logging
import sys
from typing import Any, Dict, List, Optional

import numpy as np
from quant_ml.data.loaders import available_symbols, load_close_prices
from quant_ml.forecasting.price import forecast_prices
from quant_ml.risk.engine import ParallelRiskEngine
from quant_ml.risk.ml import MODEL_TYPES, MLRiskModel
from quant_ml.serialization import to_jsonable
from quant_ml.training.trainer import train_and_evaluate

logger = logging.getLogger(__name__)

TRAIN_FRACTION = 0.7
KUPIEC_MIN_PVALUE = 0.01
FORECAST_HORIZON = 10


def evaluate_ml_calibration(
    returns: Any, confidence: float, tolerance: float
) -> Dict[str, Any]:
    split = int(len(returns) * TRAIN_FRACTION)
    weights = np.full(returns.shape[1], 1.0 / returns.shape[1])
    realised = -(returns.to_numpy() @ weights)
    results: Dict[str, Any] = {}
    for model_type in MODEL_TYPES:
        model = MLRiskModel(model_type).fit(returns.iloc[:split])
        predicted = model.predict_var(returns, confidence)
        window = model.feature_window
        actual = realised[window:]
        test = slice(split - window, len(actual))
        coverage = float(np.mean(actual[test] <= predicted[: len(actual)][test]))
        results[model_type] = {
            "coverage": coverage,
            "target": confidence,
            "passed": bool(abs(coverage - confidence) <= tolerance),
            "validation": model.metrics,
        }
    return results


def evaluate_backtests(returns: Any, confidence: float) -> Dict[str, Any]:
    engine = ParallelRiskEngine(n_jobs=1)
    summary = engine.parallel_backtest(returns, confidence_level=confidence)["summary"]
    return {
        model: {**values, "passed": bool(values["kupiec_pvalue"] >= KUPIEC_MIN_PVALUE)}
        for model, values in summary.items()
    }


def evaluate_forecasts(symbols: List[str]) -> Dict[str, Any]:
    results: Dict[str, Any] = {}
    for symbol in symbols:
        forecast = forecast_prices(symbol, FORECAST_HORIZON)
        validation = forecast["validation"] or {}
        results[symbol] = {
            "selected_model": forecast["model"],
            "beats_naive": forecast["beats_naive"],
            "scores": validation.get("scores"),
            "windows": validation.get("windows"),
        }
    return results


def evaluate(
    symbols: Optional[List[str]] = None,
    data_dir: Optional[str] = None,
    confidence: float = 0.95,
    tolerance: float = 0.06,
) -> Dict[str, Any]:
    selected = symbols or available_symbols(data_dir)
    prices = load_close_prices(selected, data_dir)
    returns = prices.pct_change().dropna()
    _, optimizer = train_and_evaluate(prices)
    ml = evaluate_ml_calibration(returns, confidence, tolerance)
    backtests = evaluate_backtests(returns, confidence)
    forecasts = evaluate_forecasts(list(prices.columns))
    checks = {f"ml_coverage_{name}": item["passed"] for name, item in ml.items()}
    checks.update(
        {f"backtest_{name}": item["passed"] for name, item in backtests.items()}
    )
    return {
        "data": {
            "assets": list(prices.columns),
            "observations": int(len(returns)),
            "start": str(prices.index[0].date()),
            "end": str(prices.index[-1].date()),
        },
        "optimizer": optimizer,
        "ml_risk": ml,
        "backtests": backtests,
        "forecasts": forecasts,
        "checks": checks,
        "passed": all(checks.values()),
    }


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate quant_ml models on historical data"
    )
    parser.add_argument("--symbols", nargs="*", default=None)
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--tolerance", type=float, default=0.06)
    parser.add_argument("--output", default=None)
    parser.add_argument("--strict", action="store_true")
    arguments = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    report = to_jsonable(
        evaluate(
            arguments.symbols,
            arguments.data_dir,
            arguments.confidence,
            arguments.tolerance,
        )
    )
    text = json.dumps(report, indent=2, allow_nan=False)
    if arguments.output:
        with open(arguments.output, "w", encoding="utf-8") as handle:
            handle.write(text)
        logger.info("Evaluation report written to %s", arguments.output)
    else:
        print(text)
    for name, passed in report["checks"].items():
        logger.info("%s: %s", name, "pass" if passed else "FAIL")
    return 0 if report["passed"] or not arguments.strict else 1


if __name__ == "__main__":
    sys.exit(main())
