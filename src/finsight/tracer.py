"""tracer bullet: tivker -> snapshot + headlines -> one Gemini call -> memo in terminal
Run with: uv run python -m finsight.tracer NVDA
Delibrately Ugly and synchornous
"""

import os
from datetime import date, timedelta
from pathlib import Path

import requests
import yfinance as yf
from dotenv import load_dotenv

PROMPT_PATH = Path(__file__).resolve().parents[2] / "prompts" / "tracer_memo_v1.md"


def get_snapshot(ticker: str) -> dict:
    """One yfinance call. Every field optional on purpose: missing data must not crash"""
    info = yf.Ticker(ticker).info
    return {
        "ticker": ticker,
        "name": info.get("shortName", ticker),
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "currency": info.get("currency", "USD"),
        "market_cap": info.get("marketCap"),
        "trailing_pe": info.get("trailingPE"),
        "fifty_two_week_high": info.get("fiftyTwoWeekHigh"),
        "fifty_two_week_low": info.get("fiftyTwoWeekLow"),
        "sector": info.get("sector"),
    }


def get_headlines(ticker: str, n: int = 5) -> list[dict]:
    to_day = date.today()
    from_day = to_day - timedelta(days=7)
    resp = requests.get(
        "https://finnhub.io/api/v1/company-news",
        params={
            "symbol": ticker,
            "from": from_day.isoformat(),
            "to": to_day.isoformat(),
            "token": os.environ["FINNHUB_API_KEY"],
        },
        timeout=15,
    )

    resp.raise_for_status()
    return [
        {"headline": item["headline"], "source": item["source"], "url": item["url"]}
        for item in resp.json()[:n]
    ]


if __name__ == "__main__":
    # Temporary smoke test
    load_dotenv()
    print(get_snapshot("NVDA"))
    print(get_headlines("NVDA"))
