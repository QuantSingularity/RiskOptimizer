import numpy as np
import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def preprocess_data(filepath: str) -> pd.DataFrame:
    """
    Loads and preprocesses OHLCV data from a CSV file.

    Normalises column names to lowercase so the function works with both
    'Close'/'close' style CSV files.

    Args:
        filepath: Path to the CSV file.

    Returns:
        DataFrame with normalised, scaled features.
    """
    df = pd.read_csv(filepath)
    # FIX: normalise column names to lowercase so we handle both 'Close' and 'close'
    df.columns = df.columns.str.lower()
    df = df.ffill()
    df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
    # Drop the first row which has NaN log_returns after the shift
    df = df.dropna(subset=["log_returns"])
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(
        df[["open", "high", "low", "volume", "log_returns"]]
    )
    return pd.DataFrame(
        scaled_data,
        columns=["open_norm", "high_norm", "low_norm", "volume_norm", "log_returns"],
    )
