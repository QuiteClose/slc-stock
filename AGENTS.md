# slc-stock — Agent Context

Local stock quote API serving OHLCV data over HTTP, backed by SQLite with pluggable data providers. Designed for personal/local use — fetches from upstream providers on demand and caches everything locally.

## File Map

```
slc_stock/
  __init__.py
  __main__.py              # Entry point for `python -m slc_stock.cli`
  app.py                   # Flask app factory, all HTTP routes
  cli.py                   # Click CLI commands (prefetch, dump, load, etc.)
  config.py                # All configuration from env vars via python-dotenv
  db.py                    # SQLAlchemy engine, session factory, schema migration
  logging_config.py        # Centralized logging setup
  models.py                # SQLAlchemy Quote model (single table)
  service.py               # QuoteService — all business logic lives here
  providers/
    __init__.py             # StockProvider ABC, QuoteData, SymbolNotFoundError, registry
    yfinance_provider.py    # Yahoo Finance (no API key needed)
    alpha_vantage_provider.py  # Alpha Vantage (requires API key)
    polygon_provider.py     # Polygon.io (requires API key)

tests/
  conftest.py              # MockProvider, in-memory SQLite, fixtures
  test_service.py          # Unit tests for QuoteService
  test_api.py              # Integration tests for Flask routes
  test_cli.py              # CLI command tests
```

## Key Patterns

### Provider Abstraction

All data providers implement `StockProvider` (ABC in `providers/__init__.py`) with these methods:
- `get_quote(symbol, day)` → `Optional[QuoteData]`
- `get_history(symbol, start, end)` → `list[QuoteData]`
- `validate_symbol(symbol)` → `bool`
- `is_configured()` → `bool`

Providers register themselves via the `@register` decorator, which adds them to `_registry`. The registry is keyed by `provider.name` (e.g., `"yfinance"`, `"alpha_vantage"`, `"polygon"`).

Provider imports in `app.py` and `cli.py` trigger registration at startup. When adding a new provider, you must also add its import to both files.

### Cache-Through

`QuoteService.get_quote()` checks SQLite first. On cache miss:
1. Validates the symbol (rejects invalid symbols before any DB writes)
2. Fetches from the configured provider
3. Stores the result in SQLite
4. Returns the data

### Market-Closed Fallback

When a requested date returns no data (weekend, holiday), the service walks backward up to 7 calendar days to find the most recent trading day. The response includes both `date` (actual trading day) and `requested_date` (what was asked for).

### Background Prefetch

On the first successful quote for a symbol (fewer than 30 rows in DB), a daemon thread downloads `PREFETCH_YEARS` of history. In-flight prefetches are tracked in `QuoteService._prefetch_in_flight` (a `set` of `(symbol, provider)` tuples) to avoid duplicate work. The `/stock/info` endpoint exposes this set for debugging.

### Rate-Limit Retry

Alpha Vantage and Polygon providers wrap API calls with retry-on-rate-limit logic (exponential backoff: 15s, 30s, 60s). Alpha Vantage signals rate limits via a `"Note"` key in JSON; Polygon returns HTTP 429.

## Data Model

Single `quotes` table:

| Column | Type | Notes |
|---|---|---|
| id | Integer | PK, auto-increment |
| symbol | String | Indexed, always uppercase |
| date | Date | Indexed |
| open, high, low, close | Float | |
| volume | Float | |
| adjusted | Boolean | True = split/dividend adjusted |
| provider | String | Which source supplied this row |
| fetched_at | DateTime | When stored |

Unique constraint: `(symbol, date, provider)` — each provider's data stored independently.

## Configuration

All in `config.py`, loaded from environment / `.env`:
- `DATABASE_URL` — SQLAlchemy URL (default: `sqlite:///instance/quotes.db`)
- `DEFAULT_PROVIDER` — used on cache miss (default: `yfinance`)
- `PREFETCH_YEARS` — background prefetch window (default: `3`)
- `ALPHA_VANTAGE_API_KEY`, `POLYGON_API_KEY` — provider credentials

## Conventions

- **Symbols are uppercased at the service boundary** — `QuoteService` calls `.upper()` on every symbol before any DB or provider interaction.
- **Invalid symbols never reach the database** — `validate_symbol()` is called before any writes. On failure, `SymbolNotFoundError` is raised and the Flask layer returns 400.
- **Provider implementations are self-contained** — each file in `providers/` handles its own API calls, response parsing, and rate-limit retry. They return normalized `QuoteData` objects.
- **Tests use MockProvider** — `conftest.py` replaces all registered providers with a `MockProvider` that has a fixed set of trading days. Tests never hit real APIs. The DB is reset between tests.
- **Logging uses `logging.getLogger(__name__)`** — every module gets its own logger under the `slc_stock` namespace.

## Adding a New Provider

1. Create `slc_stock/providers/new_provider.py`
2. Subclass `StockProvider`, set `name = "new_provider"`
3. Implement `get_quote`, `get_history`, `validate_symbol`, and optionally `is_configured`
4. Decorate the class with `@register`
5. Add `import slc_stock.providers.new_provider` to both `app.py` and `cli.py`
6. Add any required config (API keys) to `config.py` and `.env.example`

## Running

```bash
# API server
python -m slc_stock.app

# CLI
python -m slc_stock.cli --help

# Tests
python -m pytest tests/ -v
```
