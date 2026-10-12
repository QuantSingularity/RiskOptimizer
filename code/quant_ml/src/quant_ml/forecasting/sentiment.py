import logging
import math
import threading
from typing import Any, Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)

MAX_SENTIMENT_TEXTS = 500

MAX_TEXT_LENGTH = 2000

FINANCE_LEXICON = {
    "hike": -1.5,
    "hikes": -1.5,
    "recall": -2.0,
    "recalls": -2.0,
    "surge": 2.0,
    "surges": 2.0,
    "surged": 2.0,
    "rally": 1.8,
    "rallies": 1.8,
    "plunge": -2.5,
    "plunges": -2.5,
    "plunged": -2.5,
    "slump": -2.0,
    "slumps": -2.0,
    "crash": -3.0,
    "selloff": -2.0,
    "jitters": -1.5,
    "bullish": 2.0,
    "bearish": -2.0,
    "upgrade": 1.8,
    "upgraded": 1.8,
    "downgrade": -1.8,
    "downgraded": -1.8,
    "outperform": 1.8,
    "underperform": -1.8,
    "bankruptcy": -3.0,
    "layoffs": -1.8,
    "default": -2.2,
}

_analyzer: Optional[Any] = None

_analyzer_lock = threading.Lock()


class AnalyticsUnavailableError(RuntimeError):
    pass


def build_sentiment_analyzer() -> Any:
    try:
        import nltk
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
    except ImportError as error:
        raise AnalyticsUnavailableError("nltk is not installed") from error
    try:
        nltk.data.find("sentiment/vader_lexicon.zip")
    except LookupError:
        if not nltk.download("vader_lexicon", quiet=True):
            raise AnalyticsUnavailableError(
                "VADER lexicon could not be downloaded"
            ) from None
    try:
        analyzer = SentimentIntensityAnalyzer()
    except LookupError as error:
        raise AnalyticsUnavailableError("VADER lexicon is unavailable") from error
    analyzer.lexicon.update(FINANCE_LEXICON)
    return analyzer


def get_sentiment_analyzer() -> Any:
    global _analyzer
    if _analyzer is None:
        with _analyzer_lock:
            if _analyzer is None:
                _analyzer = build_sentiment_analyzer()
    return _analyzer


def analyze_sentiment(
    text_list: List[str],
    positive_threshold: float = 0.05,
    negative_threshold: float = -0.05,
) -> pd.DataFrame:
    if not isinstance(text_list, list) or not all(
        isinstance(element, str) for element in text_list
    ):
        raise TypeError("Input 'text_list' must be a list of strings.")
    if not negative_threshold < positive_threshold:
        raise ValueError("negative_threshold must be lower than positive_threshold")
    analyzer = get_sentiment_analyzer()
    rows = []
    for text in text_list:
        compound = float(analyzer.polarity_scores(text)["compound"])
        if compound >= positive_threshold:
            label = "Positive"
        elif compound <= negative_threshold:
            label = "Negative"
        else:
            label = "Neutral"
        rows.append({"text": text, "compound": compound, "sentiment": label})
    return pd.DataFrame(rows, columns=["text", "compound", "sentiment"])


def summarize_sentiment(frame: pd.DataFrame) -> Dict[str, Any]:
    counts = frame["sentiment"].value_counts()
    mean_compound = float(frame["compound"].mean()) if len(frame) else 0.0
    if not math.isfinite(mean_compound):
        mean_compound = 0.0
    if mean_compound >= 0.05:
        overall = "Positive"
    elif mean_compound <= -0.05:
        overall = "Negative"
    else:
        overall = "Neutral"
    return {
        "count": int(len(frame)),
        "mean_compound": mean_compound,
        "positive": int(counts.get("Positive", 0)),
        "neutral": int(counts.get("Neutral", 0)),
        "negative": int(counts.get("Negative", 0)),
        "overall": overall,
    }
