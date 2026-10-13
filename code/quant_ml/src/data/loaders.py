import os
import re
from pathlib import Path
from typing import Iterable, List, Optional

import pandas as pd
import settings

FILE_SUFFIX = "_historical.csv"
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9._-]{1,15}$")
MIN_OVERLAP_ROWS = 30


def resolve_data_dir(data_dir: Optional[os.PathLike] = None) -> Path:
    if data_dir:
        return Path(data_dir)
    return settings.data_dir()


def normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not SYMBOL_PATTERN.match(symbol.strip()):
        raise ValueError(f"Invalid symbol: {symbol!r}")
    return symbol.strip().upper().replace("-", "_").replace(".", "_")


def available_symbols(data_dir: Optional[os.PathLike] = None) -> List[str]:
    directory = resolve_data_dir(data_dir)
    if not directory.is_dir():
        return []
    return sorted(
        path.name[: -len(FILE_SUFFIX)] for path in directory.glob(f"*{FILE_SUFFIX}")
    )


def find_symbol_file(
    symbol: str, data_dir: Optional[os.PathLike] = None
) -> Optional[Path]:
    directory = resolve_data_dir(data_dir)
    stem = normalize_symbol(symbol)
    for candidate in (stem, f"{stem}_USD"):
        path = directory / f"{candidate}{FILE_SUFFIX}"
        if path.is_file():
            return path
    return None


def load_close_series(symbol: str, data_dir: Optional[os.PathLike] = None) -> pd.Series:
    path = find_symbol_file(symbol, data_dir)
    if path is None:
        raise FileNotFoundError(f"No historical data available for symbol {symbol}")
    frame = pd.read_csv(path, index_col=0, parse_dates=True)
    frame.columns = [str(column).strip().lower() for column in frame.columns]
    if "close" not in frame.columns:
        raise ValueError(f"Data file for {symbol} has no Close column")
    series = pd.to_numeric(frame["close"], errors="coerce")
    series = series[~series.index.duplicated(keep="last")].sort_index().dropna()
    series = series[series > 0]
    series.name = symbol.strip().upper()
    return series


def load_close_prices(
    symbols: Iterable[str],
    data_dir: Optional[os.PathLike] = None,
    minimum_symbols: int = 2,
) -> pd.DataFrame:
    unique: List[str] = []
    for symbol in symbols:
        label = symbol.strip().upper() if isinstance(symbol, str) else symbol
        if label not in unique:
            unique.append(label)
    if len(unique) < minimum_symbols:
        raise ValueError(f"At least {minimum_symbols} distinct symbols are required")
    frame = pd.concat(
        [load_close_series(symbol, data_dir) for symbol in unique],
        axis=1,
        join="inner",
    )
    if len(frame) < MIN_OVERLAP_ROWS:
        raise ValueError(
            f"Selected symbols share only {len(frame)} common trading days; "
            f"at least {MIN_OVERLAP_ROWS} are required"
        )
    return frame
