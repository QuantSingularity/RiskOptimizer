import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from quant_ml.reporting import (
    EmailDelivery,
    ReportArchive,
    ReportGenerator,
    ReportTemplate,
    validate_recipients,
)
from quant_ml.risk import performance_summary
from quant_ml.risk.common import historical_var_es
from src.tasks.celery_app import (
    TaskValidationError,
    celery_app,
    task_result_manager,
    task_with_progress,
)
from src.tasks.quant_adapter import (
    list_portfolios,
    load_portfolio_returns,
    output_directory,
    safe_filename,
    translate_errors,
)

logger = logging.getLogger(__name__)

REPORT_FORMATS = ("pdf", "html")
EXPORT_FORMATS = ("excel", "csv")


def now() -> str:
    return datetime.now(timezone.utc).replace(tzinfo=None).isoformat()


def stamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def progress(task: Any, percent: int, status: str) -> None:
    task_result_manager.store_task_progress(
        task.request.id, {"progress": percent, "status": status}
    )


def fail(task: Any, label: str, error: Exception) -> None:
    logger.error("%s failed for task %s: %s", label, task.request.id, error)
    task_result_manager.store_task_progress(
        task.request.id, {"progress": 0, "status": f"Failed: {error}"}
    )


def get_file_size(path: Any) -> int:
    try:
        return os.path.getsize(path)
    except OSError:
        return 0


def report_format(config: Dict[str, Any]) -> str:
    value = config.get("format", "pdf")
    if value not in REPORT_FORMATS:
        raise TaskValidationError(f"format must be one of {', '.join(REPORT_FORMATS)}")
    return value


def percent(value: Any) -> str:
    return f"{float(value):.2%}"


def metric_table(rows: List[tuple]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["Metric", "Value"])


def render(template: ReportTemplate, data: Dict[str, Any], path: Path) -> None:
    generator = ReportGenerator(template)
    written = (
        generator.generate_pdf(str(path), data)
        if path.suffix == ".pdf"
        else generator.generate_html(str(path), data)
    )
    if not written:
        raise RuntimeError("Report could not be written")


def deliver(path: Path, config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    recipients = config.get("recipients")
    if not recipients:
        return None
    with translate_errors():
        addresses = validate_recipients(recipients)
    delivery = EmailDelivery.from_environment()
    if delivery is None:
        return {"delivered": False, "error": "No delivery handler configured"}
    try:
        return {"delivered": bool(delivery(str(path), addresses)), "error": None}
    except Exception as error:
        logger.error("Report delivery failed: %s", error)
        return {"delivered": False, "error": str(error)}


def build_portfolio_template(portfolio_data: Dict[str, Any]) -> tuple:
    holdings = portfolio_data["holdings"]
    if not isinstance(holdings, dict) or not holdings:
        raise TaskValidationError("holdings must be a non-empty mapping")
    for asset, value in holdings.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise TaskValidationError(
                f"Holding value for {asset} must be a non-negative number"
            )
    total = float(sum(holdings.values()))
    if total <= 0:
        raise TaskValidationError("Total portfolio value must be positive")
    name = str(portfolio_data["portfolio_name"])
    template = ReportTemplate(
        "Portfolio Analysis Report",
        description=f"Portfolio: {name}",
        author="RiskOptimizer",
    )
    template.add_section("Portfolio Summary", f"Total value: {total:,.2f}", "text")
    template.add_section(
        "Holdings", {"data_key": "holdings", "options": {"show_index": False}}, "table"
    )
    data: Dict[str, Any] = {
        "holdings": pd.DataFrame(
            [
                {
                    "Asset": asset,
                    "Weight": f"{value / total:.2%}",
                    "Value": f"{value:,.2f}",
                }
                for asset, value in holdings.items()
            ]
        )
    }
    template.add_section(
        "Allocation", {"data_key": "allocation", "chart_type": "pie"}, "chart"
    )
    data["allocation"] = {
        "labels": list(holdings),
        "values": [float(v) for v in holdings.values()],
    }
    performance = portfolio_data.get("performance_data")
    if isinstance(performance, dict) and performance:
        template.add_section(
            "Performance Analysis",
            {"data_key": "performance", "options": {"show_index": False}},
            "table",
        )
        data["performance"] = metric_table(
            [
                ("Total Return", percent(performance.get("total_return", 0))),
                ("Annualized Return", percent(performance.get("annualized_return", 0))),
                ("Volatility", percent(performance.get("volatility", 0))),
                ("Sharpe Ratio", f"{float(performance.get('sharpe_ratio', 0)):.2f}"),
                ("Max Drawdown", percent(performance.get("max_drawdown", 0))),
            ]
        )
    risk = portfolio_data.get("risk_metrics")
    if isinstance(risk, dict) and risk:
        template.add_section(
            "Risk Analysis",
            {"data_key": "risk", "options": {"show_index": False}},
            "table",
        )
        data["risk"] = metric_table(
            [
                ("VaR (95%)", percent(risk.get("var_95", 0))),
                ("VaR (99%)", percent(risk.get("var_99", 0))),
                ("CVaR (95%)", percent(risk.get("cvar_95", 0))),
                ("CVaR (99%)", percent(risk.get("cvar_99", 0))),
            ]
        )
    return template, data, name


@task_with_progress()
def generate_portfolio_report(
    self, portfolio_data: Dict, report_config: Dict
) -> Dict[str, Any]:
    try:
        for field in ("portfolio_name", "holdings", "performance_data"):
            if field not in portfolio_data:
                raise TaskValidationError(f"Missing required field: {field}")
        extension = report_format(report_config)
        progress(self, 20, "Building report")
        template, data, name = build_portfolio_template(portfolio_data)
        filename = f"portfolio_report_{safe_filename(name)}_{stamp()}.{extension}"
        path = output_directory() / filename
        progress(self, 60, "Rendering report")
        render(template, data, path)
        results = {
            "report_path": str(path),
            "report_filename": filename,
            "report_type": "portfolio_analysis",
            "portfolio_name": name,
            "generated_at": now(),
            "file_size_bytes": get_file_size(path),
            "metadata": {"task_id": self.request.id, "report_config": report_config},
        }
        delivery = deliver(path, report_config)
        if delivery is not None:
            results["delivery"] = delivery
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Portfolio report generation", error)
        raise


@task_with_progress()
def generate_risk_report(
    self, risk_analysis_data: Dict, report_config: Dict
) -> Dict[str, Any]:
    try:
        extension = report_format(report_config)
        progress(self, 20, "Building report")
        template = ReportTemplate(
            "Risk Analysis Report",
            description="Simulation and stress test results",
            author="RiskOptimizer",
        )
        data: Dict[str, Any] = {}
        simulation = risk_analysis_data.get("monte_carlo_results")
        if isinstance(simulation, dict):
            template.add_section(
                "Monte Carlo Simulation Results",
                {"data_key": "simulation", "options": {"show_index": False}},
                "table",
            )
            data["simulation"] = metric_table(
                [
                    (
                        "Number of Simulations",
                        f"{int(simulation.get('num_simulations', 0)):,}",
                    ),
                    ("Time Horizon (days)", f"{simulation.get('time_horizon', 0)}"),
                    ("VaR (95%)", percent(simulation.get("var_95", 0))),
                    ("VaR (99%)", percent(simulation.get("var_99", 0))),
                    ("CVaR (95%)", percent(simulation.get("cvar_95", 0))),
                    ("CVaR (99%)", percent(simulation.get("cvar_99", 0))),
                    (
                        "Probability of Loss",
                        percent(simulation.get("probability_of_loss", 0)),
                    ),
                ]
            )
        stress = risk_analysis_data.get("stress_test_results")
        if isinstance(stress, dict) and stress.get("stress_results"):
            template.add_section(
                "Stress Test Results",
                {"data_key": "stress", "options": {"show_index": False}},
                "table",
            )
            data["stress"] = pd.DataFrame(
                [
                    {
                        "Scenario": str(
                            item.get("scenario", {}).get("type", "unknown")
                        ),
                        "Return Impact": percent(item.get("return_impact", 0)),
                        "Volatility Impact": percent(item.get("volatility_impact", 0)),
                        "Stressed VaR (95%)": percent(item.get("stressed_var_95", 0)),
                    }
                    for item in stress["stress_results"]
                ]
            )
        if not data:
            raise TaskValidationError(
                "risk_analysis_data must contain monte_carlo_results or stress_test_results"
            )
        filename = f"risk_report_{stamp()}.{extension}"
        path = output_directory() / filename
        progress(self, 60, "Rendering report")
        render(template, data, path)
        results = {
            "report_path": str(path),
            "report_filename": filename,
            "report_type": "risk_analysis",
            "generated_at": now(),
            "file_size_bytes": get_file_size(path),
            "metadata": {"task_id": self.request.id, "report_config": report_config},
        }
        delivery = deliver(path, report_config)
        if delivery is not None:
            results["delivery"] = delivery
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Risk report generation", error)
        raise


@task_with_progress()
def export_portfolio_data(
    self, portfolio_data: Dict, export_config: Dict
) -> Dict[str, Any]:
    try:
        export_format = export_config.get("format", "excel")
        if export_format not in EXPORT_FORMATS:
            raise TaskValidationError(
                f"format must be one of {', '.join(EXPORT_FORMATS)}"
            )
        holdings = portfolio_data.get("holdings")
        if not isinstance(holdings, dict) or not holdings:
            raise TaskValidationError("holdings must be a non-empty mapping")
        total = float(sum(holdings.values()))
        if total <= 0:
            raise TaskValidationError("Total portfolio value must be positive")
        progress(self, 30, "Preparing export")
        holdings_frame = pd.DataFrame(
            [
                {"Asset": asset, "Value": value, "Weight": value / total}
                for asset, value in holdings.items()
            ]
        )
        extension = "xlsx" if export_format == "excel" else "csv"
        filename = f"portfolio_data_{safe_filename(portfolio_data.get('portfolio_name', 'portfolio'))}_{stamp()}.{extension}"
        path = output_directory() / filename
        if export_format == "excel":
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                holdings_frame.to_excel(writer, sheet_name="Holdings", index=False)
                for key, sheet in (
                    ("performance_data", "Performance"),
                    ("risk_metrics", "Risk_Metrics"),
                ):
                    if isinstance(portfolio_data.get(key), dict):
                        pd.DataFrame([portfolio_data[key]]).to_excel(
                            writer, sheet_name=sheet, index=False
                        )
                if portfolio_data.get("historical_returns") is not None:
                    pd.DataFrame(portfolio_data["historical_returns"]).to_excel(
                        writer, sheet_name="Historical_Returns", index=False
                    )
        else:
            holdings_frame.to_csv(path, index=False)
        results = {
            "export_path": str(path),
            "export_filename": filename,
            "export_format": export_format,
            "portfolio_name": portfolio_data.get("portfolio_name", "Unknown"),
            "exported_at": now(),
            "file_size_bytes": get_file_size(path),
            "metadata": {"task_id": self.request.id, "export_config": export_config},
        }
        progress(self, 100, "Completed successfully")
        return results
    except Exception as error:
        fail(self, "Portfolio data export", error)
        raise


def daily_report_for(
    portfolio: Dict[str, Any], archive: ReportArchive
) -> Dict[str, Any]:
    returns = load_portfolio_returns(portfolio["id"])
    summary = performance_summary(returns.to_numpy())
    var95, es95 = historical_var_es(returns.to_numpy(), 0.95)
    stats = summary["performance_summary"]
    template = ReportTemplate(
        "Daily Portfolio Report",
        description=f"Portfolio: {portfolio['name']}",
        author="RiskOptimizer",
    )
    template.add_section(
        "Performance",
        {"data_key": "performance", "options": {"show_index": False}},
        "table",
    )
    template.add_section(
        "Risk", {"data_key": "risk", "options": {"show_index": False}}, "table"
    )
    data = {
        "performance": metric_table(
            [
                ("Total Return", percent(stats["total_return"])),
                ("Annualized Return", percent(stats["annualized_return"])),
                ("Volatility", percent(stats["volatility"])),
                ("Sharpe Ratio", f"{stats['sharpe_ratio']:.2f}"),
                ("Max Drawdown", percent(stats["max_drawdown"])),
            ]
        ),
        "risk": metric_table(
            [("VaR (95%)", percent(var95)), ("ES (95%)", percent(es95))]
        ),
    }
    path = (
        output_directory()
        / f"daily_report_{portfolio['id']}_{safe_filename(portfolio['name'])}_{stamp()}.pdf"
    )
    render(template, data, path)
    archived = archive.archive_report(
        str(path),
        "daily",
        {"portfolio_id": portfolio["id"], "portfolio_name": portfolio["name"]},
    )
    return {"report_path": str(path), "archived_path": archived}


@celery_app.task(bind=True)
def generate_daily_reports(self) -> Dict[str, Any]:
    try:
        portfolios = list_portfolios()
        archive = ReportArchive()
        email_owners = os.getenv(
            "DAILY_REPORTS_EMAIL_OWNERS", "false"
        ).strip().lower() in {"1", "true", "yes"}
        delivery = EmailDelivery.from_environment() if email_owners else None
        generated: List[Dict[str, Any]] = []
        for portfolio in portfolios:
            entry: Dict[str, Any] = {
                "portfolio_id": portfolio["id"],
                "portfolio_name": portfolio["name"],
                "report_date": now(),
            }
            try:
                entry.update(daily_report_for(portfolio, archive))
                entry["status"] = "generated"
                if delivery is not None and portfolio.get("owner_email"):
                    try:
                        entry["emailed"] = bool(
                            delivery(entry["report_path"], [portfolio["owner_email"]])
                        )
                    except Exception as error:
                        entry["emailed"] = False
                        entry["email_error"] = str(error)
            except TaskValidationError as error:
                entry.update({"status": "skipped", "reason": str(error)})
            except Exception as error:
                logger.error(
                    "Daily report failed for portfolio %s: %s", portfolio["id"], error
                )
                entry.update({"status": "failed", "error": str(error)})
            generated.append(entry)
        return {
            "task_type": "daily_reports",
            "generated_at": now(),
            "portfolios_processed": len(portfolios),
            "generated": sum(1 for item in generated if item["status"] == "generated"),
            "skipped": sum(1 for item in generated if item["status"] == "skipped"),
            "failed": sum(1 for item in generated if item["status"] == "failed"),
            "reports": generated,
        }
    except Exception as error:
        logger.error("Daily report generation failed: %s", error)
        raise
