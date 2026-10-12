import base64
import logging
import os
import re
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

import numpy as np
import pandas as pd
from src.core.exceptions import CalculationError, ModelError, ValidationError
from src.services.quant_ml_bridge import ensure_quant_ml

ensure_quant_ml()

QUANT_ML_IMPORT_ERROR: Optional[Exception] = None

try:
    from quant_ml import settings as quant_settings
    from quant_ml.data.loaders import available_symbols, load_close_prices
    from quant_ml.optimization.mean_variance import (
        discrete_allocation_suggestion,
        mean_variance_optimization,
    )
    from quant_ml.reporting import (
        EmailDelivery,
        ReportArchive,
        ReportGenerator,
        ReportTemplate,
    )
    from quant_ml.risk import (
        CopulaMLRiskModel,
        ExtremeValueRisk,
        HybridRiskModel,
        MLRiskModel,
        ParallelRiskEngine,
    )
    from quant_ml.risk.analysis import run_risk_analysis
    from quant_ml.risk.common import (
        as_frame,
        level_key,
        portfolio_returns,
        weight_vector,
    )
    from quant_ml.serialization import to_jsonable
except ImportError as import_error:
    QUANT_ML_IMPORT_ERROR = import_error

logger = logging.getLogger(__name__)

MAX_ROWS = 5000
MAX_ASSETS = 50
MAX_SCENARIOS = 200_000
MAX_PORTFOLIOS = 100_000
MAX_FRONTIER_POINTS = 200
MAX_WINDOWS = 200
REPORT_NAME = re.compile(r"^[A-Za-z0-9_-]+_\d{8}_\d{6}_\d{6}\.(html|pdf)$")
ENGINE_JOBS = max(1, int(os.getenv("QUANT_ML_N_JOBS", "1")))


def failure(error: Exception, operation: str) -> Exception:
    if isinstance(error, (ValidationError, ModelError, CalculationError)):
        return error
    if isinstance(error, (ValueError, TypeError, KeyError, FileNotFoundError)):
        return ValidationError(str(error))
    if isinstance(error, ArithmeticError):
        return CalculationError(f"{operation} failed: {error}", operation)
    logger.error("%s failed: %s", operation, error, exc_info=True)
    return error


class QuantRiskService:
    def __init__(self) -> None:
        if QUANT_ML_IMPORT_ERROR is not None:
            raise ModelError(
                f"quant_ml package is unavailable: {QUANT_ML_IMPORT_ERROR}", "quant_ml"
            )
        self.engine = ParallelRiskEngine(n_jobs=ENGINE_JOBS, backend="loky")
        self.archive = ReportArchive()

    def returns_from(
        self,
        symbols: Optional[List[str]] = None,
        returns: Any = None,
        minimum_assets: int = 1,
    ) -> pd.DataFrame:
        if returns is not None:
            frame = as_frame(returns, min_rows=30)
        elif symbols:
            prices = load_close_prices(symbols, minimum_symbols=1)
            frame = prices.pct_change().dropna()
        else:
            raise ValidationError("Provide either symbols or returns")
        if len(frame) > MAX_ROWS:
            raise ValidationError(f"Data exceeds {MAX_ROWS} rows")
        if frame.shape[1] > MAX_ASSETS:
            raise ValidationError(f"Data exceeds {MAX_ASSETS} assets")
        if frame.shape[1] < minimum_assets:
            raise ValidationError(f"At least {minimum_assets} assets are required")
        return frame

    def run(self, operation: str, function: Any) -> Dict[str, Any]:
        try:
            return to_jsonable(function())
        except Exception as error:
            raise failure(error, operation) from error

    def evt(
        self,
        symbols=None,
        returns=None,
        weights=None,
        confidence_levels=(0.95, 0.99),
        threshold_quantile: float = 0.1,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            series = portfolio_returns(frame, weights).to_numpy()
            model = ExtremeValueRisk(seed=seed).fit_pot(
                series, threshold_quantile=threshold_quantile
            )
            params = model.pot_params
            risk = {}
            for confidence in confidence_levels:
                risk[level_key(confidence)] = {
                    method: {
                        "var": model.calculate_var(confidence, method),
                        "es": model.calculate_es(confidence, method),
                    }
                    for method in ("evt", "historical", "normal")
                }
            return {
                "observations": int(len(series)),
                "tail": {
                    "shape": params["shape"],
                    "scale": params["scale"],
                    "loss_threshold": params["loss_threshold"],
                    "tail_fraction": params["tail_fraction"],
                    "exceedances": params["n_exceedances"],
                },
                "risk": risk,
            }

        return self.run("EVT risk", compute)

    def ml_risk(
        self,
        symbols=None,
        returns=None,
        weights=None,
        model_type: str = "gbm",
        confidence_levels=(0.95, 0.99),
        feature_window: int = 10,
        horizon: int = 1,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            model = MLRiskModel(model_type).fit(
                frame, feature_window, horizon, weights=weights
            )
            forecast = {
                level_key(c): {
                    "var": model.forecast_var(frame, c),
                    "es": model.forecast_es(frame, c),
                }
                for c in confidence_levels
            }
            importance = None
            if model.feature_importance is not None:
                importance = model.feature_importance.head(10).to_dict(orient="records")
            return {
                "model_type": model_type,
                "next_period_forecast": forecast,
                "validation": model.metrics,
                "feature_importance": importance,
            }

        return self.run("ML risk", compute)

    def copula_risk(
        self,
        symbols=None,
        returns=None,
        weights=None,
        copula_type: str = "gaussian",
        confidence_levels=(0.95, 0.99),
        n_scenarios: int = 20000,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            model = CopulaMLRiskModel(copula_type, n_scenarios, seed).fit(frame)
            return {
                "copula_type": copula_type,
                "metrics": model.calculate_risk_metrics(weights, confidence_levels),
                "correlation": pd.DataFrame(
                    model.correlation_matrix,
                    index=model.asset_names,
                    columns=model.asset_names,
                ).to_dict(),
            }

        return self.run("Copula risk", compute)

    def hybrid_risk(
        self,
        symbols=None,
        returns=None,
        weights=None,
        traditional_weight: float = 0.5,
        ml_model_type: str = "gbm",
        copula_type: str = "gaussian",
        confidence_levels=(0.95, 0.99),
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            vector = weight_vector(weights, list(frame.columns))
            model = HybridRiskModel(
                traditional_weight, ml_model_type, copula_type, seed
            )
            model.fit(frame, weights=vector)
            return {
                "traditional_weight": traditional_weight,
                "metrics": model.calculate_risk_metrics(
                    frame, vector, confidence_levels
                ),
            }

        return self.run("Hybrid risk", compute)

    def monte_carlo(
        self,
        symbols=None,
        returns=None,
        weights=None,
        copula_type: str = "t",
        n_scenarios: int = 50000,
        confidence_levels=(0.95, 0.99),
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            model = CopulaMLRiskModel(copula_type, 1000, seed).fit(frame)
            return self.engine.parallel_monte_carlo(
                model, weights, n_scenarios, confidence_levels, seed
            )

        return self.run("Monte Carlo simulation", compute)

    def batch_risk(
        self,
        symbols=None,
        returns=None,
        weights=None,
        risk_models=None,
        confidence_levels=(0.95, 0.99),
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            return self.engine.parallel_batch_risk_calculation(
                frame, risk_models, confidence_levels, weights
            )

        return self.run("Batch risk", compute)

    def stress_test(
        self,
        symbols=None,
        returns=None,
        weights=None,
        scenarios=None,
        n_custom_scenarios: int = 100,
        asset_classes=None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            return self.engine.parallel_stress_testing(
                frame, weights, scenarios, n_custom_scenarios, asset_classes, seed
            )

        return self.run("Stress test", compute)

    def backtest(
        self,
        symbols=None,
        returns=None,
        weights=None,
        risk_models=None,
        confidence_level: float = 0.95,
        window_size: int = 252,
        step_size: int = 20,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            result = self.engine.parallel_backtest(
                frame, risk_models, confidence_level, window_size, step_size, weights
            )
            windows = result["windows"]
            result["window_count"] = len(windows)
            result["windows"] = windows[-MAX_WINDOWS:]
            return result

        return self.run("Backtest", compute)

    def sensitivity(
        self,
        symbols=None,
        returns=None,
        weights=None,
        shock_range: Sequence[float] = (-0.1, 0.1),
        n_points: int = 10,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            return self.engine.parallel_sensitivity_analysis(
                frame, weights, shock_range, n_points
            )

        return self.run("Sensitivity analysis", compute)

    def decomposition(
        self,
        symbols=None,
        returns=None,
        weights=None,
        risk_measure: str = "volatility",
        confidence: float = 0.95,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            return self.engine.parallel_risk_decomposition(
                frame, weights, risk_measure, confidence
            )

        return self.run("Risk decomposition", compute)

    def analysis(
        self,
        symbols=None,
        returns=None,
        confidence: float = 0.99,
        horizon: int = 5,
        stress_multiplier: float = 4.0,
        n_simulations: int = 10000,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            logs = np.log1p(frame)
            return run_risk_analysis(
                var_confidence=confidence,
                horizon=horizon,
                stress_multiplier=stress_multiplier,
                n_simulations=n_simulations,
                seed=seed,
                returns=logs,
            )

        return self.run("Risk analysis", compute)

    def portfolio_search(
        self,
        symbols=None,
        returns=None,
        risk_model: str = "markowitz",
        n_portfolios: int = 5000,
        target_return: Optional[float] = None,
        target_risk: Optional[float] = None,
        seed: Optional[int] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns, minimum_assets=2)
            result = self.engine.parallel_portfolio_optimization(
                frame,
                risk_model,
                n_portfolios,
                target_return=target_return,
                target_risk=target_risk,
                seed=seed,
            )
            frontier = result["efficient_frontier"]
            if len(frontier) > MAX_FRONTIER_POINTS:
                keep = np.linspace(0, len(frontier) - 1, MAX_FRONTIER_POINTS).astype(
                    int
                )
                frontier = frontier.iloc[keep]
            result["efficient_frontier"] = frontier
            del result["all_portfolios"]
            return result

        return self.run("Portfolio search", compute)

    def mean_variance(
        self,
        symbols=None,
        risk_free_rate: float = 0.02,
        max_weight: float = 1.0,
        portfolio_value: Optional[float] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            if not symbols:
                raise ValidationError("symbols are required")
            prices = load_close_prices(symbols)
            result = mean_variance_optimization(prices, risk_free_rate, max_weight)
            if portfolio_value is not None:
                result["discrete_allocation"] = discrete_allocation_suggestion(
                    prices, result["max_sharpe_weights"], portfolio_value
                )
            return result

        return self.run("Mean variance optimization", compute)

    def generate_report(
        self,
        symbols=None,
        returns=None,
        weights=None,
        title: str = "Portfolio Risk Report",
        confidence_levels=(0.95, 0.99),
        report_format: str = "html",
        recipients: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            frame = self.returns_from(symbols, returns)
            batch = self.engine.parallel_batch_risk_calculation(
                frame, None, confidence_levels, weights
            )
            decomposition = self.engine.parallel_risk_decomposition(
                frame, weights, "es", max(confidence_levels)
            )
            stress = self.engine.parallel_stress_testing(
                frame, weights, n_custom_scenarios=50
            )
            metrics = (
                pd.DataFrame(batch["risk_metrics"])
                .T.reset_index()
                .rename(columns={"index": "model"})
            )
            contributions = pd.DataFrame(decomposition["contributions"])
            scenarios = pd.DataFrame(
                [
                    {
                        "scenario": name,
                        "portfolio_return": item["portfolio_return"],
                        "var_95": item["var_95"],
                        "es_95": item["es_95"],
                        "applied": item["applied"],
                    }
                    for name, item in stress["predefined_scenarios"].items()
                ]
            )
            template = ReportTemplate(
                title, author="RiskOptimizer", description="Generated risk report"
            )
            template.add_section(
                "Summary",
                f"Portfolio of {frame.shape[1]} assets over {len(frame)} observations. "
                "Risk figures are one period losses expressed as fractions of portfolio value.",
                "text",
            )
            template.add_section(
                "Value at Risk and Expected Shortfall",
                {"data_key": "metrics", "options": {"show_index": False}},
                "table",
            )
            template.add_section(
                "Expected Shortfall Contributions",
                {"data_key": "contributions", "options": {"show_index": False}},
                "table",
            )
            template.add_section(
                "Stress Scenarios",
                {"data_key": "scenarios", "options": {"show_index": False}},
                "table",
            )
            template.add_section(
                "Contribution Chart",
                {
                    "data_key": "chart",
                    "chart_type": "bar",
                    "options": {"title": "Percentage contribution to ES", "grid": True},
                },
                "chart",
            )
            chart = {
                "x": contributions["asset"].tolist(),
                "y": contributions["percentage_contribution"].tolist(),
            }
            data = {
                "metrics": metrics,
                "contributions": contributions,
                "scenarios": scenarios,
                "chart": chart,
            }
            generator = ReportGenerator(template)
            directory = quant_settings.report_dir() / "generated"
            directory.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            source = directory / f"risk_report_{stamp}.{report_format}"
            if report_format == "pdf":
                written = generator.generate_pdf(str(source), data)
            else:
                written = generator.generate_html(str(source), data)
            if not written:
                raise CalculationError("Report could not be written", "report")
            archived = self.archive.archive_report(
                str(source),
                "risk",
                {
                    "title": title,
                    "assets": list(frame.columns),
                    "observations": len(frame),
                },
            )
            result: Dict[str, Any] = {
                "report_id": os.path.basename(archived) if archived else None,
                "format": report_format,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }
            if report_format == "pdf":
                result["pdf_base64"] = base64.b64encode(source.read_bytes()).decode(
                    "ascii"
                )
            else:
                result["html"] = source.read_text(encoding="utf-8")
            if recipients:
                result["delivery"] = self.deliver(str(source), recipients)
            return result

        return self.run("Report generation", compute)

    def deliver(self, path: str, recipients: List[str]) -> Dict[str, Any]:
        delivery = EmailDelivery.from_environment()
        if delivery is None:
            return {"delivered": False, "error": "Email delivery is not configured"}
        try:
            return {"delivered": bool(delivery(path, recipients)), "error": None}
        except Exception as error:
            logger.error("Report delivery failed: %s", error)
            return {"delivered": False, "error": str(error)}

    def list_reports(self, limit: int = 20) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            items = self.archive.list_archived_reports("risk", limit)
            return {
                "reports": [
                    {
                        "report_id": item["filename"],
                        "created_at": item["timestamp"].isoformat(),
                        "metadata": item["metadata"],
                    }
                    for item in items
                ]
            }

        return self.run("Report listing", compute)

    def get_report(self, report_id: str) -> Dict[str, Any]:
        def compute() -> Dict[str, Any]:
            if not REPORT_NAME.match(report_id):
                raise ValidationError("Invalid report id", "report_id")
            path = os.path.join(self.archive.archive_dir, "risk", report_id)
            if report_id.endswith(".pdf"):
                if not os.path.isfile(path):
                    raise ValidationError("Report not found", "report_id")
                with open(path, "rb") as handle:
                    return {
                        "report_id": report_id,
                        "format": "pdf",
                        "pdf_base64": base64.b64encode(handle.read()).decode("ascii"),
                    }
            html = self.archive.get_report(path)
            if html is None:
                raise ValidationError("Report not found", "report_id")
            return {"report_id": report_id, "format": "html", "html": html}

        return self.run("Report retrieval", compute)

    def info(self) -> Dict[str, Any]:
        return to_jsonable(
            {
                "engine": self.engine.system_info(),
                "available_symbols": available_symbols(),
                "risk_models": [
                    "evt",
                    "ml",
                    "copula",
                    "hybrid",
                    "monte_carlo",
                    "batch",
                ],
                "report_formats": ["html", "pdf"],
                "report_delivery_configured": EmailDelivery.from_environment()
                is not None,
                "copula_types": ["gaussian", "t", "clayton", "gumbel"],
                "ml_model_types": ["gbm", "rf", "nn"],
                "limits": {
                    "max_rows": MAX_ROWS,
                    "max_assets": MAX_ASSETS,
                    "max_scenarios": MAX_SCENARIOS,
                    "max_portfolios": MAX_PORTFOLIOS,
                },
            }
        )


_service: Optional[QuantRiskService] = None
_service_lock = threading.Lock()


def get_quant_service() -> QuantRiskService:
    global _service
    if _service is None:
        with _service_lock:
            if _service is None:
                _service = QuantRiskService()
    return _service


def reset_quant_service() -> None:
    global _service
    with _service_lock:
        _service = None
