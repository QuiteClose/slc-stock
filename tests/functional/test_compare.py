import re

from playwright.sync_api import Page, expect


def test_compare_page_loads(page: Page, server):
    page.goto(server.url("/compare"))
    expect(page).to_have_title(re.compile("Compare"))
    expect(page.locator("h1")).to_have_text("Provider Comparison")


def test_compare_form_has_inputs(page: Page, server):
    page.goto(server.url("/compare"))
    expect(page.locator("input[name='symbol']")).to_be_visible()
    expect(page.locator("input[name='date']")).to_be_visible()
    expect(page.locator(".compare-form .btn")).to_be_visible()


def test_compare_empty_submit_no_crash(page: Page, server):
    """Submitting without inputs should not crash — results area stays empty."""
    page.goto(server.url("/compare"))
    page.locator(".compare-form .btn").click()
    page.wait_for_timeout(1000)
    results = page.locator("#compare-results")
    expect(results).to_be_empty()


def test_compare_valid_request_shows_table(page: Page, seeded_server):
    page.goto(seeded_server.url("/compare"))
    page.fill("input[name='symbol']", "CSCO")
    page.fill("input[name='date']", "2026-02-13")
    page.locator(".compare-form .btn").click()
    page.wait_for_timeout(2000)
    results = page.locator("#compare-results")
    expect(results).not_to_be_empty()


def test_compare_result_has_provider_column(page: Page, seeded_server):
    page.goto(seeded_server.url("/compare"))
    page.fill("input[name='symbol']", "CSCO")
    page.fill("input[name='date']", "2026-02-13")
    page.locator(".compare-form .btn").click()
    page.wait_for_timeout(2000)
    table = page.locator("#compare-results table")
    expect(table).to_contain_text("Provider")
    expect(table).to_contain_text("yfinance")


def test_compare_result_has_ohlcv_columns(page: Page, seeded_server):
    page.goto(seeded_server.url("/compare"))
    page.fill("input[name='symbol']", "CSCO")
    page.fill("input[name='date']", "2026-02-13")
    page.locator(".compare-form .btn").click()
    page.wait_for_timeout(2000)
    table = page.locator("#compare-results table")
    expect(table).to_contain_text("Open")
    expect(table).to_contain_text("High")
    expect(table).to_contain_text("Low")
    expect(table).to_contain_text("Close")
    expect(table).to_contain_text("Volume")


def test_compare_no_data_shows_message(page: Page, seeded_server):
    """A date with no seeded data should show the 'no data' message."""
    page.goto(seeded_server.url("/compare"))
    page.fill("input[name='symbol']", "CSCO")
    page.fill("input[name='date']", "2020-01-01")
    page.locator(".compare-form .btn").click()
    page.wait_for_timeout(2000)
    results = page.locator("#compare-results")
    expect(results).to_contain_text("No provider data found")
