"""Paper order manager for simulated fills at mid price."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pandas as pd

from polymarket_bt.backtester.portfolio import Portfolio
from polymarket_bt.strategies.base import Signal


@dataclass
class PaperOrder:
    """Single simulated paper order entry."""

    timestamp: datetime
    token_id: str
    side: str
    price: float
    qty: float
    fill_status: str


class OrderManager:
    """Handles in-memory paper orders and updates portfolio fills."""

    def __init__(self, portfolio: Portfolio) -> None:
        self.portfolio = portfolio
        self.pending_orders: list[PaperOrder] = []
        self.filled_orders: list[PaperOrder] = []

    def execute_signal(self, signal: Signal, mid_price: float) -> PaperOrder:
        """Execute a signal at current mid-price.

        Args:
            signal: Signal to execute.
            mid_price: Mid-market fill price.

        Returns:
            Recorded paper order.
        """
        ts = datetime.now(tz=timezone.utc)
        order = PaperOrder(ts, signal.token_id, signal.side, float(mid_price), signal.qty, "pending")
        self.pending_orders.append(order)

        filled = False
        if signal.side == "buy":
            filled = self.portfolio.buy(signal.token_id, mid_price, signal.qty, timestamp=ts)
        elif signal.side == "sell":
            filled = self.portfolio.sell(signal.token_id, mid_price, signal.qty, timestamp=ts)

        order.fill_status = "filled" if filled else "rejected"
        self.pending_orders.remove(order)
        self.filled_orders.append(order)
        return order

    def order_log(self) -> pd.DataFrame:
        """Return DataFrame of all processed paper orders."""
        if not self.filled_orders:
            return pd.DataFrame(columns=["timestamp", "token_id", "side", "price", "qty", "fill_status"])
        return pd.DataFrame([o.__dict__ for o in self.filled_orders]).sort_values("timestamp").reset_index(drop=True)


if __name__ == "__main__":
    print("Order manager smoke test")
    from polymarket_bt.strategies.base import Signal

    pm = Portfolio(initial_cash=10)
    om = OrderManager(pm)
    print(om.execute_signal(Signal("yes", "buy", 5), 0.5))
    print(om.order_log())
