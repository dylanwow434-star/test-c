"""SQLite cache layer for market metadata and historical prices."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import timezone
from typing import Iterator

import pandas as pd

from polymarket_bt import config


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(config.DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure_tables() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS markets (
                condition_id TEXT PRIMARY KEY,
                yes_token_id TEXT NOT NULL,
                no_token_id TEXT NOT NULL,
                question TEXT,
                start TEXT,
                end TEXT,
                event_slug TEXT,
                market_slug TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                token_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                PRIMARY KEY (token_id, timestamp)
            )
            """
        )


def save_markets(markets: list[dict]) -> None:
    """Persist discovered market metadata.

    Args:
        markets: Market metadata dictionaries.
    """
    _ensure_tables()
    with _connect() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO markets
            (condition_id, yes_token_id, no_token_id, question, start, end, event_slug, market_slug)
            VALUES (:condition_id, :yes_token_id, :no_token_id, :question, :start, :end, :event_slug, :market_slug)
            """,
            markets,
        )


def get_cached_history(token_id: str, start_ts: int, end_ts: int) -> pd.DataFrame | None:
    """Load cached history for a token and time range.

    Args:
        token_id: Outcome token ID.
        start_ts: Unix start timestamp.
        end_ts: Unix end timestamp.

    Returns:
        DataFrame if cache has records, else None.
    """
    _ensure_tables()
    start_iso = pd.to_datetime(start_ts, unit="s", utc=True).isoformat()
    end_iso = pd.to_datetime(end_ts, unit="s", utc=True).isoformat()

    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT timestamp, price
            FROM price_history
            WHERE token_id = ? AND timestamp >= ? AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (token_id, start_iso, end_iso),
        ).fetchall()

    if not rows:
        return None

    df = pd.DataFrame(rows, columns=["timestamp", "price"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df["price"] = df["price"].astype(float)
    return df


def save_history(token_id: str, df: pd.DataFrame) -> None:
    """Persist token price history rows.

    Args:
        token_id: Outcome token ID.
        df: DataFrame with columns `timestamp` and `price`.
    """
    _ensure_tables()
    if df.empty:
        return

    rows = [
        (
            token_id,
            pd.Timestamp(ts).tz_convert(timezone.utc).isoformat(),
            float(price),
        )
        for ts, price in zip(df["timestamp"], df["price"])
    ]

    with _connect() as conn:
        conn.executemany(
            """
            INSERT OR REPLACE INTO price_history (token_id, timestamp, price)
            VALUES (?, ?, ?)
            """,
            rows,
        )


if __name__ == "__main__":
    print("Store smoke test")
    sample = [
        {
            "condition_id": "c1",
            "yes_token_id": "y1",
            "no_token_id": "n1",
            "question": "test",
            "start": "2025-01-01T00:00:00Z",
            "end": "2025-01-01T00:05:00Z",
            "event_slug": "event",
            "market_slug": "market",
        }
    ]
    save_markets(sample)
    df = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(["2025-01-01T00:01:00Z", "2025-01-01T00:02:00Z"], utc=True),
            "price": [0.5, 0.52],
        }
    )
    save_history("y1", df)
    out = get_cached_history("y1", 1735689600, 1735689900)
    print(out)
