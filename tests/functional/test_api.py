"""Functional tests for the REST API (no browser needed)."""


def test_health(seeded_server):
    status, body = seeded_server.api_get("/api/v1/health")
    assert status == 200
    assert body == {"status": "ok"}


def test_quote_with_known_date(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/quote/CSCO/2026-02-13")
    assert status == 200
    assert body["symbol"] == "CSCO"
    assert body["date"] == "2026-02-13"
    assert body["close"] == 61.20
    assert "open" in body
    assert "high" in body
    assert "low" in body
    assert "volume" in body
    assert "provider" in body


def test_quote_includes_adjusted_field(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/quote/CSCO/2026-02-13")
    assert status == 200
    assert "adjusted" in body
    assert body["adjusted"] is True


def test_quote_includes_requested_date(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/quote/CSCO/2026-02-13")
    assert status == 200
    assert "requested_date" in body
    assert body["requested_date"] == "2026-02-13"


def test_quote_latest(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/quote/CSCO")
    assert status == 200
    assert body["symbol"] == "CSCO"
    assert "close" in body


def test_quote_invalid_date(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/quote/CSCO/not-a-date")
    assert status == 400
    assert "error" in body


def test_quote_no_data_for_old_date(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/quote/CSCO/2020-01-01")
    assert status in (200, 404)


def test_quote_provider_all(seeded_server):
    status, body = seeded_server.api_get(
        "/api/v1/stock/quote/CSCO/2026-02-13?provider=all"
    )
    assert status == 200
    assert "quotes" in body
    assert isinstance(body["quotes"], list)
    assert len(body["quotes"]) >= 1
    assert body["quotes"][0]["provider"] == "yfinance"


def test_info_inventory(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/info")
    assert status == 200
    assert body["total_symbols"] >= 2
    assert body["total_quotes"] >= 6
    assert "symbols" in body
    symbols = {s["symbol"] for s in body["symbols"]}
    assert "CSCO" in symbols
    assert "AAPL" in symbols


def test_info_inventory_structure(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/info")
    assert status == 200
    assert "database_path" in body
    assert "database_size_mb" in body
    assert "providers_configured" in body
    assert "prefetch_in_flight" in body


def test_info_symbol_detail(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/info/CSCO")
    assert status == 200
    assert body["symbol"] == "CSCO"
    assert body["total_quotes"] >= 5
    assert "providers" in body
    assert "yfinance" in body["providers"]
    assert "date_range" in body
    assert body["date_range"]["earliest"] <= "2026-02-09"
    assert body["date_range"]["latest"] >= "2026-02-13"
    assert "by_provider" in body


def test_info_symbol_not_cached(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/info/NOPE")
    assert status == 404
    assert "error" in body


def test_info_symbol_case_insensitive(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/info/csco")
    assert status == 200
    assert body["symbol"] == "CSCO"


def test_history(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/history/CSCO")
    assert status == 200
    assert body["symbol"] == "CSCO"
    assert body["count"] >= 5
    assert isinstance(body["quotes"], list)
    assert len(body["quotes"]) >= 5


def test_history_empty_symbol(seeded_server):
    status, body = seeded_server.api_get("/api/v1/stock/history/NOPE")
    assert status == 200
    assert body["count"] == 0
    assert body["quotes"] == []


def test_prefetch_start(seeded_server):
    status, body = seeded_server.api_post("/api/v1/stock/prefetch/CSCO")
    assert status == 200
    assert body["symbol"] == "CSCO"
    assert body["status"] in ("started", "already_in_progress")
