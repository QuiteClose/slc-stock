import re

from playwright.sync_api import Page, expect


def test_nav_brand_links_to_dashboard(page: Page, server):
    page.goto(server.url("/compare"))
    page.locator(".nav-brand").click()
    expect(page).to_have_url(re.compile(r"/$"))
    expect(page).to_have_title(re.compile("Dashboard"))


def test_nav_compare_link(page: Page, server):
    page.goto(server.url("/"))
    page.locator(".nav-links a", has_text="Compare").click()
    expect(page).to_have_url(re.compile(r"/compare$"))
    expect(page).to_have_title(re.compile("Compare"))


def test_nav_dashboard_link(page: Page, server):
    page.goto(server.url("/compare"))
    page.locator(".nav-links a", has_text="Dashboard").click()
    expect(page).to_have_url(re.compile(r"/$"))


def test_symbol_row_navigates_to_symbol_page(page: Page, seeded_server):
    page.goto(seeded_server.url("/"))
    csco_row = page.locator(".symbols-section tbody tr.clickable", has_text="CSCO")
    csco_row.click()
    expect(page).to_have_url(re.compile(r"/symbol/CSCO$"))
    expect(page).to_have_title(re.compile("CSCO"))


def test_search_result_navigates_to_symbol_page(page: Page, seeded_server):
    page.goto(seeded_server.url("/"))
    page.fill(".search-form input", "AAPL")
    page.wait_for_selector(".search-result a", timeout=5000)
    page.locator(".search-result a").click()
    expect(page).to_have_url(re.compile(r"/symbol/AAPL$"))
    expect(page).to_have_title(re.compile("AAPL"))
