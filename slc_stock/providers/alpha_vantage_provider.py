from datetime import date
from typing import Optional

import requests

from slc_stock.config import ALPHA_VANTAGE_API_KEY
from slc_stock.providers import QuoteData, StockProvider, register

_BASE_URL = "https://www.alphavantage.co/query"


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

    def _fetch_daily(self, symbol: str, outputsize: str = "compact") -> dict:
        self._require_key()
        params = {
            "function": "TIME_SERIES_DAILY",
            "symbol": symbol,
            "outputsize": outputsize,
            "apikey": ALPHA_VANTAGE_API_KEY,
        }
        resp = requests.get(_BASE_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        if "Error Message" in data:
            raise RuntimeError(f"Alpha Vantage error: {data['Error Message']}")
        if "Note" in data:
            raise RuntimeError(f"Alpha Vantage rate limit: {data['Note']}")
        return data.get("Time Series (Daily)", {})

    @staticmethod
    def _parse_row(symbol: str, day_str: str, row: dict) -> QuoteData:
        return QuoteData(
            symbol=symbol,
            date=date.fromisoformat(day_str),
            open=float(row["1. open"]),
            high=float(row["2. high"]),
            low=float(row["3. low"]),
            close=float(row["4. close"]),
            volume=float(row["5. volume"]),
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
