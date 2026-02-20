# slc-stock

Local stock quote API backed by SQLite with multiple data providers.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # add API keys if using Alpha Vantage / Polygon

# Pre-fetch 3 years of history for a symbol
python -m slc_stock.cli prefetch CSCO

# Start the API server
python -m slc_stock.app
```

## API

| Endpoint | Description |
|---|---|
| `GET /stock/quote/<SYMBOL>/<YYYY-MM-DD>` | OHLCV for a single day |
| `GET /stock/quote/<SYMBOL>/<YYYY-MM-DD>?provider=all` | Compare across providers |
| `GET /stock/history/<SYMBOL>?years=3` | Stored daily history |
| `GET /health` | Liveness check |

## CLI

```bash
python -m slc_stock.cli prefetch CSCO --years 3 --provider yfinance
python -m slc_stock.cli prefetch-all CSCO --years 3
python -m slc_stock.cli providers
python -m slc_stock.cli compare CSCO 2025-10-11
```

## Providers

- **yfinance** — Yahoo Finance (no API key required)
- **alpha_vantage** — requires `ALPHA_VANTAGE_API_KEY` in `.env`
- **polygon** — requires `POLYGON_API_KEY` in `.env`
