from datetime import date, datetime
from typing import Optional

from sqlalchemy.exc import IntegrityError

from slc_stock.config import DEFAULT_PROVIDER
from slc_stock.db import get_session, init_db
from slc_stock.models import Quote
from slc_stock.providers import (
    QuoteData,
    StockProvider,
    get_provider,
    list_providers,
)


def _store_quote(session, qd: QuoteData, provider_name: str) -> Quote:
    row = Quote(
        symbol=qd.symbol.upper(),
        date=qd.date,
        open=qd.open,
        high=qd.high,
        low=qd.low,
        close=qd.close,
        volume=qd.volume,
        provider=provider_name,
        fetched_at=datetime.utcnow(),
    )
    session.merge(row)
    return row


class QuoteService:
    def __init__(self):
        init_db()

    def get_quote(
        self,
        symbol: str,
        day: date,
        provider_name: Optional[str] = None,
    ) -> Optional[dict]:
        symbol = symbol.upper()
        pname = provider_name or DEFAULT_PROVIDER
        session = get_session()
        try:
            row = (
                session.query(Quote)
                .filter_by(symbol=symbol, date=day, provider=pname)
                .first()
            )
            if row:
                return row.to_dict()

            provider = get_provider(pname)
            qd = provider.get_quote(symbol, day)
            if qd is None:
                return None

            _store_quote(session, qd, pname)
            session.commit()

            row = (
                session.query(Quote)
                .filter_by(symbol=symbol, date=day, provider=pname)
                .first()
            )
            return row.to_dict() if row else None
        finally:
            session.close()

    def get_quote_all_providers(self, symbol: str, day: date) -> list[dict]:
        symbol = symbol.upper()
        session = get_session()
        try:
            rows = (
                session.query(Quote)
                .filter_by(symbol=symbol, date=day)
                .all()
            )
            return [r.to_dict() for r in rows]
        finally:
            session.close()

    def get_history(
        self,
        symbol: str,
        start: date,
        end: date,
        provider_name: Optional[str] = None,
    ) -> list[dict]:
        symbol = symbol.upper()
        pname = provider_name or DEFAULT_PROVIDER
        session = get_session()
        try:
            rows = (
                session.query(Quote)
                .filter(
                    Quote.symbol == symbol,
                    Quote.date >= start,
                    Quote.date <= end,
                    Quote.provider == pname,
                )
                .order_by(Quote.date)
                .all()
            )
            return [r.to_dict() for r in rows]
        finally:
            session.close()

    def prefetch(
        self,
        symbol: str,
        start: date,
        end: date,
        provider_name: Optional[str] = None,
    ) -> int:
        """Download history from a provider and store it. Returns row count."""
        symbol = symbol.upper()
        pname = provider_name or DEFAULT_PROVIDER
        provider = get_provider(pname)
        quotes = provider.get_history(symbol, start, end)

        session = get_session()
        stored = 0
        try:
            for qd in quotes:
                try:
                    _store_quote(session, qd, pname)
                    session.flush()
                    stored += 1
                except IntegrityError:
                    session.rollback()
            session.commit()
        finally:
            session.close()

        return stored
