from __future__ import annotations

from typing import Dict, List

import pandas as pd


SECTORS_IN_ORDER = ["Banking", "Fintech", "IT & Tech", "Pharma", "Energy", "Auto"]


# Keyword matching is intentionally simple + deterministic.
# If a headline matches multiple sectors, we pick the first one in SECTORS_IN_ORDER.
_SECTOR_KEYWORDS: Dict[str, List[str]] = {
    "Banking": [
        "rbi",
        "sbi",
        "hdfc",
        "hdfc bank",
        "nifty",
        "sensex",
        "sebi",
        "bank",
        "interest",
        "credit",
        "loan",
        "lending",
        "nbfc",
        "bajaj finance",
        "markets",
        "equities",
    ],
    "Fintech": [
        "paytm",
        "phonepe",
        "upi",
        "digital payments",
        "wallet",
        "fintech",
        "zomato",
        "payment",
        "payments",
        "transaction",
    ],
    "IT & Tech": [
        "infosys",
        "tcs",
        "wipro",
        "software",
        "cloud",
        "technology",
        "it services",
        "cyber",
        "tech stocks",
    ],
    "Pharma": [
        "pharma",
        "pharmaceutical",
        "drug",
        "sun pharma",
        "cipla",
        "dr reddy",
        "drreddy",
        "divis labs",
        "biocon",
    ],
    "Energy": [
        "reliance",
        "oil",
        "gas",
        "refining",
        "petroleum",
        "crude",
        "energy",
        "adani energy",
    ],
    "Auto": [
        "auto",
        "automobile",
        "tata motors",
        "maruti",
        "mahindra",
        "bajaj auto",
        "vehicle",
        "vehicles",
    ],
}


def classify_sector(headline: str) -> str:
    text = (headline or "").lower()
    for sector in SECTORS_IN_ORDER:
        for kw in _SECTOR_KEYWORDS.get(sector, []):
            if kw in text:
                return sector
    # If nothing matches, keep it deterministic (send to Banking).
    return "Banking"


def aggregate_sector_sentiment(articles: List[dict]) -> pd.DataFrame:
    """
    Compute average compound sentiment per sector.
    Articles are expected to have at least: `sector`, `compound`.
    """
    df = pd.DataFrame(articles or [])
    if df.empty:
        return pd.DataFrame({"sector": SECTORS_IN_ORDER, "avg_compound": [0.0] * len(SECTORS_IN_ORDER)})

    if "sector" not in df.columns:
        df["sector"] = df.get("headline", "").apply(classify_sector)
    if "compound" not in df.columns:
        df["compound"] = 0.0

    # Ensure only known sectors are aggregated (keeps ordering deterministic).
    df = df[df["sector"].isin(SECTORS_IN_ORDER)]

    grouped = df.groupby("sector", as_index=False)["compound"].mean().rename(columns={"compound": "avg_compound"})

    out = pd.DataFrame({"sector": SECTORS_IN_ORDER})
    out = out.merge(grouped, on="sector", how="left")
    out["avg_compound"] = out["avg_compound"].fillna(0.0)
    return out

