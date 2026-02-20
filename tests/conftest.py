import os
from datetime import date
from typing import Optional
from unittest.mock import patch

import pytest

os.environ["DATABASE_URL"] = "sqlite://"

from slc_stock.providers import QuoteData, StockProvider, _registry, register  # noqa: E402


TRADING_DAYS = {
    date(2026, 2, 9),   # Monday
    date(2026, 2, 10),  # Tuesday
    date(2026, 2, 11),  # Wednesday
    date(2026, 2, 12),  # Thursday
    date(2026, 2, 13),  # Friday
    date(2026, 2, 17),  # Tuesday (Mon is President's Day)
    date(2026, 2, 18),  # Wednesday
    date(2026, 2, 19),  # Thursday
    date(2026, 2, 20),  # Friday
    date(2026, 11, 24), # Tuesday before Thanksgiving 2026
    date(2026, 11, 30), # Monday after Thanksgiving week
}

VALID_SYMBOLS = {"CSCO", "AAPL", "IBIT"}


class MockProvider(StockProvider):
    name = "mock"

    def validate_symbol(self, symbol: str) -> bool:
        return symbol.upper() in VALID_SYMBOLS

    def get_quote(self, symbol: str, day: date) -> Optional[QuoteData]:
        if symbol.upper() not in VALID_SYMBOLS:
            return None
        if day not in TRADING_DAYS:
            return None
        return QuoteData(
            symbol=symbol,
            date=day,
            open=100.0,
            high=105.0,
            low=99.0,
            close=103.0,
            volume=1000000.0,
            adjusted=True,
        )

    def get_history(self, symbol: str, start: date, end: date) -> list[QuoteData]:
        if symbol.upper() not in VALID_SYMBOLS:
            return []
        results = []
        for day in sorted(TRADING_DAYS):
            if start <= day <= end:
                results.append(
                    QuoteData(
                        symbol=symbol,
                        date=day,
                        open=100.0,
                        high=105.0,
                        low=99.0,
                        close=103.0,
                        volume=1000000.0,
                        adjusted=True,
                    )
                )
        return results


@pytest.fixture(autouse=True)
def mock_provider():
    """Replace all registered providers with MockProvider and reset DB for every test."""
    from slc_stock.db import engine
    from slc_stock.models import Base

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    original = dict(_registry)
    _registry.clear()
    _registry["mock"] = MockProvider

    with patch("slc_stock.config.DEFAULT_PROVIDER", "mock"):
        with patch("slc_stock.service.DEFAULT_PROVIDER", "mock"):
            yield

    _registry.clear()
    _registry.update(original)


@pytest.fixture()
def service():
    from slc_stock.service import QuoteService
    return QuoteService()


@pytest.fixture()
def app():
    import slc_stock.app as app_module
    app_module._svc = None
    application = app_module.create_app()
    application.config["TESTING"] = True
    yield application
    app_module._svc = None


@pytest.fixture()
def client(app):
    return app.test_client()
