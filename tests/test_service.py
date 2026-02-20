from datetime import date

import pytest

from slc_stock.providers import SymbolNotFoundError


class TestGetQuote:
    def test_normal_trading_day(self, service):
        result = service.get_quote("CSCO", date(2026, 2, 13))
        assert result is not None
        assert result["symbol"] == "CSCO"
        assert result["date"] == "2026-02-13"
        assert result["close"] == 103.0
        assert result["requested_date"] == "2026-02-13"

    def test_cache_hit(self, service):
        """Second call should come from cache."""
        r1 = service.get_quote("CSCO", date(2026, 2, 13))
        r2 = service.get_quote("CSCO", date(2026, 2, 13))
        assert r1["date"] == r2["date"]
        assert r1["close"] == r2["close"]

    def test_weekend_falls_back_to_friday(self, service):
        """Saturday 2026-02-14 should fall back to Friday 2026-02-13."""
        result = service.get_quote("CSCO", date(2026, 2, 14))
        assert result is not None
        assert result["date"] == "2026-02-13"
        assert result["requested_date"] == "2026-02-14"

    def test_sunday_falls_back_to_friday(self, service):
        """Sunday 2026-02-15 should fall back to Friday 2026-02-13."""
        result = service.get_quote("CSCO", date(2026, 2, 15))
        assert result is not None
        assert result["date"] == "2026-02-13"
        assert result["requested_date"] == "2026-02-15"

    def test_presidents_day_falls_back_to_friday(self, service):
        """President's Day 2026-02-16 (Monday) should fall back to Friday 2026-02-13."""
        result = service.get_quote("CSCO", date(2026, 2, 16))
        assert result is not None
        assert result["date"] == "2026-02-13"
        assert result["requested_date"] == "2026-02-16"

    def test_thanksgiving_multi_day_gap(self, service):
        """
        Thanksgiving 2026 is Nov 26 (Thu). Markets closed Thu+Fri.
        Requesting Nov 27 (Fri) should fall back to Nov 24 (Tue).
        """
        result = service.get_quote("CSCO", date(2026, 11, 27))
        assert result is not None
        assert result["date"] == "2026-11-24"
        assert result["requested_date"] == "2026-11-27"


class TestInvalidSymbol:
    def test_invalid_symbol_raises_400(self, service):
        with pytest.raises(SymbolNotFoundError):
            service.get_quote("FAKESYMBOL", date(2026, 2, 13))

    def test_invalid_symbol_no_db_writes(self, service):
        with pytest.raises(SymbolNotFoundError):
            service.get_quote("FAKESYMBOL", date(2026, 2, 13))
        info = service.get_symbol_info("FAKESYMBOL")
        assert info is None


class TestLatestQuote:
    def test_get_latest_quote(self, service):
        result = service.get_latest_quote("CSCO")
        assert result is not None
        assert result["symbol"] == "CSCO"


class TestPrefetch:
    def test_prefetch_stores_rows(self, service):
        count = service.prefetch(
            "CSCO", date(2026, 2, 9), date(2026, 2, 20), provider_name="mock"
        )
        assert count > 0
        history = service.get_history(
            "CSCO", date(2026, 2, 9), date(2026, 2, 20), provider_name="mock"
        )
        assert len(history) == count


class TestSymbolInfo:
    def test_info_after_prefetch(self, service):
        service.prefetch("CSCO", date(2026, 2, 9), date(2026, 2, 20), provider_name="mock")
        info = service.get_symbol_info("CSCO")
        assert info is not None
        assert info["symbol"] == "CSCO"
        assert info["total_quotes"] > 0
        assert "mock" in info["providers"]

    def test_info_unknown_symbol(self, service):
        info = service.get_symbol_info("ZZZZ")
        assert info is None


class TestCacheInfo:
    def test_cache_info_empty(self, service):
        info = service.get_cache_info()
        assert info["total_quotes"] == 0
        assert info["total_symbols"] == 0

    def test_cache_info_after_data(self, service):
        service.prefetch("CSCO", date(2026, 2, 9), date(2026, 2, 20), provider_name="mock")
        info = service.get_cache_info()
        assert info["total_quotes"] > 0
        assert info["total_symbols"] == 1
        assert len(info["symbols"]) == 1
        assert info["symbols"][0]["symbol"] == "CSCO"


class TestDumpLoad:
    def test_round_trip(self, service):
        service.prefetch("CSCO", date(2026, 2, 9), date(2026, 2, 20), provider_name="mock")
        records = service.dump_database()
        assert len(records) > 0

        from slc_stock.service import QuoteService
        svc2 = QuoteService()
        loaded = svc2.load_database(records)
        assert loaded == len(records)
