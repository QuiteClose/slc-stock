class TestWebDashboard:
    def test_dashboard_loads(self, client):
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"slc-stock" in resp.data

    def test_dashboard_shows_cached_table(self, client):
        client.get("/api/v1/stock/quote/CSCO/2026-02-13")
        resp = client.get("/")
        assert resp.status_code == 200
        assert b"CSCO" in resp.data


class TestWebSymbolPage:
    def test_symbol_page_loads(self, client):
        resp = client.get("/symbol/CSCO")
        assert resp.status_code == 200
        assert b"CSCO" in resp.data

    def test_symbol_page_has_chart_canvas(self, client):
        resp = client.get("/symbol/CSCO")
        assert b"priceChart" in resp.data


class TestWebComparePage:
    def test_compare_page_loads(self, client):
        resp = client.get("/compare")
        assert resp.status_code == 200
        assert b"Compare" in resp.data


class TestHtmxPartials:
    def test_search_empty(self, client):
        resp = client.get("/ui/search?q=")
        assert resp.status_code == 200

    def test_search_known_symbol(self, client):
        client.get("/api/v1/stock/quote/CSCO/2026-02-13")
        resp = client.get("/ui/search?q=CSCO")
        assert resp.status_code == 200
        assert b"CSCO" in resp.data

    def test_cache_status(self, client):
        resp = client.get("/ui/cache-status")
        assert resp.status_code == 200
        assert b"System Status" in resp.data

    def test_quote_partial(self, client):
        resp = client.get("/ui/quote/CSCO/2026-02-13")
        assert resp.status_code == 200

    def test_chart_data_partial(self, client):
        resp = client.get("/ui/chart-data/CSCO?years=1")
        assert resp.status_code == 200
