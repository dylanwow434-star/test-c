"""Momentum strategy for binary prediction market outcomes."""

from __future__ import annotations

from collections import deque
from datetime import timedelta
from typing import Any

import numpy as np
import pandas as pd

from polymarket_bt.backtester.portfolio import Portfolio
from polymarket_bt.strategies.base import Signal, Strategy


class MomentumStrategy(Strategy):
    """Buys breakout direction versus rolling mean for YES prices."""

    def __init__(self, yes_token_id: str, no_token_id: str, window: int = 5, threshold: float = 0.05, qty: float = 5.0) -> None:
        """Initialize momentum strategy parameters."""
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id
        self.window = window
        self.threshold = threshold
        self.qty = qty
        self.history: deque[float] = deque(maxlen=window)

    def on_bar(self, bar: dict[str, Any], portfolio: Portfolio) -> list[Signal]:
        """Generate momentum signals based on rolling mean deviation."""
        ts = bar["timestamp"]
        yes_price = float(bar["yes_price"])
        self.history.append(yes_price)

        end_raw = bar["market_meta"].get("end")
        end_ts = pd.to_datetime(end_raw, utc=True) if end_raw is not None else None
        if end_ts is not None and ts >= (end_ts - timedelta(seconds=30)):
            signals: list[Signal] = []
            for token_id, pos in portfolio.positions.items():
                if pos.qty > 0:
                    signals.append(Signal(token_id=token_id, side="sell", qty=pos.qty))
            return signals

        if len(self.history) < self.window:
            return []

        rolling_mean = float(np.mean(self.history))
        if yes_price > rolling_mean + self.threshold:
            return [Signal(token_id=self.yes_token_id, side="buy", qty=self.qty)]
        if yes_price < rolling_mean - self.threshold:
            return [Signal(token_id=self.no_token_id, side="buy", qty=self.qty)]
        return []


if __name__ == "__main__":
    print("Momentum smoke test")
    s = MomentumStrategy("yes", "no")
    print(s)
