# test-c
# Polymarket BTC 5-Minute Backtesting + Paper Trading

## Overview

This project provides a Python framework for:

- Discovering Polymarket Bitcoin 5-minute prediction markets via Gamma API.
- Fetching historical and live prices via Polymarket CLOB API.
- Running strategy backtests with portfolio accounting and performance metrics.
- Running live paper trading with simulated fills at mid-price.
- Rendering visual reports (equity, drawdown, trades).

> **Data integrity rule:** all market data is fetched from real Polymarket public APIs. No synthetic price generation is used.

## Architecture

```text
polymarket_bt/
├── config.py
├── data/
│   ├── fetcher.py
│   └── store.py
├── backtester/
│   ├── engine.py
│   ├── portfolio.py
│   └── metrics.py
├── paper_trader/
│   ├── live_engine.py
│   └── order_manager.py
├── strategies/
│   ├── base.py
│   ├── momentum.py
│   └── mean_reversion.py
├── visualization/
│   └── dashboard.py
└── main.py
```

## Setup

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

## Usage

### Backtest Mode

```bash
python -m polymarket_bt.main backtest \
  --strategy momentum \
  --start 2025-01-01 \
  --end 2025-02-15 \
  --cash 1000 \
  --fee 0.02 \
  --param window=5 \
  --param threshold=0.05
```

### Paper Trading Mode

```bash
python -m polymarket_bt.main paper \
  --strategy mean_reversion \
  --cash 500 \
  --poll 10 \
  --param overbought=0.75 \
  --param oversold=0.25
```

## Notes

- All timestamps are handled in UTC.
- API calls include retry/backoff behavior for transient failures and rate limiting.
- SQLite cache database is automatically created at `polymarket_bt/polymarket_cache.sqlite3`.
- Plotly report PNG export requires `kaleido`.

## Smoke Tests

Each module includes a small `if __name__ == "__main__"` block for quick local validation.

Examples:

```bash
python -m polymarket_bt.config
python -m polymarket_bt.data.fetcher
python -m polymarket_bt.backtester.portfolio
```