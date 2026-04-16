# FinRadar (Streamlit Financial News Sentiment Dashboard)

FinRadar scrapes Indian financial news headlines, scores sentiment using **VADER** (with a custom finance lexicon), maps results into **6 market sectors**, and displays a dark interactive dashboard.

## Tech Stack

- Streamlit
- vaderSentiment (VADER)
- Plotly
- pandas
- requests
- python-dotenv

## Prerequisites

1. Install Python (3.9+ recommended).
2. Create a NewsAPI account: https://newsapi.org/
3. Get your **API key** from NewsAPI.

## Project Files

- `app.py` - Streamlit UI + dashboard (charts, filters, metrics, auto-refresh toggle)
- `scraper.py` - News fetching (NewsAPI with fallback to hardcoded headlines)
- `sentiment.py` - VADER sentiment scoring + finance lexicon boosters
- `mapper.py` - Keyword-based sector classification + sector sentiment aggregation
- `requirements.txt` - Python dependencies

## Installation

Open PowerShell in this project folder and run:

```powershell
cd "C:\Users\DELL\OneDrive\Desktop\PROJECT SEM IV\NewsScrapper"
pip install -r requirements.txt
```

## NewsAPI Setup (.env)

Create a file named `.env` in the same folder as `app.py` and `scraper.py`.

Add:

```env
NEWSAPI_KEY=your_newsapi_key_here
```

Notes:
- The code expects the key variable name to be exactly `NEWSAPI_KEY`.
- If the key is missing or the NewsAPI request fails, the app automatically falls back to a built-in set of realistic Indian financial headlines (so the dashboard still works).

## Run the App

```powershell
streamlit run app.py
```

After running, Streamlit will show a local URL (usually `http://localhost:8501`) in your terminal.

## API Behavior (What the scraper requests)

`scraper.py` uses NewsAPI **`/v2/top-headlines`** with:

- `country`: `in`
- `category`: `business`
- `language`: `en`
- `pageSize`: `100`
- `q`: a query built from the finance entities you specified (RBI, HDFC, Infosys, Paytm, Reliance, Nifty, Sensex, SBI, TCS, Zomato, PhonePe, SEBI, Bajaj Finance)

Then it performs lightweight client-side filtering so returned headlines include at least one of the required entity keywords.

