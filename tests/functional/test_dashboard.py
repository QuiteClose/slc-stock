import re

from playwright.sync_api import Page, expect


def test_dashboard_loads(page: Page, server):
    page.goto(server.url("/"))
    expect(page).to_have_title(re.compile("slc-stock"))
    expect(page.locator(".nav-brand")).to_have_text("slc-stock")


def test_empty_dashboard_shows_no_data_message(page: Page, server):
    page.goto(server.url("/"))
    expect(page.locator(".symbols-section")).to_contain_text("No data cached yet")


def test_empty_dashboard_has_no_table_rows(page: Page, server):
    page.goto(server.url("/"))
    rows = page.locator(".symbols-section tbody tr")
    expect(rows).to_have_count(0)


def test_cache_status_panel_loads(page: Page, server):
    page.goto(server.url("/"))
    status = page.locator(".status-section")
    expect(status).to_contain_text("System Status")
    expect(status).to_contain_text("Total Symbols")
    expect(status).to_contain_text("Total Quotes")


def test_search_returns_results(page: Page, server):
    page.goto(server.url("/"))
    page.fill(".search-form input", "CSCO")
    page.wait_for_selector(".search-result", timeout=5000)
    expect(page.locator(".search-result")).to_contain_text("CSCO")


def test_search_result_has_link_to_symbol(page: Page, server):
    page.goto(server.url("/"))
    page.fill(".search-form input", "CSCO")
    page.wait_for_selector(".search-result a", timeout=5000)
    link = page.locator(".search-result a")
    expect(link).to_have_attribute("href", "/symbol/CSCO")


def test_search_clearing_input_clears_results(page: Page, server):
    page.goto(server.url("/"))
    page.fill(".search-form input", "CSCO")
    page.wait_for_selector(".search-result", timeout=5000)
    page.fill(".search-form input", "")
    page.wait_for_timeout(500)
    results = page.locator("#search-results")
    expect(results).to_be_empty()


def test_seeded_dashboard_shows_symbols_table(page: Page, seeded_server):
    page.goto(seeded_server.url("/"))
    rows = page.locator(".symbols-section tbody tr")
    expect(rows).to_have_count(2)


def test_seeded_dashboard_shows_csco_row(page: Page, seeded_server):
    page.goto(seeded_server.url("/"))
    table = page.locator(".symbols-section table")
    expect(table).to_contain_text("CSCO")
    expect(table).to_contain_text("5")


def test_seeded_dashboard_shows_aapl_row(page: Page, seeded_server):
    page.goto(seeded_server.url("/"))
    table = page.locator(".symbols-section table")
    expect(table).to_contain_text("AAPL")


def test_seeded_dashboard_symbol_row_is_clickable(page: Page, seeded_server):
    page.goto(seeded_server.url("/"))
    csco_row = page.locator(".symbols-section tbody tr.clickable", has_text="CSCO")
    expect(csco_row).to_be_visible()


def test_seeded_cache_status_shows_symbols(page: Page, seeded_server):
    """Cache status should show at least the seeded symbols."""
    page.goto(seeded_server.url("/"))
    status = page.locator(".status-section")
    expect(status).to_contain_text("System Status")
    expect(status).to_contain_text("Total Symbols")


def test_dashboard_has_api_link(page: Page, server):
    """Dashboard should have an API link badge for cached symbols."""
    page.goto(server.url("/"))
    link = page.locator(".symbols-section .api-link")
    expect(link).to_be_visible()
    assert link.get_attribute("data-url") == "/api/v1/stock/info"
