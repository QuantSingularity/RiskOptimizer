import argparse
import json
import logging
import os
from typing import Any, Dict, List, Optional

from forecasting.price import MODEL_CHOICES, forecast_prices
from forecasting.sentiment import analyze_sentiment, summarize_sentiment


def run_ai_analytics(
    ticker_to_forecast: str,
    headlines: Optional[List[str]] = None,
    periods: int = 7,
    data_dir: Optional[os.PathLike] = None,
    model: str = "auto",
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "forecast": forecast_prices(ticker_to_forecast, periods, data_dir, model),
        "sentiment": None,
    }
    if headlines:
        frame = analyze_sentiment(headlines)
        result["sentiment"] = {
            "summary": summarize_sentiment(frame),
            "items": frame.to_dict(orient="records"),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run price forecasting and sentiment analysis"
    )
    parser.add_argument("ticker")
    parser.add_argument("--periods", type=int, default=7)
    parser.add_argument("--model", default="auto", choices=MODEL_CHOICES)
    parser.add_argument("--headline", action="append", default=[])
    arguments = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    output = run_ai_analytics(
        arguments.ticker, arguments.headline, arguments.periods, model=arguments.model
    )
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
