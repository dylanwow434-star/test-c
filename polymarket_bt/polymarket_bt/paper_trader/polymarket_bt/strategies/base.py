"""Strategy interfaces and shared signal structure."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from polymarket_bt.backtester.portfolio import Portfolio


@dataclass
class Signal:
    """Trading instruction emitted by a strategy."""

    token_id: str
    side: str
    qty: float


class Strategy(ABC):
    """Abstract base class for trading strategies."""

    @abstractmethod
    def on_bar(self, bar: dict[str, Any], portfolio: "Portfolio") -> list[Signal]:
        """Generate trading signals from the latest bar.

        Args:
            bar: Bar payload including timestamp, prices, and market metadata.
            portfolio: Current portfolio state.

        Returns:
            A list of trading signals to execute.
        """


if __name__ == "__main__":
    print("Base strategy smoke test: import successful")
