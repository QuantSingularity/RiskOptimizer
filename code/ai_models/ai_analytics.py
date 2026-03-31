import logging
import os
import warnings
from typing import Any

import nltk
import pandas as pd
from nltk.sentiment.vader import SentimentIntensityAnalyzer
from prophet import Prophet

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
warnings.filterwarnings("ignore")
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except nltk.downloader.DownloadError:
    nltk.download("vader_lexicon")
DATA_DIR = "data"


def load_price_data(ticker: str, data_dir: str = DATA_DIR) -> pd.DataFrame:
    """Loads historical 'Close' price data for a single ticker for Prophet."""
    file_name = f"{ticker.replace('-', '_')}_historical.csv"
    file_path = os.path.join(data_dir, file_name)
    try:
        df = pd.read_csv(file_path, index_col=0, parse_dates=True)
        df_prophet = df["Close"].reset_index()
        df_prophet.columns = ["ds", "y"]
        logging.info(f"Loaded {len(df_prophet)} rows for {ticker} for forecasting.")
        return df_prophet
    except FileNotFoundError:
        logging.error(
            f"Data file not found for {ticker} at {file_path}. Run data_ingestion.py first."
        )
        raise
    except Exception as e:
        logging.error(f"Error loading price data for {ticker}: {e}")
        raise


def prophet_forecast(df: pd.DataFrame, ticker: str, periods: int = 30) -> Any:
    """
    Trains a Prophet model and forecasts future price movements.
    :param df: DataFrame with 'ds' and 'y' columns.
    :param ticker: The stock ticker symbol for logging purposes.
    :param periods: The number of future days to forecast.
    """
    logging.info(
        f"--- Prophet Time-Series Forecasting for {ticker} ({periods} days) ---"
    )
    try:
        m = Prophet(daily_seasonality=True)
        m.fit(df)
        future = m.make_future_dataframe(periods=periods)
        forecast = m.predict(future)
        logging.info("Forecast columns: ds, yhat (forecast), yhat_lower, yhat_upper")
        logging.info(forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]].tail())
        return forecast
    except Exception as e:
        logging.error(f"An error occurred during Prophet forecasting: {e}")
        raise


def analyze_sentiment(
    text_list: list[str],
    positive_threshold: float = 0.05,
    negative_threshold: float = -0.05,
) -> pd.DataFrame:
    """
    Performs sentiment analysis on a list of text snippets using NLTK's VADER.
    :param text_list: A list of strings to analyze.
    :param positive_threshold: The threshold for classifying sentiment as positive.
    :param negative_threshold: The threshold for classifying sentiment as negative.
    """
    if not isinstance(text_list, list) or not all(
        (isinstance(elem, str) for elem in text_list)
    ):
        raise TypeError("Input 'text_list' must be a list of strings.")
    logging.info("--- Sentiment Analysis (VADER) ---")
    sia = SentimentIntensityAnalyzer()
    results = []
    for text in text_list:
        vs = sia.polarity_scores(text)
        if vs["compound"] >= positive_threshold:
            sentiment = "Positive"
        elif vs["compound"] <= negative_threshold:
            sentiment = "Negative"
        else:
            sentiment = "Neutral"
        results.append(
            {"text": text, "compound": vs["compound"], "sentiment": sentiment}
        )
    df_sentiment = pd.DataFrame(results)
    logging.info(df_sentiment[["text", "compound", "sentiment"]])
    return df_sentiment


def run_ai_analytics(ticker_to_forecast: str) -> Any:
    """Main function to run all AI analytics components."""
    try:
        df_prices = load_price_data(ticker_to_forecast)
        prophet_forecast(df_prices, ticker=ticker_to_forecast, periods=7)
        mock_news_headlines = [
            f"{ticker_to_forecast} stock hits all-time high on strong iPhone sales report.",
            "Federal Reserve signals interest rate hike, causing market jitters.",
            "Tesla announces massive recall due to software glitch.",
            "Bitcoin surges past $100,000 milestone in a historic rally.",
            f"Analyst gives a neutral rating on {ticker_to_forecast}'s Q4 earnings.",
        ]
        analyze_sentiment(mock_news_headlines)
    except FileNotFoundError as e:
        logging.error(f"Error: {e}")
        logging.error(
            "Please ensure the data ingestion script (data_ingestion.py) has been run successfully."
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred during AI analytics: {e}")


if __name__ == "__main__":
    TICKER_TO_FORECAST = "AAPL"
    run_ai_analytics(TICKER_TO_FORECAST)
