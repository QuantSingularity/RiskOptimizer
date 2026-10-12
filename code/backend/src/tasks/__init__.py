"""
Tasks package initialization
"""

from src.services.quant_ml_bridge import ensure_quant_ml

ensure_quant_ml()

from .celery_app import celery_app
from .maintenance_tasks import (
    cache_warmup,
    cleanup_expired_tasks,
    system_health_check,
    update_market_data,
)
from .portfolio_tasks import (
    analyze_portfolio_performance,
    optimize_portfolio,
    rebalance_portfolio,
    update_portfolio_data,
)
from .report_tasks import (
    export_portfolio_data,
    generate_portfolio_report,
    generate_risk_report,
)
from .risk_tasks import (
    calculate_portfolio_metrics,
    calculate_var_cvar,
    efficient_frontier_calculation,
    monte_carlo_simulation,
    stress_test_portfolio,
)

__all__ = [
    "celery_app",
    "monte_carlo_simulation",
    "calculate_var_cvar",
    "efficient_frontier_calculation",
    "stress_test_portfolio",
    "calculate_portfolio_metrics",
    "optimize_portfolio",
    "rebalance_portfolio",
    "analyze_portfolio_performance",
    "update_portfolio_data",
    "generate_portfolio_report",
    "generate_risk_report",
    "export_portfolio_data",
    "cleanup_expired_tasks",
    "update_market_data",
    "cache_warmup",
    "system_health_check",
]
