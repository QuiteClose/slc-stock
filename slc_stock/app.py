from datetime import date

from flask import Flask, jsonify, request

import slc_stock.providers.yfinance_provider  # noqa: F401 — register providers
import slc_stock.providers.alpha_vantage_provider  # noqa: F401
import slc_stock.providers.polygon_provider  # noqa: F401
from slc_stock.logging_config import setup_logging
from slc_stock.providers import SymbolNotFoundError
from slc_stock.service import QuoteService


def create_app() -> Flask:
    setup_logging()
    app = Flask(__name__)
    svc = QuoteService()

    @app.route("/health")
    def health():
        return jsonify({"status": "ok"})

    @app.route("/stock/quote/<symbol>")
    def stock_quote_latest(symbol: str):
        provider_arg = request.args.get("provider")
        try:
            result = svc.get_latest_quote(symbol, provider_name=provider_arg)
        except SymbolNotFoundError as exc:
            return jsonify({"error": str(exc)}), 400
        if result is None:
            return jsonify({"error": f"No quote available for {symbol.upper()}"}), 404
        return jsonify(result)

    @app.route("/stock/quote/<symbol>/<date_str>")
    def stock_quote(symbol: str, date_str: str):
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

    @app.route("/stock/history/<symbol>")
    def stock_history(symbol: str):
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

    @app.route("/stock/info")
    def stock_info_all():
        return jsonify(svc.get_cache_info())

    @app.route("/stock/info/<symbol>")
    def stock_info(symbol: str):
        result = svc.get_symbol_info(symbol)
        if result is None:
            return jsonify({"error": f"No data cached for {symbol.upper()}"}), 404
        return jsonify(result)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000)
