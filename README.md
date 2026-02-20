# slc-stock

Local stock quote API and web interface backed by SQLite with pluggable data providers (yfinance, Alpha Vantage, Polygon.io). Serves OHLCV data over HTTP on localhost, with a CLI for bulk prefetch and database management.

## Prerequisites

- Python 3.11+
- (Optional) API keys for Alpha Vantage and/or Polygon.io

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env to add API keys if using Alpha Vantage or Polygon

# Start the server (API + web UI)
python -m slc_stock.app

# Or pre-fetch history first
python -m slc_stock.cli prefetch CSCO --years 3
```

The SQLite database is created automatically at `instance/quotes.db` on first run.

## Web Interface

Open `http://localhost:5000/` in a browser. The web interface provides:

- **Dashboard** (`/`) — search bar with instant results, cached symbols table, system status sidebar (auto-refreshes)
- **Symbol detail** (`/symbol/<SYMBOL>`) — price chart (Chart.js with 1M/3M/6M/1Y/3Y/All ranges), quote lookup by date, cache info panel, and a prefetch button
- **Compare** (`/compare`) — enter a symbol and date to see OHLCV from all providers side by side

The UI uses htmx for dynamic updates (no full page reloads) and Chart.js for price charts. Both are loaded from CDN with SRI integrity hashes.

## API Reference

All JSON endpoints live under `/api/v1/`. The server runs on `http://localhost:5000` by default.

### `GET /api/v1/stock/quote/<SYMBOL>`

Returns the latest available quote. If the market is closed, falls back to the most recent trading day.

```bash
curl http://localhost:5000/api/v1/stock/quote/CSCO
```

```json
{
  "symbol": "CSCO",
  "date": "2026-02-20",
  "requested_date": "2026-02-20",
  "open": 64.12,
  "high": 64.89,
  "low": 63.95,
  "close": 64.50,
  "volume": 18200000,
  "adjusted": true,
  "provider": "yfinance",
  "fetched_at": "2026-02-20T18:13:29"
}
```

### `GET /api/v1/stock/quote/<SYMBOL>/<YYYY-MM-DD>`

Returns OHLCV for a specific day. If the market was closed that day (weekend, holiday), the response automatically falls back to the most recent prior trading day. The `requested_date` field shows what was originally asked for; `date` shows what was actually returned.

```bash
curl http://localhost:5000/api/v1/stock/quote/CSCO/2026-02-16
```

```json
{
  "symbol": "CSCO",
  "date": "2026-02-13",
  "requested_date": "2026-02-16",
  "close": 64.50,
  "..."
}
```

Add `?provider=all` to compare across all cached providers:

```bash
curl http://localhost:5000/api/v1/stock/quote/CSCO/2025-10-10?provider=all
```

### `GET /api/v1/stock/history/<SYMBOL>?years=3`

Returns stored daily history from the database. Optional query params: `years` (default 3), `provider`.

```bash
curl http://localhost:5000/api/v1/stock/history/CSCO?years=1
```

### `POST /api/v1/stock/prefetch/<SYMBOL>`

Triggers a background prefetch of historical data. Returns immediately.

```bash
curl -X POST http://localhost:5000/api/v1/stock/prefetch/CSCO
```

```json
{"status": "started", "symbol": "CSCO"}
```

If already in progress: `{"status": "already_in_progress", "symbol": "CSCO"}`

### `GET /api/v1/stock/info`

Cache inventory -- shows all symbols in the database, quote counts, date ranges, provider configuration, and any background prefetch threads in flight. Useful for debugging.

```bash
curl http://localhost:5000/api/v1/stock/info
```

```json
{
  "total_quotes": 2310,
  "total_symbols": 3,
  "database_path": "/path/to/instance/quotes.db",
  "database_size_mb": 1.4,
  "providers_configured": {"yfinance": true, "alpha_vantage": false, "polygon": false},
  "prefetch_in_flight": [],
  "symbols": [
    {"symbol": "CSCO", "total_quotes": 754, "providers": ["yfinance"], "earliest": "2023-02-20", "latest": "2026-02-20", "..."}
  ]
}
```

### `GET /api/v1/stock/info/<SYMBOL>`

Per-symbol detail with provider-by-provider breakdown.

```bash
curl http://localhost:5000/api/v1/stock/info/CSCO
```

### `GET /api/v1/health`

```bash
curl http://localhost:5000/api/v1/health
```

## CLI Reference

All commands: `python -m slc_stock.cli --help`

### prefetch

Download historical quotes into the local database.

```bash
python -m slc_stock.cli prefetch CSCO --years 3 --provider yfinance
```

### prefetch-all

Download history from every configured provider.

```bash
python -m slc_stock.cli prefetch-all CSCO --years 3
```

### providers

List available data providers and whether they're configured.

```bash
python -m slc_stock.cli providers
```

### compare

Show data from all providers for a given symbol and date side-by-side.

```bash
python -m slc_stock.cli compare CSCO 2025-10-10
```

### dump

Export the entire database to a JSON file (backup).

```bash
python -m slc_stock.cli dump --output backup.json
```

### load

Import quotes from a JSON file (restore).

```bash
python -m slc_stock.cli load backup.json
```

## Providers

| Provider | API Key Required | Rate Limit (free) | Prices |
|---|---|---|---|
| **yfinance** | No | Unofficial, generous | Adjusted |
| **alpha_vantage** | Yes (`ALPHA_VANTAGE_API_KEY`) | 5 calls/min | Adjusted (daily adjusted endpoint) |
| **polygon** | Yes (`POLYGON_API_KEY`) | 5 calls/min | Adjusted |

Rate-limited providers retry automatically with exponential backoff (15s, 30s, 60s) before failing.

## Configuration

All settings are loaded from environment variables (`.env` file supported via python-dotenv).

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///instance/quotes.db` | SQLAlchemy database URL |
| `DEFAULT_PROVIDER` | `yfinance` | Provider used on cache miss |
| `PREFETCH_YEARS` | `3` | Years of history for background prefetch |
| `ALPHA_VANTAGE_API_KEY` | (empty) | Alpha Vantage API key |
| `POLYGON_API_KEY` | (empty) | Polygon.io API key |

## Architecture

- **Cache-through pattern**: API checks SQLite first; on cache miss, fetches from the configured provider, stores the result, and returns it. Pre-fetching via CLI seeds the DB so API responses are fast.
- **Market-closed fallback**: When a requested date has no data (weekend, holiday), the service walks back up to 7 days to find the most recent trading day.
- **Background prefetch**: The first time a new symbol is queried, a daemon thread automatically downloads its full history (configurable via `PREFETCH_YEARS`). Subsequent queries are served from cache.
- **Multi-provider storage**: Each provider's data is stored independently (unique constraint on symbol+date+provider), enabling cross-reference and comparison.
- **Symbol validation**: Invalid symbols are rejected before any database writes occur (HTTP 400).
- **API versioning**: All JSON endpoints are namespaced under `/api/v1/` via a Flask Blueprint. The web UI lives on root paths (`/`, `/symbol/<sym>`, `/compare`).
- **Web UI**: Server-rendered Jinja2 templates with htmx for partial page updates and Chart.js for interactive price charts. No build step required.

## Running Tests

```bash
python -m pytest tests/ -v
```

Tests use a mock provider and in-memory SQLite -- they never hit real APIs.
