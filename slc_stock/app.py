from datetime import date
from pathlib import Path

from flask import Blueprint, Flask, jsonify, request

import slc_stock.providers.yfinance_provider  # noqa: F401 — register providers
import slc_stock.providers.alpha_vantage_provider  # noqa: F401
import slc_stock.providers.polygon_provider  # noqa: F401
from slc_stock.logging_config import setup_logging
from slc_stock.providers import SymbolNotFoundError
from slc_stock.service import QuoteService

api = Blueprint("api", __name__)

_svc: QuoteService | None = None


def _get_svc() -> QuoteService:
    global _svc
    if _svc is None:
        _svc = QuoteService()
    return _svc


@api.route("/health")
def health():
    return jsonify({"status": "ok"})


@api.route("/stock/quote/<symbol>")
def stock_quote_latest(symbol: str):
    svc = _get_svc()
    provider_arg = request.args.get("provider")
    try:
        result = svc.get_latest_quote(symbol, provider_name=provider_arg)
    except SymbolNotFoundError as exc:
        return jsonify({"error": str(exc)}), 400
    if result is None:
        return jsonify({"error": f"No quote available for {symbol.upper()}"}), 404
    return jsonify(result)


@api.route("/stock/quote/<symbol>/<date_str>")
def stock_quote(symbol: str, date_str: str):
    svc = _get_svc()
    try:
        day = date.fromisoformat(date_str)
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD."}), 400

    provider_arg = request.args.get("provider")

    if provider_arg == "all":
        results = svc.get_quote_all_providers(symbol, day)
        return jsonify({"symbol": symbol.upper(), "date": date_str, "quotes": results})

    try:
        result = svc.get_quote(symbol, day, provider_name=provider_arg)
    except SymbolNotFoundError as exc:
        return jsonify({"error": str(exc)}), 400

    if result is None:
        return jsonify({"error": f"No quote found for {symbol.upper()} on {date_str}"}), 404
    return jsonify(result)


@api.route("/stock/history/<symbol>")
def stock_history(symbol: str):
    svc = _get_svc()
    years = request.args.get("years", 3, type=int)
    provider_arg = request.args.get("provider")
    end = date.today()
    start = date(end.year - years, end.month, end.day)

    results = svc.get_history(symbol, start, end, provider_name=provider_arg)
    return jsonify({
        "symbol": symbol.upper(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "count": len(results),
        "quotes": results,
    })


@api.route("/stock/info")
def stock_info_all():
    return jsonify(_get_svc().get_cache_info())


@api.route("/stock/info/<symbol>")
def stock_info(symbol: str):
    result = _get_svc().get_symbol_info(symbol)
    if result is None:
        return jsonify({"error": f"No data cached for {symbol.upper()}"}), 404
    return jsonify(result)


@api.route("/stock/prefetch/<symbol>", methods=["POST"])
def stock_prefetch(symbol: str):
    from slc_stock.config import DEFAULT_PROVIDER as _dp
    svc = _get_svc()
    symbol = symbol.upper()
    provider_name = request.args.get("provider") or _dp

    try:
        svc._validate_symbol(symbol, provider_name)
    except SymbolNotFoundError as exc:
        return jsonify({"error": str(exc)}), 400

    key = (symbol, provider_name)
    if key in svc._prefetch_in_flight:
        return jsonify({"status": "already_in_progress", "symbol": symbol})

    svc._maybe_background_prefetch(symbol, provider_name)
    return jsonify({"status": "started", "symbol": symbol})


def create_app() -> Flask:
    setup_logging()
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent / "templates"),
        static_folder=str(Path(__file__).parent / "static"),
    )

    app.register_blueprint(api, url_prefix="/api/v1")

    from slc_stock.web import web
    app.register_blueprint(web)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080)
