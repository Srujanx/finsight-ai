"""SQLite memo cache. Key = (ticker, date). 24h-ish TTL via the date in the key.

Bible §5.2: repeat lookups cost zero quota. §7.4: idempotency.
"""

import json
import sqlite3
from datetime import date
from pathlib import Path

from finsight.schemas.models import InvestmentMemo

_DB_PATH = Path(__file__).resolve().parents[2] / "finsight_cache.db"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS memos ("
        "  ticker TEXT NOT NULL,"
        "  as_of TEXT NOT NULL,"
        "  memo_json TEXT NOT NULL,"
        "  PRIMARY KEY (ticker, as_of)"
        ")"
    )
    return conn


def get_cached_memo(ticker: str) -> InvestmentMemo | None:
    today = date.today().isoformat()
    with _conn() as conn:
        row = conn.execute(
            "SELECT memo_json FROM memos WHERE ticker = ? AND as_of = ?",
            (ticker, today),
        ).fetchone()
    if row is None:
        return None
    return InvestmentMemo.model_validate(json.loads(row[0]))


def save_memo(memo: InvestmentMemo) -> None:
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO memos (ticker, as_of, memo_json) VALUES (?, ?, ?)",
            (memo.ticker, memo.as_of, memo.model_dump_json()),
        )
