"""Global configuration constants for the Polymarket backtesting project."""

from __future__ import annotations

from pathlib import Path

GAMMA_BASE_URL: str = "https://gamma-api.polymarket.com"
CLOB_BASE_URL: str = "https://clob.polymarket.com"

DEFAULT_INITIAL_CASH: float = 1000.0
DEFAULT_FEE_RATE: float = 0.02
DEFAULT_POLL_INTERVAL_SEC: int = 10
DEFAULT_FIDELITY_MINUTES: int = 1

REQUEST_TIMEOUT_SEC: int = 20
MAX_RETRIES: int = 5
BACKOFF_BASE_SEC: float = 0.75
BACKOFF_MAX_SEC: float = 12.0

DEFAULT_KEYWORDS: tuple[str, ...] = ("Bitcoin", "BTC", "5 min", "5-minute", "5m")

DB_PATH: Path = Path(__file__).resolve().parent / "polymarket_cache.sqlite3"
REPORTS_DIR: Path = Path(__file__).resolve().parent / "reports"


if __name__ == "__main__":
    print("Config smoke test")
    print(f"Gamma URL: {GAMMA_BASE_URL}")
    print(f"CLOB URL: {CLOB_BASE_URL}")
    print(f"DB path: {DB_PATH}")
