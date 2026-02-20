import logging
from datetime import date, timedelta
from typing import Optional

import yfinance as yf

from slc_stock.providers import QuoteData, StockProvider, register

log = logging.getLogger(__name__)


@register
class YFinanceProvider(StockProvider):
    name = "yfinance"

    def validate_symbol(self, symbol: str) -> bool:
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            return bool(info and info.get("shortName"))
        except Exception:
            return False

    def get_quote(self, symbol: str, day: date) -> Optional[QuoteData]:
        ticker = yf.Ticker(symbol)
        start = day
        end = day + timedelta(days=1)
        log.info("yfinance: fetching %s for %s", symbol, day.isoformat())
        df = ticker.history(start=start.isoformat(), end=end.isoformat())
        if df.empty:
            return None
        row = df.iloc[0]
        return QuoteData(
            symbol=symbol,
            date=day,
            open=float(row["Open"]),
            high=float(row["High"]),
            low=float(row["Low"]),
            close=float(row["Close"]),
            volume=float(row["Volume"]),
            adjusted=True,
        )

    def get_history(self, symbol: str, start: date, end: date) -> list[QuoteData]:
        ticker = yf.Ticker(symbol)
        log.info(
            "yfinance: fetching history %s %s→%s",
            symbol, start.isoformat(), end.isoformat(),
        )
        df = ticker.history(start=start.isoformat(), end=end.isoformat())
        results = []
        for idx, row in df.iterrows():
            results.append(
                QuoteData(
                    symbol=symbol,
                    date=idx.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=float(row["Close"]),
                    volume=float(row["Volume"]),
                    adjusted=True,
                )
            )
        return results
