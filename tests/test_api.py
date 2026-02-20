class TestHealthEndpoint:
    def test_health(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.get_json()["status"] == "ok"


class TestQuoteEndpoint:
    def test_quote_with_date(self, client):
        resp = client.get("/stock/quote/CSCO/2026-02-13")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["symbol"] == "CSCO"
        assert data["date"] == "2026-02-13"
        assert "close" in data

    def test_quote_latest(self, client):
        resp = client.get("/stock/quote/CSCO")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["symbol"] == "CSCO"

    def test_quote_invalid_date(self, client):
        resp = client.get("/stock/quote/CSCO/not-a-date")
        assert resp.status_code == 400

    def test_quote_invalid_symbol(self, client):
        resp = client.get("/stock/quote/FAKESYMBOL/2026-02-13")
        assert resp.status_code == 400
        assert "not found" in resp.get_json()["error"].lower()

    def test_quote_fallback_on_holiday(self, client):
        resp = client.get("/stock/quote/CSCO/2026-02-16")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["date"] == "2026-02-13"
        assert data["requested_date"] == "2026-02-16"

    def test_quote_provider_all(self, client):
        resp = client.get("/stock/quote/CSCO/2026-02-13?provider=all")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "quotes" in data


class TestInfoEndpoint:
    def test_info_inventory_empty(self, client):
        resp = client.get("/stock/info")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["total_quotes"] == 0

    def test_info_symbol_not_cached(self, client):
        resp = client.get("/stock/info/ZZZZ")
        assert resp.status_code == 404

    def test_info_symbol_after_quote(self, client):
        client.get("/stock/quote/CSCO/2026-02-13")
        resp = client.get("/stock/info/CSCO")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["symbol"] == "CSCO"
        assert data["total_quotes"] >= 1


class TestHistoryEndpoint:
    def test_history(self, client):
        resp = client.get("/stock/history/CSCO?years=1")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["symbol"] == "CSCO"
        assert "quotes" in data
