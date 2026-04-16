from __future__ import annotations

from typing import Dict

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer


# Finance-specific booster words to make VADER more responsive to financial
# language. Values tuned to move `compound` meaningfully.
_POSITIVE_BOOSTERS = {
    "surge": 4.0,
    "profit": 3.8,
    "rally": 3.7,
    "beats": 4.0,
}

_NEGATIVE_BOOSTERS = {
    "crash": -4.0,
    "fraud": -4.2,
    "loss": -3.9,
    "slump": -3.8,
    "warning": -3.7,
}


def _build_analyzer() -> SentimentIntensityAnalyzer:
    analyzer = SentimentIntensityAnalyzer()

    # Inject boosters into VADER's lexicon (valence dictionary).
    for word, score in {**_POSITIVE_BOOSTERS, **_NEGATIVE_BOOSTERS}.items():
        analyzer.lexicon[word] = float(score)

    return analyzer


_ANALYZER = _build_analyzer()


def score_headline(headline: str) -> Dict[str, float | str]:
    """
    Score a single headline and return:
    - neg / neu / pos / compound (from VADER)
    - label: Bullish (compound >= 0.05), Bearish (compound <= -0.05), else Neutral
    """
    text = (headline or "").strip()
    scores = _ANALYZER.polarity_scores(text)
    compound = float(scores.get("compound", 0.0))

    if compound >= 0.05:
        label = "Bullish"
    elif compound <= -0.05:
        label = "Bearish"
    else:
        label = "Neutral"

    return {
        "neg": float(scores.get("neg", 0.0)),
        "neu": float(scores.get("neu", 0.0)),
        "pos": float(scores.get("pos", 0.0)),
        "compound": compound,
        "label": label,
    }

