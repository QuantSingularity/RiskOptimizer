import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler

REQUIRED_COLUMNS = ["open", "high", "low", "close", "volume"]
FEATURE_COLUMNS = ["open", "high", "low", "volume", "log_returns"]
OUTPUT_COLUMNS = ["open_norm", "high_norm", "low_norm", "volume_norm", "log_returns"]


def preprocess_data(filepath: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df.columns = df.columns.str.strip().str.lower()
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    for column in REQUIRED_COLUMNS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df = df.replace([np.inf, -np.inf], np.nan).ffill()
    df = df.dropna(subset=REQUIRED_COLUMNS)
    df = df[df["close"] > 0].reset_index(drop=True)
    if len(df) < 3:
        raise ValueError("Not enough valid rows to preprocess")
    df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
    df = df.dropna(subset=["log_returns"])
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(df[FEATURE_COLUMNS])
    return pd.DataFrame(scaled, columns=OUTPUT_COLUMNS, index=df.index)
