import logging
import multiprocessing as mp
import time
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
import psutil
from joblib import Parallel, delayed
from risk.common import (
    as_frame,
    historical_var_es,
    portfolio_returns,
    spawn_seeds,
    tail_metrics,
    validate_confidence,
    weight_vector,
)
from risk.evt import ExtremeValueRisk
from scipy import stats
from settings import RISK_FREE_RATE, TRADING_DAYS

logger = logging.getLogger(__name__)

BACKENDS = ("loky", "threading", "multiprocessing")
RISK_MODELS = ("parametric", "historical", "evt")
OPTIMIZATION_RISK_MODELS = ("markowitz", "cvar", "mad")
CRYPTO_SYMBOLS = {"BTC", "ETH", "SOL", "XRP", "ADA", "DOGE", "BNB", "LTC", "DOT"}
DEFAULT_SCENARIOS = {
    "market_crash": {"description": "Market crash scenario", "shocks": {"all": -0.15}},
    "equity_selloff": {"description": "Equity selloff", "shocks": {"equity": -0.10}},
    "crypto_crash": {"description": "Crypto market crash", "shocks": {"crypto": -0.30}},
    "broad_deleveraging": {
        "description": "Broad deleveraging across equities and crypto",
        "shocks": {"equity": -0.12, "crypto": -0.25},
    },
}
MAX_SIMULATIONS = 1_000_000


def infer_asset_class(name: str) -> str:
    prefix = str(name).upper().replace("-", "_").split("_")[0]
    return "crypto" if prefix in CRYPTO_SYMBOLS else "equity"


def parametric_var_es(values: np.ndarray, confidence: float) -> Dict[str, float]:
    mean, std = float(np.mean(values)), float(np.std(values))
    z = stats.norm.ppf(confidence)
    var = max(-mean + z * std, 0.0)
    es = max(-mean + std * stats.norm.pdf(z) / (1.0 - confidence), var)
    return {"var": var, "es": es}


def model_metrics(
    values: np.ndarray, model: str, confidence_levels: Sequence[float]
) -> Dict[str, float]:
    if model == "historical":
        return tail_metrics(values, confidence_levels)
    metrics: Dict[str, float] = {}
    evt = (
        ExtremeValueRisk().fit_pot(values, threshold_quantile=0.1)
        if model == "evt"
        else None
    )
    from risk.common import level_key

    for confidence in confidence_levels:
        if model == "parametric":
            result = parametric_var_es(values, confidence)
        else:
            es = evt.calculate_es(confidence)
            result = {
                "var": evt.calculate_var(confidence),
                "es": es if np.isfinite(es) else float("nan"),
            }
        key = level_key(confidence)
        metrics[f"var_{key}"] = result["var"]
        metrics[f"es_{key}"] = result["es"]
    return metrics


def kupiec_pvalue(breaches: int, total: int, expected_rate: float) -> float:
    if total <= 0:
        return float("nan")
    observed = breaches / total
    log_null = (total - breaches) * np.log(1 - expected_rate) + breaches * np.log(
        expected_rate
    )
    if breaches == 0:
        log_alt = total * np.log(1 - observed)
    elif breaches == total:
        log_alt = total * np.log(observed)
    else:
        log_alt = (total - breaches) * np.log(1 - observed) + breaches * np.log(
            observed
        )
    statistic = max(-2.0 * (log_null - log_alt), 0.0)
    return float(1.0 - stats.chi2.cdf(statistic, df=1))


def sample_portfolios(
    returns: np.ndarray,
    batch_size: int,
    risk_model: str,
    risk_free_rate: float,
    periods: int,
    seed: int,
    corners: Optional[np.ndarray] = None,
) -> Dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    n_assets = returns.shape[1]
    concentrations = rng.choice([0.2, 1.0, 5.0], size=batch_size)
    weights = np.vstack([rng.dirichlet(np.full(n_assets, c)) for c in concentrations])
    if corners is not None:
        weights = np.vstack([corners, weights])
    mean_returns = returns.mean(axis=0) * periods
    covariance = np.cov(returns, rowvar=False).reshape(n_assets, n_assets) * periods
    port_return = weights @ mean_returns
    volatility = np.sqrt(np.einsum("ij,jk,ik->i", weights, covariance, weights))
    if risk_model == "markowitz":
        risk_metric = volatility
    else:
        series = returns @ weights.T
        if risk_model == "cvar":
            cutoff = np.quantile(series, 0.05, axis=0)
            mask = series <= cutoff
            risk_metric = (
                -(series * mask).sum(axis=0) / mask.sum(axis=0) * np.sqrt(periods)
            )
        else:
            risk_metric = np.mean(
                np.abs(series - series.mean(axis=0)), axis=0
            ) * np.sqrt(periods)
    sharpe = np.where(
        volatility > 0,
        (port_return - risk_free_rate) / np.where(volatility > 0, volatility, 1),
        0.0,
    )
    return {
        "weights": weights,
        "return": port_return,
        "volatility": volatility,
        "risk_metric": risk_metric,
        "sharpe_ratio": sharpe,
    }


def backtest_window(
    series: np.ndarray,
    index: int,
    window_size: int,
    step_size: int,
    models: Sequence[str],
    confidence_level: float,
) -> Dict[str, Any]:
    start = index * step_size
    end = start + window_size
    test_end = min(end + step_size, len(series))
    window = series[start:end]
    test = series[end:test_end]
    result: Dict[str, Any] = {
        "window_idx": index,
        "start_idx": start,
        "end_idx": end,
        "test_start": end,
        "test_end": test_end,
        "n_test": int(len(test)),
    }
    for model in models:
        metrics = model_metrics(window, model, [confidence_level])
        var = next(value for key, value in metrics.items() if key.startswith("var_"))
        result[f"{model}_var"] = var
        result[f"{model}_breaches"] = int(np.sum(test < -var))
    return result


class ParallelRiskEngine:
    def __init__(
        self,
        n_jobs: Optional[int] = None,
        backend: str = "loky",
        verbose: int = 0,
        seed: Optional[int] = None,
    ) -> None:
        if backend not in BACKENDS:
            raise ValueError(f"backend must be one of {', '.join(BACKENDS)}")
        if n_jobs is None:
            n_jobs = mp.cpu_count()
        if (
            isinstance(n_jobs, bool)
            or not isinstance(n_jobs, int)
            or (n_jobs < 1 and n_jobs != -1)
        ):
            raise ValueError("n_jobs must be a positive integer or -1")
        self.n_jobs = mp.cpu_count() if n_jobs == -1 else n_jobs
        self.backend = backend
        self.verbose = verbose
        self.seed = seed
        logger.info(
            "Initialized ParallelRiskEngine with %s jobs using %s backend",
            self.n_jobs,
            backend,
        )

    def parallel(self) -> Parallel:
        return Parallel(n_jobs=self.n_jobs, backend=self.backend, verbose=self.verbose)

    def batches(self, total: int) -> List[int]:
        if (
            isinstance(total, bool)
            or not isinstance(total, (int, np.integer))
            or not 1 <= total <= MAX_SIMULATIONS
        ):
            raise ValueError(
                f"count must be an integer between 1 and {MAX_SIMULATIONS}"
            )
        parts = min(self.n_jobs * 4, total)
        base, extra = divmod(int(total), parts)
        return [base + (1 if i < extra else 0) for i in range(parts)]

    def parallel_monte_carlo(
        self,
        risk_model: Any,
        weights: Any,
        n_scenarios: int = 10000,
        confidence_levels: Optional[Sequence[float]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        levels = [validate_confidence(c) for c in (confidence_levels or [0.95, 0.99])]
        start = time.time()
        sizes = self.batches(n_scenarios)
        seeds = spawn_seeds(seed if seed is not None else self.seed, len(sizes))
        batches = self.parallel()(
            delayed(risk_model.generate_scenarios)(size, seed=s)
            for size, s in zip(sizes, seeds, strict=False)
        )
        scenarios = pd.concat(batches, ignore_index=True)
        vector = weight_vector(weights, list(risk_model.asset_names))
        values = scenarios.to_numpy() @ vector
        return {
            "portfolio_metrics": {
                "expected_return": float(values.mean()),
                "volatility": float(values.std()),
                "skewness": float(stats.skew(values)),
                "kurtosis": float(stats.kurtosis(values)),
                "min_return": float(values.min()),
                "max_return": float(values.max()),
            },
            "risk_metrics": tail_metrics(values, levels),
            "n_scenarios": int(len(values)),
            "time_taken": time.time() - start,
        }

    def parallel_portfolio_optimization(
        self,
        returns: Any,
        risk_model: str = "markowitz",
        n_portfolios: int = 1000,
        risk_free_rate: float = RISK_FREE_RATE,
        target_return: Optional[float] = None,
        target_risk: Optional[float] = None,
        periods_per_year: int = TRADING_DAYS,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        if risk_model not in OPTIMIZATION_RISK_MODELS:
            raise ValueError(
                f"risk_model must be one of {', '.join(OPTIMIZATION_RISK_MODELS)}"
            )
        frame = as_frame(returns, min_rows=10)
        if frame.shape[1] < 2:
            raise ValueError("At least two assets are required")
        start = time.time()
        assets = list(frame.columns)
        values = frame.to_numpy()
        sizes = self.batches(n_portfolios)
        seeds = spawn_seeds(seed if seed is not None else self.seed, len(sizes))
        corners = np.vstack(
            [np.eye(len(assets)), np.full(len(assets), 1.0 / len(assets))]
        )
        use_corners = sizes[0] > len(corners)
        if use_corners:
            sizes[0] -= len(corners)
        batches = self.parallel()(
            delayed(sample_portfolios)(
                values,
                size,
                risk_model,
                risk_free_rate,
                periods_per_year,
                s,
                corners if use_corners and i == 0 else None,
            )
            for i, (size, s) in enumerate(zip(sizes, seeds, strict=False))
        )
        table = pd.concat(
            [
                pd.DataFrame(
                    np.column_stack(
                        [
                            b["weights"],
                            b["return"],
                            b["volatility"],
                            b["risk_metric"],
                            b["sharpe_ratio"],
                        ]
                    ),
                    columns=assets
                    + ["return", "volatility", "risk_metric", "sharpe_ratio"],
                )
                for b in batches
            ],
            ignore_index=True,
        )
        frontier = self.efficient_frontier(table)
        result: Dict[str, Any] = {
            "efficient_frontier": frontier,
            "max_sharpe_portfolio": self.describe(
                table, table["sharpe_ratio"].idxmax(), assets
            ),
            "min_volatility_portfolio": self.describe(
                table, table["volatility"].idxmin(), assets
            ),
            "target_portfolios": {},
            "all_portfolios": table,
            "n_portfolios": int(len(table)),
        }
        if target_return is not None:
            idx = (table["return"] - target_return).abs().idxmin()
            result["target_portfolios"]["target_return"] = self.describe(
                table, idx, assets
            )
        if target_risk is not None:
            idx = (table["volatility"] - target_risk).abs().idxmin()
            result["target_portfolios"]["target_risk"] = self.describe(
                table, idx, assets
            )
        result["time_taken"] = time.time() - start
        return result

    @staticmethod
    def describe(table: pd.DataFrame, idx: Any, assets: List[str]) -> Dict[str, Any]:
        row = table.loc[idx]
        return {
            "weights": {asset: float(row[asset]) for asset in assets},
            "return": float(row["return"]),
            "volatility": float(row["volatility"]),
            "sharpe_ratio": float(row["sharpe_ratio"]),
        }

    @staticmethod
    def efficient_frontier(table: pd.DataFrame) -> pd.DataFrame:
        ordered = table.sort_values(["volatility", "return"], ascending=[True, False])
        best = -np.inf
        keep = []
        for idx, value in ordered["return"].items():
            if value > best:
                keep.append(idx)
                best = value
        return table.loc[keep].reset_index(drop=True)

    def parallel_batch_risk_calculation(
        self,
        returns: Any,
        risk_models: Optional[Sequence[str]] = None,
        confidence_levels: Optional[Sequence[float]] = None,
        weights: Any = None,
    ) -> Dict[str, Any]:
        models = list(risk_models or RISK_MODELS)
        unknown = [m for m in models if m not in RISK_MODELS]
        if unknown:
            raise ValueError(f"Unsupported risk models: {unknown}")
        levels = [validate_confidence(c) for c in (confidence_levels or [0.95, 0.99])]
        frame = as_frame(returns, min_rows=30)
        values = portfolio_returns(frame, weights).to_numpy()
        start = time.time()
        results = self.parallel()(
            delayed(model_metrics)(values, m, levels) for m in models
        )
        return {
            "risk_metrics": dict(zip(models, results, strict=False)),
            "time_taken": time.time() - start,
        }

    def resolve_shocks(
        self, shocks: Dict[str, float], assets: List[str], classes: Dict[str, str]
    ) -> np.ndarray:
        vector = np.zeros(len(assets))
        for target, shock in shocks.items():
            if target == "all":
                vector += shock
                continue
            for i, asset in enumerate(assets):
                if target == asset or target.lower() == classes.get(asset, "").lower():
                    vector[i] += shock
        return vector

    def scenario_result(
        self,
        base: np.ndarray,
        impact: float,
        shocks: Any,
        name: str,
        description: str,
        affected: List[str],
    ) -> Dict[str, Any]:
        shifted = base + impact
        var95, es95 = historical_var_es(shifted, 0.95)
        var99, es99 = historical_var_es(shifted, 0.99)
        return {
            "scenario_name": name,
            "description": description,
            "shocks": shocks,
            "assets_affected": affected,
            "applied": bool(affected),
            "portfolio_return": float(impact),
            "var_95": var95,
            "var_99": var99,
            "es_95": es95,
            "es_99": es99,
        }

    def parallel_stress_testing(
        self,
        returns: Any,
        weights: Any,
        predefined_scenarios: Optional[Dict[str, Dict[str, Any]]] = None,
        n_custom_scenarios: int = 100,
        asset_classes: Optional[Dict[str, str]] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        frame = as_frame(returns, min_rows=30)
        assets = list(frame.columns)
        vector = weight_vector(weights, assets)
        classes = {a: infer_asset_class(a) for a in assets}
        classes.update(asset_classes or {})
        scenarios = predefined_scenarios or DEFAULT_SCENARIOS
        if (
            isinstance(n_custom_scenarios, bool)
            or not isinstance(n_custom_scenarios, int)
            or not 1 <= n_custom_scenarios <= 100000
        ):
            raise ValueError(
                "n_custom_scenarios must be an integer between 1 and 100000"
            )
        start = time.time()
        base = frame.to_numpy() @ vector
        predefined: Dict[str, Any] = {}
        for name, scenario in scenarios.items():
            shock_vector = self.resolve_shocks(scenario["shocks"], assets, classes)
            affected = [a for a, s in zip(assets, shock_vector, strict=False) if s != 0]
            predefined[name] = self.scenario_result(
                base,
                float(shock_vector @ vector),
                scenario["shocks"],
                name,
                scenario.get("description", name),
                affected,
            )
        rng = np.random.default_rng(seed if seed is not None else self.seed)
        covariance = np.cov(frame.to_numpy(), rowvar=False).reshape(
            len(assets), len(assets)
        )
        shocks = (
            rng.multivariate_normal(
                np.zeros(len(assets)), covariance, size=n_custom_scenarios
            )
            * 3.0
        )
        impacts = shocks @ vector
        custom_vars = np.array([historical_var_es(base + i, 0.95)[0] for i in impacts])
        worst_return = int(np.argmin(impacts))
        worst_var = int(np.argmax(custom_vars))

        def custom(i: int) -> Dict[str, Any]:
            result = self.scenario_result(
                base,
                float(impacts[i]),
                dict(zip(assets, shocks[i].tolist(), strict=False)),
                f"custom_{i}",
                "Random covariance shock",
                assets,
            )
            result["scenario_type"] = "custom"
            return result

        return {
            "predefined_scenarios": predefined,
            "custom_scenarios_summary": {
                "count": n_custom_scenarios,
                "avg_return": float(impacts.mean()),
                "min_return": float(impacts.min()),
                "max_return": float(impacts.max()),
                "std_return": float(impacts.std()),
                "avg_var_95": float(custom_vars.mean()),
                "max_var_95": float(custom_vars.max()),
            },
            "worst_case_scenarios": {
                "worst_return": custom(worst_return),
                "worst_var": custom(worst_var),
            },
            "time_taken": time.time() - start,
        }

    def parallel_backtest(
        self,
        returns: Any,
        risk_models: Optional[Sequence[str]] = None,
        confidence_level: float = 0.95,
        window_size: int = 252,
        step_size: int = 20,
        weights: Any = None,
    ) -> Dict[str, Any]:
        models = list(risk_models or RISK_MODELS)
        unknown = [m for m in models if m not in RISK_MODELS]
        if unknown:
            raise ValueError(f"Unsupported risk models: {unknown}")
        confidence_level = validate_confidence(confidence_level)
        if window_size < 30 or step_size < 1:
            raise ValueError("window_size must be at least 30 and step_size at least 1")
        series = portfolio_returns(as_frame(returns, min_rows=30), weights).to_numpy()
        if window_size >= len(series):
            raise ValueError(
                "window_size must be smaller than the number of observations"
            )
        start = time.time()
        n_windows = (len(series) - window_size - 1) // step_size + 1
        windows = self.parallel()(
            delayed(backtest_window)(
                series, i, window_size, step_size, models, confidence_level
            )
            for i in range(n_windows)
        )
        expected = 1.0 - confidence_level
        total = int(sum(w["n_test"] for w in windows))
        summary = {}
        for model in models:
            breaches = int(sum(w[f"{model}_breaches"] for w in windows))
            rate = breaches / total if total else float("nan")
            summary[model] = {
                "breaches": breaches,
                "total": total,
                "breach_rate": rate,
                "expected_breach_rate": expected,
                "breach_ratio": rate / expected if total else float("nan"),
                "kupiec_pvalue": kupiec_pvalue(breaches, total, expected),
            }
        return {
            "summary": summary,
            "windows": windows,
            "time_taken": time.time() - start,
        }

    def parallel_sensitivity_analysis(
        self,
        returns: Any,
        weights: Any,
        shock_range: Sequence[float] = (-0.1, 0.1),
        n_points: int = 10,
    ) -> Dict[str, Any]:
        frame = as_frame(returns, min_rows=30)
        assets = list(frame.columns)
        vector = weight_vector(weights, assets)
        if isinstance(n_points, bool) or not isinstance(n_points, int) or n_points < 2:
            raise ValueError("n_points must be an integer of at least 2")
        points = np.linspace(shock_range[0], shock_range[1], n_points)
        base = frame.to_numpy() @ vector
        start = time.time()
        factor_results: Dict[str, Any] = {}
        sensitivities: Dict[str, Any] = {}
        span = points[-1] - points[0]
        for i, factor in enumerate(assets):
            shifted = base[:, None] + vector[i] * points[None, :]
            var = np.array(
                [historical_var_es(shifted[:, k], 0.95)[0] for k in range(n_points)]
            )
            es = np.array(
                [historical_var_es(shifted[:, k], 0.95)[1] for k in range(n_points)]
            )
            result = {
                "factor": factor,
                "shocks": points,
                "portfolio_returns": shifted.mean(axis=0),
                "portfolio_volatilities": shifted.std(axis=0),
                "var_95": var,
                "es_95": es,
            }
            factor_results[factor] = result
            sensitivities[factor] = {
                "return_sensitivity": (
                    float(
                        (
                            result["portfolio_returns"][-1]
                            - result["portfolio_returns"][0]
                        )
                        / span
                    )
                    if abs(span) > 1e-10
                    else 0.0
                ),
                "var_sensitivity": (
                    float((var[-1] - var[0]) / span) if abs(span) > 1e-10 else 0.0
                ),
            }
        return {
            "factor_results": factor_results,
            "sensitivities": sensitivities,
            "time_taken": time.time() - start,
        }

    def parallel_risk_decomposition(
        self,
        returns: Any,
        weights: Any,
        risk_measure: str = "volatility",
        confidence: float = 0.95,
    ) -> Dict[str, Any]:
        if risk_measure not in ("volatility", "var", "es"):
            raise ValueError(f"Unsupported risk measure: {risk_measure}")
        frame = as_frame(returns, min_rows=30)
        assets = list(frame.columns)
        vector = weight_vector(weights, assets)
        values = frame.to_numpy()
        start = time.time()
        series = values @ vector
        if risk_measure == "volatility":
            covariance = np.atleast_2d(np.cov(values, rowvar=False))
            portfolio_risk = float(np.sqrt(vector @ covariance @ vector))
            if portfolio_risk <= 0:
                raise ValueError("Portfolio risk is zero")
            marginal = covariance @ vector / portfolio_risk
            component = vector * marginal
        else:
            confidence = validate_confidence(confidence)
            var, es = historical_var_es(series, confidence)
            if risk_measure == "es":
                portfolio_risk = es
                tail = series <= np.quantile(series, 1.0 - confidence)
                marginal = -values[tail].mean(axis=0)
                component = vector * marginal
            else:
                portfolio_risk = var
                band = max(5, int(0.01 * len(series)))
                order = np.argsort(series)
                position = int(
                    np.searchsorted(
                        np.sort(series), np.quantile(series, 1.0 - confidence)
                    )
                )
                lo = max(0, position - band // 2)
                nearest = order[lo : lo + band]
                marginal = -values[nearest].mean(axis=0)
                component = vector * marginal
                total = component.sum()
                if abs(total) > 1e-15:
                    scale = portfolio_risk / total
                    component = component * scale
                    marginal = marginal * scale
        percentage = (
            component / portfolio_risk if portfolio_risk else np.zeros_like(component)
        )
        contributions = sorted(
            (
                {
                    "asset": asset,
                    "weight": float(vector[i]),
                    "marginal_contribution": float(marginal[i]),
                    "component_contribution": float(component[i]),
                    "percentage_contribution": float(percentage[i]),
                }
                for i, asset in enumerate(assets)
            ),
            key=lambda item: item["percentage_contribution"],
            reverse=True,
        )
        return {
            "risk_measure": risk_measure,
            "portfolio_risk": float(portfolio_risk),
            "total_risk": float(portfolio_risk),
            "contributions": contributions,
            "component_contributions": [
                c["component_contribution"] for c in contributions
            ],
            "percentage_contributions": [
                c["percentage_contribution"] for c in contributions
            ],
            "time_taken": time.time() - start,
        }

    def system_info(self) -> Dict[str, Any]:
        try:
            cpu_percent: Optional[float] = psutil.cpu_percent(interval=0.1)
        except Exception:
            cpu_percent = None
        try:
            memory = psutil.virtual_memory()
            memory_info: Optional[Dict[str, float]] = {
                "total": memory.total,
                "available": memory.available,
                "percent": memory.percent,
            }
        except Exception:
            memory_info = None
        return {
            "cpu_count": mp.cpu_count(),
            "cpu_percent": cpu_percent,
            "memory": memory_info,
            "backend": self.backend,
            "n_jobs": self.n_jobs,
        }
