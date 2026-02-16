"""Data retrieval utilities for Polymarket Gamma and CLOB APIs."""

from __future__ import annotations

import random
import time
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import requests

from polymarket_bt import config


class APIError(RuntimeError):
    """Raised when an API call repeatedly fails."""


def _request_with_backoff(
    url: str,
    params: dict[str, Any] | None = None,
    max_retries: int = config.MAX_RETRIES,
) -> Any:
    """Perform GET requests with retries, exponential backoff, and jitter.

    Args:
        url: Endpoint URL.
        params: Query parameters.
        max_retries: Maximum number of attempts.

    Returns:
        Parsed JSON object.

    Raises:
        APIError: If all retries are exhausted.
    """
    for attempt in range(max_retries):
        try:
            response = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SEC)
            if response.status_code == 429:
                raise requests.HTTPError("429 rate limited", response=response)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            if attempt == max_retries - 1:
                raise APIError(f"Request failed for {url} after {max_retries} attempts") from exc
            sleep_for = min(config.BACKOFF_BASE_SEC * (2**attempt), config.BACKOFF_MAX_SEC)
            sleep_for += random.uniform(0, 0.3)
            time.sleep(sleep_for)
    raise APIError(f"Unreachable failure for {url}")


def _is_btc_5min_event(title: str) -> bool:
    lowered = title.lower()
    has_btc = ("bitcoin" in lowered) or ("btc" in lowered)
    has_5m = any(tag in lowered for tag in ("5 min", "5-minute", "5m"))
    return has_btc and has_5m


def discover_btc_5min_markets(limit: int = 100) -> list[dict[str, Any]]:
    """Discover Bitcoin 5-minute markets via the Gamma API.

    Args:
        limit: Pagination limit for each API request.

    Returns:
        List of market metadata dictionaries with condition/token IDs and timing.
    """
    discovered: list[dict[str, Any]] = []
    seen_condition_ids: set[str] = set()

    for keyword in config.DEFAULT_KEYWORDS:
        offset = 0
        while True:
            events = _request_with_backoff(
                f"{config.GAMMA_BASE_URL}/events",
                params={"limit": limit, "offset": offset, "search": keyword},
            )
            if not isinstance(events, list) or not events:
                break

            filtered_events = [e for e in events if _is_btc_5min_event(str(e.get("title", "")))]
            for event in filtered_events:
                slug = event.get("slug")
                if not slug:
                    continue

                m_offset = 0
                while True:
                    markets = _request_with_backoff(
                        f"{config.GAMMA_BASE_URL}/markets",
                        params={"event_slug": slug, "limit": limit, "offset": m_offset},
                    )
                    if not isinstance(markets, list) or not markets:
                        break

                    for market in markets:
                        clob_ids = market.get("clobTokenIds") or []
                        if isinstance(clob_ids, str):
                            cleaned = clob_ids.strip().strip("[]")
                            clob_ids = [x.strip().strip('"').strip("'") for x in cleaned.split(",") if x.strip()]
                        if len(clob_ids) < 2:
                            continue

                        condition_id = str(market.get("conditionId", "")).strip()
                        if not condition_id or condition_id in seen_condition_ids:
                            continue
                        seen_condition_ids.add(condition_id)

                        discovered.append(
                            {
                                "condition_id": condition_id,
                                "yes_token_id": str(clob_ids[0]),
                                "no_token_id": str(clob_ids[1]),
                                "question": market.get("question", ""),
                                "start": market.get("startDate") or event.get("startDate"),
                                "end": market.get("endDate") or event.get("endDate"),
                                "event_slug": slug,
                                "market_slug": market.get("slug", ""),
                            }
                        )

                    if len(markets) < limit:
                        break
                    m_offset += limit

            if len(events) < limit:
                break
            offset += limit

    return discovered


def fetch_price_history(
    token_id: str,
    start_ts: int,
    end_ts: int,
    fidelity: int = config.DEFAULT_FIDELITY_MINUTES,
) -> pd.DataFrame:
    """Fetch historical token prices from CLOB `/prices-history` endpoint.

    Args:
        token_id: Outcome token ID.
        start_ts: UTC unix start timestamp.
        end_ts: UTC unix end timestamp.
        fidelity: Resolution in minutes.

    Returns:
        DataFrame with columns `timestamp` (UTC datetime) and `price` (float).
    """
    payload = _request_with_backoff(
        f"{config.CLOB_BASE_URL}/prices-history",
        params={
            "market": token_id,
            "startTs": int(start_ts),
            "endTs": int(end_ts),
            "fidelity": int(fidelity),
        },
    )

    rows = payload if isinstance(payload, list) else payload.get("history", []) if isinstance(payload, dict) else []
    records: list[dict[str, Any]] = []
    for row in rows:
        ts = row.get("t")
        price = row.get("p")
        if ts is None or price is None:
            continue
        records.append(
            {
                "timestamp": datetime.fromtimestamp(float(ts), tz=timezone.utc),
                "price": float(price),
            }
        )

    return pd.DataFrame(records, columns=["timestamp", "price"]).sort_values("timestamp").reset_index(drop=True)


def fetch_current_price(token_id: str) -> float | None:
    """Fetch the current mid price for a token.

    Args:
        token_id: Outcome token ID.

    Returns:
        Mid-price value if available, else None.
    """
    payload = _request_with_backoff(f"{config.CLOB_BASE_URL}/price", params={"token_id": token_id})
    if isinstance(payload, dict):
        for key in ("price", "mid", "midPrice"):
            if key in payload and payload[key] is not None:
                return float(payload[key])
    return None


if __name__ == "__main__":
    print("Fetcher smoke test")
    markets = discover_btc_5min_markets(limit=25)
    print(f"Discovered markets: {len(markets)}")
    if markets:
        now = int(datetime.now(tz=timezone.utc).timestamp())
        start = now - 3600
        sample_df = fetch_price_history(markets[0]["yes_token_id"], start, now, fidelity=1)
        print(sample_df.head())
