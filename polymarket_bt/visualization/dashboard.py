"""Visualization helpers for backtest reporting."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from polymarket_bt.backtester.engine import BacktestResult


def _drawdown_series(equity_curve: pd.Series) -> pd.Series:
    peak = equity_curve.cummax()
    return (equity_curve - peak) / peak.replace(0, pd.NA) * 100.0


def render_backtest_report(result: BacktestResult, output_dir: str) -> None:
    """Render and save backtest charts and print performance table.

    Args:
        result: Backtest output containing equity curve, trades, and metrics.
        output_dir: Directory where PNG images are saved.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    eq_df = result.equity_curve.rename("equity").reset_index().rename(columns={"index": "timestamp"})
    eq_fig = px.line(eq_df, x="timestamp", y="equity", title="Equity Curve")
    eq_fig.write_image(str(out / "equity_curve.png"))

    drawdown = _drawdown_series(result.equity_curve)
    dd_df = drawdown.rename("drawdown_pct").reset_index().rename(columns={"index": "timestamp"})
    dd_fig = px.line(dd_df, x="timestamp", y="drawdown_pct", title="Drawdown (%)")
    dd_fig.write_image(str(out / "drawdown.png"))

    trades = result.trade_log.copy()
    if not trades.empty:
        trade_fig = px.scatter(
            trades,
            x="timestamp",
            y="price",
            color="side",
            symbol="token_id",
            title="Trade Scatter",
        )
    else:
        trade_fig = go.Figure()
        trade_fig.update_layout(title="Trade Scatter (no trades)")
    trade_fig.write_image(str(out / "trade_scatter.png"))

    metrics = {k: v for k, v in result.metrics.items() if k != "equity_curve"}
    summary_df = pd.DataFrame(metrics.items(), columns=["Metric", "Value"])
    print("\nBacktest Performance Summary")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    print("Dashboard smoke test: module import successful")
