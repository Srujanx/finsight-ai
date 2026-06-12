""" " Preflight checks: prove every exteral dependency works before building on it"""

import os
import sys
from datetime import date, timedelta

import requests
import yfinance as yf
from dotenv import load_dotenv
from google import genai

""" Run with: uv run python -m finsight.preflight"""


def check_env_vars() -> bool:
    required = ["GEMINI_API_KEY", "FINNHUB_API_KEY"]
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        print(f"FAIL env: missing {', '.join(missing)} - is .env filled in?")
        return False
    print("PASS env: required keys present")
    return True


def check_yfinance() -> bool:
    # Broad excepts are delibrate here: pre-flight reports failures, it never crashes.
    try:
        info = yf.Ticker("AAPL").info
        price = info.get("currentPrice") or info.get("regularMarketPrice")
        if price is None:
            print("FAIL yfinance: response recieved but no price field")
            return False
        print(f"PASS yfinance: AAPL price = {price}")
        return True
    except Exception as exc:
        print(f"FAIL yfinance: {exc}")
        return False


def check_finnhub() -> bool:
    try:
        to_day = date.today()
        from_day = to_day - timedelta(days=7)
        resp = requests.get(
            "https://finnhub.io/api/v1/company-news",
            params={
                "symbol": "AAPL",
                "from": from_day.isoformat(),
                "to": to_day.isoformat(),
                "token": os.environ["FINNHUB_API_KEY"],
            },
            timeout=15,
        )
        resp.raise_for_status()
        print(f"PASS finnhub: {len(resp.json())} AAPL news item in last 7 days")
        return True
    except Exception as exc:
        print(f"FAIL finnhub: {exc}")
        return False


def check_gemini() -> bool:
    try:
        client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Reply with exactly: pong",
        )
        print(f"PASS gemini: model replied {resp.text!r}")
        return True
    except Exception as exc:
        print(f"FAIL gemini: {exc}")
        return False


def main() -> None:
    load_dotenv()
    results = [check_env_vars(), check_yfinance(), check_finnhub(), check_gemini()]
    if all(results):
        print("\nAll systems go.")
    sys.exit(0)
    print("\nAt least one dependency failed - fix it before starting tracer")
    sys.exit(1)


if __name__ == "__main__":
    main()
