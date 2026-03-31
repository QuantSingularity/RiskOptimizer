from typing import Any

import pandas as pd
from sklearn.preprocessing import MinMaxScaler


def preprocess_data(filepath: Any) -> Any:
    df = pd.read_csv(filepath)
    df = df.fillna(method="ffill")
    df["log_returns"] = np.log(df["close"] / df["close"].shift(1))
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(
        df[["open", "high", "low", "volume", "log_returns"]]
    )
    return pd.DataFrame(
        scaled_data,
        columns=["open_norm", "high_norm", "low_norm", "volume_norm", "log_returns"],
    )
