"""CLI entry point for backtesting and paper trading."""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from polymarket_bt import config
from polymarket_bt.backtester.engine import BacktestEngine
from polymarket_bt.backtester.portfolio import Portfolio
from polymarket_bt.data.fetcher import discover_btc_5min_markets, fetch_price_history
from polymarket_bt.data.store import get_cached_history, save_history, save_markets
from polymarket_bt.paper_trader.live_engine import PaperTradingEngine
from polymarket_bt.strategies.mean_reversion import MeanReversionStrategy
from polymarket_bt.strategies.momentum import MomentumStrategy
from polymarket_bt.visualization.dashboard import render_backtest_report


def _parse_params(raw: list[str] | None) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for item in raw or []:
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        try:
            parsed: Any = int(value)
        except ValueError:
            try:
                parsed = float(value)
            except ValueError:
                parsed = value
        params[key] = parsed
    return params


def _select_strategy(name: str, yes_token_id: str, no_token_id: str, params: dict[str, Any]):
    if name == "momentum":
        return MomentumStrategy(yes_token_id=yes_token_id, no_token_id=no_token_id, **params)
    if name == "mean_reversion":
        return MeanReversionStrategy(yes_token_id=yes_token_id, no_token_id=no_token_id, **params)
    raise ValueError(f"Unsupported strategy: {name}")


def _pick_market(markets: list[dict[str, Any]], start: datetime, end: datetime) -> dict[str, Any]:
    for market in markets:
        m_start = pd.to_datetime(market["start"], utc=True)
        if start <= m_start <= end:
            market["start"] = m_start
            market["end"] = pd.to_datetime(market["end"], utc=True)
            return market
    raise RuntimeError("No BTC 5-minute market found in selected date range")


def run_backtest(args: argparse.Namespace) -> None:
    """Execute backtest command using real Polymarket historical data."""
    start = datetime.fromisoformat(args.start).replace(tzinfo=timezone.utc)
    end = datetime.fromisoformat(args.end).replace(tzinfo=timezone.utc)
    start_ts = int(start.timestamp())
    end_ts = int(end.timestamp())

    markets = discover_btc_5min_markets()
    save_markets(markets)
    market = _pick_market(markets, start, end)

    yes_df = get_cached_history(market["yes_token_id"], start_ts, end_ts)
    if yes_df is None or yes_df.empty:
        yes_df = fetch_price_history(market["yes_token_id"], start_ts, end_ts, fidelity=1)
        save_history(market["yes_token_id"], yes_df)

    no_df = get_cached_history(market["no_token_id"], start_ts, end_ts)
    if no_df is None or no_df.empty:
        no_df = fetch_price_history(market["no_token_id"], start_ts, end_ts, fidelity=1)
        save_history(market["no_token_id"], no_df)

    data = (
        yes_df.rename(columns={"price": "yes_price"})
        .merge(no_df.rename(columns={"price": "no_price"}), on="timestamp", how="inner")
        .dropna()
        .sort_values("timestamp")
    )

    strategy = _select_strategy(args.strategy, market["yes_token_id"], market["no_token_id"], _parse_params(args.param))
    portfolio = Portfolio(initial_cash=args.cash, fee_rate=args.fee)
    engine = BacktestEngine(strategy, portfolio, data, market)
    result = engine.run()

    print("Backtest completed")
    for key, val in result.metrics.items():
        if key != "equity_curve":
            print(f"{key}: {val}")

    render_backtest_report(result, str(config.REPORTS_DIR))


def run_paper(args: argparse.Namespace) -> None:
    """Execute live paper trading command."""
    markets = discover_btc_5min_markets()
    if not markets:
        raise RuntimeError("No BTC 5-minute markets discovered")
    market = markets[0]

    strategy = _select_strategy(args.strategy, market["yes_token_id"], market["no_token_id"], _parse_params(args.param))
    portfolio = Portfolio(initial_cash=args.cash, fee_rate=args.fee)
    engine = PaperTradingEngine(strategy, portfolio, poll_interval_sec=args.poll)
    asyncio.run(engine.run())


def build_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser."""
    parser = argparse.ArgumentParser(description="Polymarket BTC 5-minute backtester and paper trader")
    sub = parser.add_subparsers(dest="mode", required=True)

    b = sub.add_parser("backtest", help="Run historical backtest")
    b.add_argument("--strategy", choices=["momentum", "mean_reversion"], required=True)
    b.add_argument("--start", required=True, help="YYYY-MM-DD")
    b.add_argument("--end", required=True, help="YYYY-MM-DD")
    b.add_argument("--cash", type=float, default=config.DEFAULT_INITIAL_CASH)
    b.add_argument("--fee", type=float, default=config.DEFAULT_FEE_RATE)
    b.add_argument("--param", action="append", default=[])
    b.set_defaults(func=run_backtest)

    p = sub.add_parser("paper", help="Run live paper trading loop")
    p.add_argument("--strategy", choices=["momentum", "mean_reversion"], required=True)
    p.add_argument("--cash", type=float, default=config.DEFAULT_INITIAL_CASH)
    p.add_argument("--fee", type=float, default=config.DEFAULT_FEE_RATE)
    p.add_argument("--poll", type=int, default=config.DEFAULT_POLL_INTERVAL_SEC)
    p.add_argument("--param", action="append", default=[])
    p.set_defaults(func=run_paper)

    return parser


def main() -> None:
    """CLI program entry point."""
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()