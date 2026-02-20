from datetime import date, timedelta
from typing import Optional

import yfinance as yf

from slc_stock.providers import QuoteData, StockProvider, register


@register
class YFinanceProvider(StockProvider):
    name = "yfinance"

    def get_quote(self, symbol: str, day: date) -> Optional[QuoteData]:
        ticker = yf.Ticker(symbol)
        # yfinance needs a range that spans the target day
        start = day
        end = day + timedelta(days=1)
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
        )

    def get_history(self, symbol: str, start: date, end: date) -> list[QuoteData]:
        ticker = yf.Ticker(symbol)
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
                )
            )
        return results
