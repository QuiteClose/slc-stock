import logging
from datetime import date, timedelta
from html import escape as html_escape

from flask import Blueprint, render_template, request

from slc_stock.app import _get_svc
from slc_stock.providers import SymbolNotFoundError
from slc_stock.validation import is_valid_symbol_format

log = logging.getLogger(__name__)

web = Blueprint("web", __name__)

_MAX_CHART_DAYS = 3650
_MIN_CHART_DAYS = 1


def _bad_symbol_html():
    return '<p class="error">Invalid symbol format.</p>', 400


@web.route("/")
def dashboard():
    svc = _get_svc()
    cache_info = svc.get_cache_info()
    return render_template("dashboard.html", cache=cache_info)


@web.route("/symbol/<symbol>")
def symbol_detail(symbol: str):
    if not is_valid_symbol_format(symbol):
        return _bad_symbol_html()
    svc = _get_svc()
    symbol = symbol.upper()
    info = svc.get_symbol_info(symbol)
    latest = None
    try:
        latest = svc.get_latest_quote(symbol)
    except SymbolNotFoundError:
        pass
    except Exception:
        log.exception("Failed to fetch latest quote for %s", symbol)
    return render_template("symbol.html", symbol=symbol, info=info, latest=latest)


@web.route("/compare")
def compare():
    return render_template("compare.html")


# ---- htmx partials ----

@web.route("/ui/search")
def ui_search():
    q = request.args.get("q", "").strip().upper()
    if not q:
        return ""
    svc = _get_svc()
    info = svc.get_symbol_info(q)
    cached = info is not None
    return render_template("partials/search_results.html", symbol=q, cached=cached, info=info)


@web.route("/ui/quote/<symbol>/<date_str>")
def ui_quote(symbol: str, date_str: str):
    if not is_valid_symbol_format(symbol):
        return _bad_symbol_html()
    svc = _get_svc()
    symbol = symbol.upper()
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        return '<p class="error">Invalid date format.</p>'

    try:
        result = svc.get_quote(symbol, day)
    except SymbolNotFoundError:
        return f'<p class="error">Symbol {html_escape(symbol)} not found.</p>'

    if result is None:
        return f'<p class="muted">No data for {html_escape(symbol)} near {html_escape(date_str)}.</p>'

    return render_template("partials/quote_result.html", q=result)


@web.route("/ui/cache-status")
def ui_cache_status():
    svc = _get_svc()
    cache_info = svc.get_cache_info()
    return render_template("partials/cache_status.html", cache=cache_info)


@web.route("/ui/chart-data/<symbol>")
def ui_chart_data(symbol: str):
    if not is_valid_symbol_format(symbol):
        return _bad_symbol_html()
    svc = _get_svc()
    symbol = symbol.upper()
    days = request.args.get("days", 1095, type=int)
    if not _MIN_CHART_DAYS <= days <= _MAX_CHART_DAYS:
        return '<p class="error">days must be between 1 and 3650.</p>', 400
    end = date.today()
    start = end - timedelta(days=days)
    quotes = svc.get_history(symbol, start, end)
    return render_template("partials/chart_data.html", symbol=symbol, quotes=quotes)


@web.route("/ui/prefetch/<symbol>", methods=["POST"])
def ui_prefetch(symbol: str):
    if not is_valid_symbol_format(symbol):
        return _bad_symbol_html()
    svc = _get_svc()
    symbol = symbol.upper()
    from slc_stock.config import DEFAULT_PROVIDER as _dp
    provider_name = request.args.get("provider") or _dp

    try:
        svc._validate_symbol(symbol, provider_name)
    except SymbolNotFoundError as exc:
        return f'<p class="error">{html_escape(str(exc))}</p>'

    key = (symbol, provider_name)
    if key in svc._prefetch_in_flight:
        return '<p class="info">Prefetch already in progress.</p>'

    svc._maybe_background_prefetch(symbol, provider_name)
    return '<p class="success">Prefetch started.</p>'


@web.route("/ui/compare")
def ui_compare():
    symbol = request.args.get("symbol", "").strip().upper()
    date_str = request.args.get("date", "").strip()
    if not symbol or not date_str:
        return ""
    svc = _get_svc()
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        return '<p class="error">Invalid date.</p>'
    results = svc.get_quote_all_providers(symbol, day)
    return render_template("partials/compare_results.html", symbol=symbol, date=date_str, quotes=results)
