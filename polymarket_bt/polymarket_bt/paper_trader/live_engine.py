"""Async paper-trading loop for live Polymarket BTC 5-minute markets."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import aiohttp
import pandas as pd

from polymarket_bt import config
from polymarket_bt.backtester.portfolio import Portfolio
from polymarket_bt.data.fetcher import discover_btc_5min_markets
from polymarket_bt.paper_trader.order_manager import OrderManager
from polymarket_bt.strategies.base import Strategy


class PaperTradingEngine:
    """Runs live polling for market data and simulates paper trades."""

    def __init__(self, strategy: Strategy, portfolio: Portfolio, poll_interval_sec: int = 10) -> None:
        self.strategy = strategy
        self.portfolio = portfolio
        self.poll_interval_sec = poll_interval_sec
        self.order_manager = OrderManager(portfolio)

    async def _fetch_price(self, session: aiohttp.ClientSession, token_id: str) -> float | None:
        url = f"{config.CLOB_BASE_URL}/price"
        params = {"token_id": token_id}
        for attempt in range(config.MAX_RETRIES):
            try:
                async with session.get(url, params=params, timeout=config.REQUEST_TIMEOUT_SEC) as resp:
                    if resp.status == 429:
                        await asyncio.sleep(min(config.BACKOFF_BASE_SEC * (2**attempt), config.BACKOFF_MAX_SEC))
                        continue
                    resp.raise_for_status()
                    payload = await resp.json()
                    for key in ("price", "mid", "midPrice"):
                        if key in payload and payload[key] is not None:
                            return float(payload[key])
                    return None
            except (aiohttp.ClientError, asyncio.TimeoutError):
                if attempt == config.MAX_RETRIES - 1:
                    return None
                await asyncio.sleep(min(config.BACKOFF_BASE_SEC * (2**attempt), config.BACKOFF_MAX_SEC))
        return None

    async def run(self) -> None:
        """Run continuous paper-trading cycle across active BTC 5-minute markets."""
        async with aiohttp.ClientSession() as session:
            while True:
                markets = discover_btc_5min_markets(limit=50)
                now = datetime.now(tz=timezone.utc)

                active = None
                for m in markets:
                    start = pd.to_datetime(m["start"], utc=True)
                    end = pd.to_datetime(m["end"], utc=True)
                    if start <= now <= end:
                        active = m
                        break

                if not active:
                    print("No active BTC 5-minute market found. Sleeping...")
                    await asyncio.sleep(self.poll_interval_sec)
                    continue

                yes_price = await self._fetch_price(session, active["yes_token_id"])
                no_price = await self._fetch_price(session, active["no_token_id"])
                if yes_price is None or no_price is None:
                    print("Price fetch failed; retrying")
                    await asyncio.sleep(self.poll_interval_sec)
                    continue

                bar: dict[str, Any] = {
                    "timestamp": now,
                    "yes_price": yes_price,
                    "no_price": no_price,
                    "market_meta": {**active, "end": pd.to_datetime(active["end"], utc=True)},
                }

                signals = self.strategy.on_bar(bar, self.portfolio)
                for signal in signals:
                    mid = yes_price if signal.token_id == active["yes_token_id"] else no_price
                    order = self.order_manager.execute_signal(signal, mid)
                    print(f"Order: {order}")

                if now >= pd.to_datetime(active["end"], utc=True):
                    resolved_yes = 1.0 if yes_price >= 0.5 else 0.0
                    self.portfolio.settle(active["yes_token_id"], resolved_yes, timestamp=now)
                    self.portfolio.settle(active["no_token_id"], 1.0 - resolved_yes, timestamp=now)
                    print("Market settled")

                print(f"Equity: {self.portfolio.equity():.2f}")
                await asyncio.sleep(self.poll_interval_sec)


if __name__ == "__main__":
    print("Live engine smoke test: import successful")
