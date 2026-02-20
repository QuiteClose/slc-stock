import re

from playwright.sync_api import Page, expect


def test_symbol_page_loads(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    expect(page).to_have_title(re.compile("CSCO"))
    expect(page.locator(".symbol-header h1")).to_have_text("CSCO")


def test_symbol_page_case_insensitive(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/csco"))
    expect(page).to_have_title(re.compile("CSCO"))


def test_latest_price_displayed(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    price = page.locator(".latest-price .price")
    expect(price).to_be_visible()
    expect(price).to_contain_text("$")


def test_latest_date_displayed(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    date_el = page.locator(".latest-price .date")
    expect(date_el).to_be_visible()


def test_chart_canvas_present(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    canvas = page.locator("#priceChart")
    expect(canvas).to_be_visible()


def test_chart_data_loads(page: Page, seeded_server):
    """After page load, htmx should fetch chart data into chart-data-holder."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.wait_for_selector("#chart-data-holder #chart-payload", state="attached", timeout=10000)
    payload = page.locator("#chart-payload")
    assert payload.get_attribute("data-labels") is not None


def test_chart_renders_with_seeded_data(page: Page, seeded_server):
    """Chart should render — chartInstance should be initialised by afterSwap."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.wait_for_function("typeof chartInstance !== 'undefined' && chartInstance !== null", timeout=10000)
    has_chart = page.evaluate("typeof chartInstance !== 'undefined' && chartInstance !== null")
    assert has_chart, "Expected chartInstance to be initialised after data loads"


def test_range_button_3y_is_active_by_default(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    active = page.locator(".range-buttons .btn-sm.active")
    expect(active).to_have_text("3Y")


def test_range_button_1y_sets_active(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.wait_for_timeout(1000)
    btn_1y = page.locator(".range-buttons .btn-sm", has_text="1Y")
    btn_1y.click()
    page.wait_for_timeout(1000)
    expect(btn_1y).to_have_class(re.compile("active"))


def test_range_button_1m_requests_valid_data(page: Page, seeded_server):
    """1M button should show data (not "No history data available")."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.wait_for_timeout(1000)
    btn_1m = page.locator(".range-buttons .btn-sm", has_text="1M")
    btn_1m.click()
    page.wait_for_timeout(2000)
    holder = page.locator("#chart-data-holder")
    expect(holder).not_to_contain_text("No history data available")


def test_range_button_3m_requests_valid_data(page: Page, seeded_server):
    """3M button should show data."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.wait_for_timeout(1000)
    btn_3m = page.locator(".range-buttons .btn-sm", has_text="3M")
    btn_3m.click()
    page.wait_for_timeout(2000)
    holder = page.locator("#chart-data-holder")
    expect(holder).not_to_contain_text("No history data available")


def test_range_button_6m_requests_valid_data(page: Page, seeded_server):
    """6M button should show data."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.wait_for_timeout(1000)
    btn_6m = page.locator(".range-buttons .btn-sm", has_text="6M")
    btn_6m.click()
    page.wait_for_timeout(2000)
    holder = page.locator("#chart-data-holder")
    expect(holder).not_to_contain_text("No history data available")


def test_date_picker_present(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    picker = page.locator("#lookup-date")
    expect(picker).to_be_visible()


def test_date_picker_returns_quote(page: Page, seeded_server):
    """Setting a known date should populate #quote-result with OHLCV data."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.fill("#lookup-date", "2026-02-13")
    page.locator("#lookup-date").dispatch_event("change")
    page.wait_for_timeout(2000)
    result = page.locator("#quote-result")
    expect(result).not_to_be_empty()
    expect(result).to_contain_text("Close")


def test_date_picker_shows_ohlcv_values(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.fill("#lookup-date", "2026-02-13")
    page.locator("#lookup-date").dispatch_event("change")
    page.wait_for_timeout(2000)
    result = page.locator("#quote-result")
    expect(result).to_contain_text("Close")
    expect(result).to_contain_text("Open")
    expect(result).to_contain_text("High")
    expect(result).to_contain_text("Low")
    expect(result).to_contain_text("Volume")


def test_prefetch_button_present(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    btn = page.locator(".prefetch-section .btn")
    expect(btn).to_be_visible()
    expect(btn).to_contain_text("Fetch 3yr History")


def test_prefetch_button_shows_feedback(page: Page, seeded_server):
    """Prefetch button should show readable feedback, not raw JSON."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    page.wait_for_timeout(1000)
    page.locator(".prefetch-section .btn").click()
    page.wait_for_timeout(2000)
    status = page.locator("#prefetch-status")
    expect(status).not_to_be_empty()
    expect(status).not_to_contain_text("{")


def test_cache_info_shows_provider(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    info = page.locator(".cache-info")
    expect(info).to_contain_text("yfinance")


def test_cache_info_shows_quote_count(page: Page, seeded_server):
    page.goto(seeded_server.url("/symbol/CSCO"))
    info = page.locator(".cache-info")
    expect(info).to_contain_text("5")


def test_cache_info_shows_date_range(page: Page, seeded_server):
    """Cache info should display a date range that covers the seeded data."""
    page.goto(seeded_server.url("/symbol/CSCO"))
    info = page.locator(".cache-info")
    expect(info).to_contain_text("Date Range")
    expect(info).to_contain_text("→")
