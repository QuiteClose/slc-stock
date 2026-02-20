import logging
import time
from datetime import date
from typing import Optional

import requests

from slc_stock.config import POLYGON_API_KEY
from slc_stock.providers import QuoteData, StockProvider, register

log = logging.getLogger(__name__)

_BASE_URL = "https://api.polygon.io"
_RETRY_DELAYS = [15, 30, 60]


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

    def _get_with_retry(self, url: str, params: dict | None = None) -> requests.Response:
        for attempt in range(len(_RETRY_DELAYS) + 1):
            resp = requests.get(
                url, headers=self._headers(), params=params or {}, timeout=30
            )
            if resp.status_code == 429:
                if attempt < len(_RETRY_DELAYS):
                    delay = _RETRY_DELAYS[attempt]
                    log.warning(
                        "Polygon rate limit (429), retrying in %ds (attempt %d/%d)",
                        delay, attempt + 1, len(_RETRY_DELAYS),
                    )
                    time.sleep(delay)
                    continue
                resp.raise_for_status()
            return resp
        return resp

    def validate_symbol(self, symbol: str) -> bool:
        if not self.is_configured():
            return True
        try:
            url = f"{_BASE_URL}/v3/reference/tickers/{symbol.upper()}"
            resp = requests.get(url, headers=self._headers(), timeout=15)
            if resp.status_code == 404:
                return False
            resp.raise_for_status()
            data = resp.json()
            return data.get("status") == "OK" and bool(data.get("results"))
        except Exception:
            return True

    def get_quote(self, symbol: str, day: date) -> Optional[QuoteData]:
        self._require_key()
        url = f"{_BASE_URL}/v1/open-close/{symbol.upper()}/{day.isoformat()}"
        log.info("Polygon: fetching %s for %s", symbol, day.isoformat())
        resp = self._get_with_retry(url, {"adjusted": "true"})
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
            adjusted=True,
        )

    def get_history(self, symbol: str, start: date, end: date) -> list[QuoteData]:
        self._require_key()
        url = (
            f"{_BASE_URL}/v2/aggs/ticker/{symbol.upper()}"
            f"/range/1/day/{start.isoformat()}/{end.isoformat()}"
        )
        params: dict = {"adjusted": "true", "sort": "asc", "limit": 50000}
        results: list[QuoteData] = []
        log.info(
            "Polygon: fetching history %s %s→%s",
            symbol, start.isoformat(), end.isoformat(),
        )

        while url:
            resp = self._get_with_retry(url, params)
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
                        adjusted=True,
                    )
                )
            url = data.get("next_url")
            params = {}

        return results
