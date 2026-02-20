import logging
import time
from datetime import date
from typing import Optional

import requests

from slc_stock.config import ALPHA_VANTAGE_API_KEY
from slc_stock.providers import QuoteData, StockProvider, register

log = logging.getLogger(__name__)

_BASE_URL = "https://www.alphavantage.co/query"
_RETRY_DELAYS = [15, 30, 60]


def _request_with_retry(params: dict) -> dict:
    for attempt in range(_RETRY_DELAYS.__len__() + 1):
        resp = requests.get(_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        if "Error Message" in data:
            raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")

        if "Note" in data:
            if attempt < len(_RETRY_DELAYS):
                delay = _RETRY_DELAYS[attempt]
                log.warning(
                    "Alpha Vantage rate limit hit, retrying in %ds (attempt %d/%d)",
                    delay, attempt + 1, len(_RETRY_DELAYS),
                )
                time.sleep(delay)
                continue
            raise RuntimeError(f"Alpha Vantage rate limit after {len(_RETRY_DELAYS)} retries: {data['Note']}")

        return data

    return {}


@register
class AlphaVantageProvider(StockProvider):
    name = "alpha_vantage"

    def is_configured(self) -> bool:
        return bool(ALPHA_VANTAGE_API_KEY)

    def _require_key(self):
        if not self.is_configured():
            raise RuntimeError(
                "ALPHA_VANTAGE_API_KEY is not set. "
                "Get a free key at https://www.alphavantage.co/support/#api-key"
            )

    def validate_symbol(self, symbol: str) -> bool:
        if not self.is_configured():
            return True
        try:
            params = {
                "function": "SYMBOL_SEARCH",
                "keywords": symbol,
                "apikey": ALPHA_VANTAGE_API_KEY,
            }
            resp = requests.get(_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            matches = resp.json().get("bestMatches", [])
            return any(m.get("1. symbol", "").upper() == symbol.upper() for m in matches)
        except Exception:
            return True

    def _fetch_daily(self, symbol: str, outputsize: str = "compact") -> dict:
        self._require_key()
        log.info("Alpha Vantage: fetching %s (outputsize=%s)", symbol, outputsize)
        params = {
            "function": "TIME_SERIES_DAILY_ADJUSTED",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": ALPHA_VANTAGE_API_KEY,
        }
        data = _request_with_retry(params)
        return data.get("Time Series (Daily)", {})

    @staticmethod
    def _parse_row(symbol: str, day_str: str, row: dict) -> QuoteData:
        return QuoteData(
            symbol=symbol,
            date=date.fromisoformat(day_str),
            open=float(row["1. open"]),
            high=float(row["2. high"]),
            low=float(row["3. low"]),
            close=float(row.get("5. adjusted close", row["4. close"])),
            volume=float(row["6. volume"] if "6. volume" in row else row["5. volume"]),
            adjusted=True,
        )

    def get_quote(self, symbol: str, day: date) -> Optional[QuoteData]:
        daily = self._fetch_daily(symbol, outputsize="compact")
        day_str = day.isoformat()
        if day_str not in daily:
            return None
        return self._parse_row(symbol, day_str, daily[day_str])

    def get_history(self, symbol: str, start: date, end: date) -> list[QuoteData]:
        daily = self._fetch_daily(symbol, outputsize="full")
        results = []
        for day_str, row in daily.items():
            d = date.fromisoformat(day_str)
            if start <= d <= end:
                results.append(self._parse_row(symbol, day_str, row))
        results.sort(key=lambda q: q.date)
        return results
