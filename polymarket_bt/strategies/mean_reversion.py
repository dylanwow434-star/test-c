"""Mean-reversion strategy for YES/NO outcome probabilities."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pandas as pd

from polymarket_bt.backtester.portfolio import Portfolio
from polymarket_bt.strategies.base import Signal, Strategy


class MeanReversionStrategy(Strategy):
    """Trades against extreme YES probabilities expecting reversion."""

    def __init__(
        self,
        yes_token_id: str,
        no_token_id: str,
        overbought: float = 0.75,
        oversold: float = 0.25,
        mid_low: float = 0.45,
        mid_high: float = 0.55,
        qty: float = 5.0,
    ) -> None:
        """Initialize mean-reversion thresholds."""
        self.yes_token_id = yes_token_id
        self.no_token_id = no_token_id
        self.overbought = overbought
        self.oversold = oversold
        self.mid_low = mid_low
        self.mid_high = mid_high
        self.qty = qty

    def on_bar(self, bar: dict[str, Any], portfolio: Portfolio) -> list[Signal]:
        """Generate contrarian entry/exit signals from YES price extremes."""
        ts = bar["timestamp"]
        yes_price = float(bar["yes_price"])
        signals: list[Signal] = []

        end_raw = bar["market_meta"].get("end")
        end_ts = pd.to_datetime(end_raw, utc=True) if end_raw is not None else None
        if end_ts is not None and ts >= (end_ts - timedelta(seconds=30)):
            for token_id, pos in portfolio.positions.items():
                if pos.qty > 0:
                    signals.append(Signal(token_id=token_id, side="sell", qty=pos.qty))
            return signals

        if self.mid_low <= yes_price <= self.mid_high:
            for token_id, pos in portfolio.positions.items():
                if pos.qty > 0:
                    signals.append(Signal(token_id=token_id, side="sell", qty=pos.qty))
            return signals

        if yes_price > self.overbought:
            signals.append(Signal(token_id=self.no_token_id, side="buy", qty=self.qty))
        elif yes_price < self.oversold:
            signals.append(Signal(token_id=self.yes_token_id, side="buy", qty=self.qty))
        return signals


if __name__ == "__main__":
    print("Mean-reversion smoke test")
    s = MeanReversionStrategy("yes", "no")
    print(s)
