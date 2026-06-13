"""tracer bullet: tivker -> snapshot + headlines -> one Gemini call -> memo in terminal
Run with: uv run python -m finsight.tracer NVDA
Delibrately Ugly and synchornous
"""

import os
import sys
from datetime import date, timedelta
from pathlib import Path

import requests
import yfinance as yf
from dotenv import load_dotenv
from google import genai

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


def build_prompt(snapshot: dict, headlines: list[dict]) -> str:
    snapshot_lines = "\n".join(f" - {key}: {value}" for key, value in snapshot.items())
    headlines_lines = "\n".join(
        f"N{i}. [{item['source']}] {item['headline']}" for i, item in enumerate(headlines, start=1)
    )
    template = PROMPT_PATH.read_text()
    return template.format(snapshot=snapshot_lines, headlines=headlines_lines)


def generate_memo(prompt: str) -> str:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
    return response.text or "(empty response)"


def main() -> None:
    load_dotenv()
    ticker = sys.argv[1].upper() if len(sys.argv) > 1 else "NVDA"
    print(f"-> snapshot for {ticker} (yfinance, the slow flaky one)...", flush=True)
    snapshot = get_snapshot(ticker)
    print("-> headlines (finnhub)...", flush=True)
    headlines = get_headlines(ticker)
    print("-> one gemini call...", flush=True)
    memo = generate_memo(build_prompt(snapshot, headlines))
    print("\n" + "=" * 70 + "\n")
    print(memo)
    print("\n---\nEducational tool. Not investment advice.")


if __name__ == "__main__":
    main()
