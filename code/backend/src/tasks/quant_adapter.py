import logging
import re
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Mapping, Sequence, Tuple

import numpy as np
import pandas as pd
from src.services.quant_ml_bridge import ensure_quant_ml
from src.tasks.celery_app import TaskError, TaskValidationError

ensure_quant_ml()

import settings as quant_settings
from risk.common import as_frame, weight_vector

logger = logging.getLogger(__name__)

MAX_ROWS = 5000
MAX_ASSETS = 50
FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")


@contextmanager
def translate_errors() -> Iterator[None]:
    try:
        yield
    except TaskError:
        raise
    except (ValueError, KeyError, TypeError) as error:
        raise TaskValidationError(str(error)) from error
    except ArithmeticError as error:
        raise TaskError(str(error)) from error


def returns_frame(
    data: Mapping[str, Any], key: str, names_key: str = "asset_names"
) -> pd.DataFrame:
    if key not in data:
        raise TaskValidationError(f"Missing required field: {key}")
    frame = as_frame(data[key], min_rows=30)
    names = data.get(names_key)
    if names is not None:
        if not isinstance(names, (list, tuple)) or len(names) != frame.shape[1]:
            raise TaskValidationError(f"{names_key} must list one name per column")
        frame.columns = [str(name) for name in names]
    if len(frame) > MAX_ROWS or frame.shape[1] > MAX_ASSETS:
        raise TaskValidationError(
            f"Returns exceed {MAX_ROWS} rows or {MAX_ASSETS} assets"
        )
    return frame


def portfolio_inputs(
    portfolio_data: Mapping[str, Any],
) -> Tuple[pd.DataFrame, np.ndarray]:
    frame = returns_frame(portfolio_data, "historical_returns")
    if "weights" not in portfolio_data:
        raise TaskValidationError("Missing required field: weights")
    return frame, weight_vector(portfolio_data["weights"], list(frame.columns))


def safe_filename(name: Any, fallback: str = "report") -> str:
    cleaned = FILENAME_PATTERN.sub("_", str(name)).strip("_")[:60]
    return cleaned or fallback


def output_directory() -> Path:
    directory = quant_settings.report_dir() / "generated"
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def portfolio_returns_from_records(
    allocations: Sequence[Tuple[str, float]],
    prices: Mapping[str, Sequence[Tuple[Any, float]]],
) -> pd.Series:
    weights = {
        symbol: float(percentage)
        for symbol, percentage in allocations
        if float(percentage) > 0
    }
    if not weights:
        raise TaskValidationError("Portfolio has no allocations")
    series = {}
    for symbol in weights:
        rows = prices.get(symbol)
        if not rows:
            raise TaskValidationError(f"No market data for {symbol}")
        frame = pd.Series(
            {pd.Timestamp(date): float(close) for date, close in rows}
        ).sort_index()
        series[symbol] = frame[frame > 0]
    table = pd.concat(series, axis=1, join="inner").dropna()
    if len(table) < 30:
        raise TaskValidationError(
            "Fewer than 30 overlapping price observations are available"
        )
    vector = np.array([weights[c] for c in table.columns], dtype=float)
    vector = vector / vector.sum()
    return pd.Series(
        table.pct_change().dropna().to_numpy() @ vector,
        index=table.index[1:],
        name="portfolio",
    )


def load_portfolio_returns(portfolio_id: int) -> pd.Series:
    from src.infrastructure.database.models import Allocation, MarketData
    from src.infrastructure.database.session import get_db_session

    with get_db_session() as session:
        allocations = [
            (row.asset_symbol, float(row.percentage))
            for row in session.query(Allocation)
            .filter(Allocation.portfolio_id == portfolio_id)
            .all()
        ]
        if not allocations:
            raise TaskValidationError(f"Portfolio {portfolio_id} has no allocations")
        prices: Dict[str, List[Tuple[Any, float]]] = {}
        for symbol, _ in allocations:
            rows = (
                session.query(MarketData.date, MarketData.close_price)
                .filter(MarketData.symbol == symbol)
                .order_by(MarketData.date)
                .all()
            )
            prices[symbol] = [(row[0], float(row[1])) for row in rows]
    return portfolio_returns_from_records(allocations, prices)


def list_portfolios() -> List[Dict[str, Any]]:
    from src.infrastructure.database.models import Portfolio, User
    from src.infrastructure.database.session import get_db_session

    with get_db_session() as session:
        rows = (
            session.query(Portfolio, User.email)
            .join(User, User.id == Portfolio.user_id)
            .all()
        )
        return [
            {
                "id": row.Portfolio.id,
                "name": row.Portfolio.name,
                "owner_email": row.email,
            }
            for row in rows
        ]
