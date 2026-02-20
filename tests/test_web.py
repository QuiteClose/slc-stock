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

    def test_symbol_page_rejects_xss(self, client):
        """Issue 1: XSS in symbol should return 400."""
        resp = client.get("/symbol/CSCO%22onmouseover%3D")
        assert resp.status_code == 400


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

    def test_quote_partial_rejects_xss_symbol(self, client):
        """Issue 1: XSS in quote partial symbol."""
        resp = client.get("/ui/quote/<script>/2026-02-13")
        assert resp.status_code == 400

    def test_chart_data_partial(self, client):
        resp = client.get("/ui/chart-data/CSCO?days=365")
        assert resp.status_code == 200

    def test_chart_data_negative_days(self, client):
        """Issue 5: negative days should return 400."""
        resp = client.get("/ui/chart-data/CSCO?days=-1")
        assert resp.status_code == 400

    def test_chart_data_excessive_days(self, client):
        """Issue 5: excessively large days should be clamped or rejected."""
        resp = client.get("/ui/chart-data/CSCO?days=999999")
        assert resp.status_code == 400


class TestHtmlEscaping:
    """Issue 2: error messages must not contain raw HTML."""

    def test_error_html_escaped_in_quote_partial(self, client):
        resp = client.get("/ui/quote/FAKE<b>SYM</b>/2026-02-13")
        assert b"<b>" not in resp.data

    def test_error_html_escaped_in_prefetch(self, client):
        resp = client.post("/ui/prefetch/FAKE<b>SYM</b>")
        assert b"<b>" not in resp.data
