from datetime import date, timedelta
from typing import Optional

import requests

from slc_stock.config import POLYGON_API_KEY
from slc_stock.providers import QuoteData, StockProvider, register

_BASE_URL = "https://api.polygon.io"


@register
class PolygonProvider(StockProvider):
    name = "polygon"

    def is_configured(self) -> bool:
        return bool(POLYGON_API_KEY)

    def _require_key(self):
        if not self.is_configured():
            raise RuntimeError(
                "POLYGON_API_KEY is not set. "
                "Get a free key at https://polygon.io/dashboard/signup"
            )

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {POLYGON_API_KEY}"}

    def get_quote(self, symbol: str, day: date) -> Optional[QuoteData]:
        self._require_key()
        url = f"{_BASE_URL}/v1/open-close/{symbol.upper()}/{day.isoformat()}"
        resp = requests.get(
            url, headers=self._headers(), params={"adjusted": "true"}, timeout=30
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        data = resp.json()
        if data.get("status") == "NOT_FOUND":
            return None
        return QuoteData(
            symbol=symbol,
            date=day,
            open=float(data.get("open", 0)),
            high=float(data.get("high", 0)),
            low=float(data.get("low", 0)),
            close=float(data.get("close", 0)),
            volume=float(data.get("volume", 0)),
        )

    def get_history(self, symbol: str, start: date, end: date) -> list[QuoteData]:
        self._require_key()
        url = (
            f"{_BASE_URL}/v2/aggs/ticker/{symbol.upper()}"
            f"/range/1/day/{start.isoformat()}/{end.isoformat()}"
        )
        params = {"adjusted": "true", "sort": "asc", "limit": 50000}
        results: list[QuoteData] = []

        while url:
            resp = requests.get(
                url, headers=self._headers(), params=params, timeout=30
            )
            resp.raise_for_status()
            data = resp.json()
            for bar in data.get("results", []):
                ts_ms = bar["t"]
                bar_date = date.fromtimestamp(ts_ms / 1000)
                results.append(
                    QuoteData(
                        symbol=symbol,
                        date=bar_date,
                        open=float(bar.get("o", 0)),
                        high=float(bar.get("h", 0)),
                        low=float(bar.get("l", 0)),
                        close=float(bar.get("c", 0)),
                        volume=float(bar.get("v", 0)),
                    )
                )
            url = data.get("next_url")
            params = {}

        return results
