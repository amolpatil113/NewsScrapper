from __future__ import annotations

import time
from typing import Any, Dict, List

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from mapper import aggregate_sector_sentiment, classify_sector
from scraper import fetch_headlines
from sentiment import score_headline


APP_TITLE = "FinRadar"

ACCENT_GREEN = "#00ff88"
ACCENT_RED = "#ff4466"
BACKGROUND = "#0a0a0f"
TEXT_MUTED = "rgba(255,255,255,0.7)"


def _rerun() -> None:
    # Streamlit has changed this API name across versions.
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


def _vader_label_color(label: str) -> str:
    if label == "Bullish":
        return ACCENT_GREEN
    if label == "Bearish":
        return ACCENT_RED
    return "rgba(255,255,255,0.45)"


@st.cache_data(show_spinner=False)
def load_enriched_articles(refresh_token: int, limit: int = 30) -> List[Dict[str, Any]]:
    articles = fetch_headlines(limit=limit)

    enriched: List[Dict[str, Any]] = []
    for a in articles:
        headline = a.get("headline") or ""
        sentiment = score_headline(headline)
        sector = classify_sector(headline)

        enriched.append(
            {
                **a,
                "sector": sector,
                "neg": sentiment["neg"],
                "neu": sentiment["neu"],
                "pos": sentiment["pos"],
                "compound": sentiment["compound"],
                "label": sentiment["label"],
            }
        )

    return enriched


def _maybe_auto_refresh(interval_s: int = 60) -> None:
    if not st.session_state.get("auto_refresh", False):
        return

    # First run: set the next refresh moment and return immediately.
    if st.session_state.get("next_refresh_ts") is None:
        st.session_state["next_refresh_ts"] = time.time() + interval_s
        return

    remaining = float(st.session_state["next_refresh_ts"]) - time.time()
    if remaining > 0:
        # Server-side waiting loop (as requested). This keeps data fresh,
        # but may occupy the Streamlit worker during the wait.
        time.sleep(remaining)

    st.session_state["refresh_token"] = st.session_state.get("refresh_token", 0) + 1
    st.session_state["next_refresh_ts"] = time.time() + interval_s
    _rerun()


st.set_page_config(page_title=APP_TITLE, layout="wide", initial_sidebar_state="expanded")

# ---- Theme / typography ----
st.markdown(
    """
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Space+Mono&family=Syne:wght@400;600&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="stApp"] {
        background-color: """ + BACKGROUND + """;
        color: white;
        font-family: "Syne", "Space Mono", monospace;
      }
      .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.04) !important;
        color: white !important;
      }
      .stSelectbox div[data-baseweb="select"] > div {
        border: 1px solid rgba(255,255,255,0.08);
      }
      .st-expander {
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 10px;
        padding: 0.4rem;
      }
      .finradar-accent {
        color: """ + ACCENT_GREEN + """;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- Session state defaults ----
if "refresh_token" not in st.session_state:
    st.session_state["refresh_token"] = 0
if "auto_refresh" not in st.session_state:
    st.session_state["auto_refresh"] = True
if "next_refresh_ts" not in st.session_state:
    st.session_state["next_refresh_ts"] = None
if "search_term" not in st.session_state:
    st.session_state["search_term"] = ""
if "sector_filter" not in st.session_state:
    st.session_state["sector_filter"] = "All"
if "sentiment_filter" not in st.session_state:
    st.session_state["sentiment_filter"] = "All"


# ---- Sidebar controls ----
with st.sidebar:
    st.title(APP_TITLE)
    st.caption("Indian financial news sentiment radar")

    st.session_state["auto_refresh"] = st.toggle(
        "Auto-refresh (60s)",
        value=bool(st.session_state.get("auto_refresh", True)),
        help="Refreshes the news scan every 60 seconds.",
    )

    st.divider()

    sector_options = ["All", "Banking", "Fintech", "IT & Tech", "Pharma", "Energy", "Auto"]
    st.session_state["sector_filter"] = st.selectbox(
        "Sector",
        options=sector_options,
        index=sector_options.index(st.session_state.get("sector_filter", "All"))
        if st.session_state.get("sector_filter", "All") in sector_options
        else 0,
    )

    sentiment_options = ["All", "Bullish", "Neutral", "Bearish"]
    st.session_state["sentiment_filter"] = st.selectbox(
        "Sentiment",
        options=sentiment_options,
        index=sentiment_options.index(st.session_state.get("sentiment_filter", "All"))
        if st.session_state.get("sentiment_filter", "All") in sentiment_options
        else 0,
    )

    st.divider()
    st.caption("Search filters headline text in real-time.")
    st.session_state["search_term"] = st.text_input(
        "Live search",
        value=st.session_state.get("search_term", ""),
        placeholder="Type: RBI, Infosys, Paytm...",
    )


limit = 30
enriched_articles = load_enriched_articles(st.session_state["refresh_token"], limit=limit)

search_term = (st.session_state.get("search_term") or "").strip().lower()
sector_filter = st.session_state.get("sector_filter", "All")
sentiment_filter = st.session_state.get("sentiment_filter", "All")


def _apply_filters(articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for a in articles:
        if search_term and search_term not in (a.get("headline") or "").lower():
            continue
        if sector_filter != "All" and a.get("sector") != sector_filter:
            continue
        if sentiment_filter != "All" and a.get("label") != sentiment_filter:
            continue
        out.append(a)
    return out


filtered_articles = _apply_filters(enriched_articles)

df = pd.DataFrame(filtered_articles)
if df.empty:
    df = pd.DataFrame(
        {
            "headline": [],
            "source": [],
            "url": [],
            "publishedAt": [],
            "sector": [],
            "neg": [],
            "neu": [],
            "pos": [],
            "compound": [],
            "label": [],
        }
    )


def _sentiment_counts(frame: pd.DataFrame) -> Dict[str, int]:
    if frame.empty or "label" not in frame.columns:
        return {"Bullish": 0, "Neutral": 0, "Bearish": 0}
    counts = frame["label"].value_counts().to_dict()
    return {
        "Bullish": int(counts.get("Bullish", 0)),
        "Neutral": int(counts.get("Neutral", 0)),
        "Bearish": int(counts.get("Bearish", 0)),
    }


counts = _sentiment_counts(df)
total_articles = int(len(df))

avg_compound = float(df["compound"].mean()) if not df.empty else 0.0
if avg_compound >= 0.05:
    market_mood = "Bullish"
elif avg_compound <= -0.05:
    market_mood = "Bearish"
else:
    market_mood = "Neutral"


# ---- Top summary metrics ----
left, right = st.columns([1.2, 0.8])

with left:
    st.subheader("Market Snapshot")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total articles", f"{total_articles}")
    c2.metric("Bullish", f"{counts['Bullish']}")
    c3.metric("Bearish", f"{counts['Bearish']}")
    c4.metric("Market mood", market_mood)

with right:
    st.subheader("Leaders (after filters)")
    if not df.empty:
        bullish_idx = int(df["compound"].idxmax())
        bearish_idx = int(df["compound"].idxmin())
        most_bullish = df.loc[bullish_idx]
        most_bearish = df.loc[bearish_idx]

        b1, b2 = st.columns(2)
        with b1:
            st.markdown(f"**Most Bullish**")
            st.markdown(
                f"<div style='font-size:14px; color:{ACCENT_GREEN}; font-weight:600; line-height:1.2'>"
                f"{most_bullish['label']} ({most_bullish['compound']:.3f})</div>",
                unsafe_allow_html=True,
            )
        with b2:
            st.markdown(f"**Most Bearish**")
            st.markdown(
                f"<div style='font-size:14px; color:{ACCENT_RED}; font-weight:600; line-height:1.2'>"
                f"{most_bearish['label']} ({most_bearish['compound']:.3f})</div>",
                unsafe_allow_html=True,
            )
    else:
        st.caption("No articles match current filters.")


st.divider()


# ---- Charts ----
charts_left, charts_right = st.columns([0.62, 0.38])

with charts_left:
    st.subheader("Sector Sentiment")
    sector_df = aggregate_sector_sentiment(df.to_dict("records")).sort_values("avg_compound")

    colors = []
    for v in sector_df["avg_compound"].tolist():
        if v > 0:
            colors.append(ACCENT_GREEN)
        elif v < 0:
            colors.append(ACCENT_RED)
        else:
            colors.append("rgba(255,255,255,0.35)")

    fig_bar = go.Figure(
        data=[
            go.Bar(
                x=sector_df["avg_compound"],
                y=sector_df["sector"],
                orientation="h",
                marker=dict(color=colors),
                hovertemplate="Sector=%{y}<br>Avg compound=%{x:.3f}<extra></extra>",
            )
        ]
    )
    fig_bar.update_layout(
        height=320,
        template="plotly_dark",
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,
        font=dict(color="white"),
        margin=dict(l=10, r=10, t=30, b=10),
        xaxis=dict(title="Average VADER compound"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

with charts_right:
    st.subheader("Sentiment Split")
    labels = ["Bullish", "Neutral", "Bearish"]
    values = [counts["Bullish"], counts["Neutral"], counts["Bearish"]]
    donut_colors = [_vader_label_color(l) for l in labels]

    fig_donut = go.Figure(
        data=[
            go.Pie(
                labels=labels,
                values=values,
                hole=0.62,
                marker=dict(colors=donut_colors),
                hovertemplate="%{label}<br>%{value} articles<extra></extra>",
            )
        ]
    )
    fig_donut.update_layout(
        template="plotly_dark",
        paper_bgcolor=BACKGROUND,
        plot_bgcolor=BACKGROUND,
        font=dict(color="white"),
        margin=dict(l=10, r=10, t=30, b=10),
        showlegend=False,
    )
    st.plotly_chart(fig_donut, use_container_width=True)


st.subheader("Score Distribution")
hist_height = 320
if not df.empty:
    fig_hist = go.Figure(
        data=[
            go.Histogram(
                x=df["compound"],
                nbinsx=15,
                marker=dict(color="rgba(0,255,136,0.35)", line=dict(color="rgba(0,255,136,0.9)", width=1)),
                hovertemplate="Compound=%{x:.3f}<br>Count=%{y}<extra></extra>",
            )
        ]
    )
else:
    fig_hist = go.Figure()

fig_hist.update_layout(
    height=hist_height,
    template="plotly_dark",
    paper_bgcolor=BACKGROUND,
    plot_bgcolor=BACKGROUND,
    font=dict(color="white"),
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis=dict(title="VADER compound score"),
)
st.plotly_chart(fig_hist, use_container_width=True)


# ---- Headline cards ----
st.divider()
st.subheader("Headlines")

if df.empty:
    st.caption("Try changing filters or disabling search.")
else:
    # Sort by compound descending so bullish comes first.
    df_sorted = df.sort_values("compound", ascending=False)

    for _, row in df_sorted.iterrows():
        headline = str(row["headline"])
        label = str(row["label"])
        color = _vader_label_color(label)

        with st.expander(
            f"{headline[:90]}{'...' if len(headline) > 90 else ''}",
            expanded=False,
        ):
            st.markdown(
                f"<div style='color:{color}; font-weight:700; margin-bottom:6px'>{label} "
                f"(compound: {float(row['compound']):.3f})</div>",
                unsafe_allow_html=True,
            )

            st.caption(f"Sector: {row['sector']}")
            st.caption(f"Source: {row.get('source', '')}".strip())

            url = row.get("url")
            if isinstance(url, str) and url.strip():
                st.markdown(f"[Open article]({url})")

            st.write(
                {
                    "neg": float(row["neg"]),
                    "neu": float(row["neu"]),
                    "pos": float(row["pos"]),
                    "compound": float(row["compound"]),
                }
            )


# ---- Auto refresh (at the very end) ----
_maybe_auto_refresh(interval_s=60)

