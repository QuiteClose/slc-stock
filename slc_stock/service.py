import json
import logging
import os
import threading
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Optional

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError

from slc_stock.config import DATABASE_URL, DEFAULT_PROVIDER, PREFETCH_YEARS
from slc_stock.db import get_session, init_db
from slc_stock.models import Quote
from slc_stock.providers import (
    QuoteData,
    SymbolNotFoundError,
    get_provider,
    list_providers,
)

log = logging.getLogger(__name__)

_MAX_FALLBACK_DAYS = 7


def _store_quote(session, qd: QuoteData, provider_name: str) -> Quote:
    existing = (
        session.query(Quote)
        .filter_by(symbol=qd.symbol.upper(), date=qd.date, provider=provider_name)
        .first()
    )
    if existing:
        existing.open = qd.open
        existing.high = qd.high
        existing.low = qd.low
        existing.close = qd.close
        existing.volume = qd.volume
        existing.adjusted = qd.adjusted
        existing.fetched_at = datetime.now(UTC)
        return existing

    row = Quote(
        symbol=qd.symbol.upper(),
        date=qd.date,
        open=qd.open,
        high=qd.high,
        low=qd.low,
        close=qd.close,
        volume=qd.volume,
        adjusted=qd.adjusted,
        provider=provider_name,
        fetched_at=datetime.now(UTC),
    )
    session.add(row)
    return row


class QuoteService:
    def __init__(self):
        init_db()
        self._prefetch_in_flight: set[tuple[str, str]] = set()
        self._lock = threading.Lock()

    @property
    def prefetch_in_flight(self) -> list[str]:
        with self._lock:
            return [f"{s}/{p}" for s, p in self._prefetch_in_flight]

    # ------------------------------------------------------------------
    # Symbol validation
    # ------------------------------------------------------------------

    def _validate_symbol(self, symbol: str, provider_name: str):
        provider = get_provider(provider_name)
        if not provider.validate_symbol(symbol):
            log.error("Invalid symbol rejected: %s (provider=%s)", symbol, provider_name)
            raise SymbolNotFoundError(symbol)

    # ------------------------------------------------------------------
    # Single-day quote with market-closed fallback
    # ------------------------------------------------------------------

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
                log.info("Cache hit: %s %s (%s)", symbol, day, pname)
                result = row.to_dict()
                result["requested_date"] = day.isoformat()
                self._maybe_background_prefetch(symbol, pname)
                return result

            self._validate_symbol(symbol, pname)

            provider = get_provider(pname)
            qd = provider.get_quote(symbol, day)

            if qd is not None:
                _store_quote(session, qd, pname)
                session.commit()
                log.info("Cache miss → fetched: %s %s (%s)", symbol, day, pname)
                row = (
                    session.query(Quote)
                    .filter_by(symbol=symbol, date=day, provider=pname)
                    .first()
                )
                result = row.to_dict()
                result["requested_date"] = day.isoformat()
                self._maybe_background_prefetch(symbol, pname)
                return result

            # Market closed — walk back up to _MAX_FALLBACK_DAYS
            log.info("No data for %s on %s, walking back for previous trading day", symbol, day)
            for offset in range(1, _MAX_FALLBACK_DAYS + 1):
                fallback_day = day - timedelta(days=offset)

                cached = (
                    session.query(Quote)
                    .filter_by(symbol=symbol, date=fallback_day, provider=pname)
                    .first()
                )
                if cached:
                    log.info("Fallback cache hit: %s %s (requested %s)", symbol, fallback_day, day)
                    result = cached.to_dict()
                    result["requested_date"] = day.isoformat()
                    self._maybe_background_prefetch(symbol, pname)
                    return result

                qd = provider.get_quote(symbol, fallback_day)
                if qd is not None:
                    _store_quote(session, qd, pname)
                    session.commit()
                    log.info("Fallback fetched: %s %s (requested %s)", symbol, fallback_day, day)
                    row = (
                        session.query(Quote)
                        .filter_by(symbol=symbol, date=fallback_day, provider=pname)
                        .first()
                    )
                    result = row.to_dict()
                    result["requested_date"] = day.isoformat()
                    self._maybe_background_prefetch(symbol, pname)
                    return result

            log.warning("No trading day found within %d days of %s for %s", _MAX_FALLBACK_DAYS, day, symbol)
            return None
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Latest quote (no date specified)
    # ------------------------------------------------------------------

    def get_latest_quote(
        self,
        symbol: str,
        provider_name: Optional[str] = None,
    ) -> Optional[dict]:
        symbol = symbol.upper()
        pname = provider_name or DEFAULT_PROVIDER
        return self.get_quote(symbol, date.today(), provider_name=pname)

    # ------------------------------------------------------------------
    # Multi-provider comparison
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # History
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Prefetch
    # ------------------------------------------------------------------

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

        try:
            quotes = provider.get_history(symbol, start, end)
        except Exception:
            log.warning(
                "Prefetch: provider error for %s %s→%s (%s), storing what was retrieved",
                symbol, start, end, pname,
                exc_info=True,
            )
            quotes = []

        if not quotes:
            log.warning("Prefetch: no data returned for %s (%s)", symbol, pname)
            return 0

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

        log.info("Prefetch complete: %s (%s) — %d quotes stored", symbol, pname, stored)
        return stored

    # ------------------------------------------------------------------
    # Background prefetch
    # ------------------------------------------------------------------

    def _maybe_background_prefetch(self, symbol: str, provider_name: str):
        key = (symbol, provider_name)
        with self._lock:
            if key in self._prefetch_in_flight:
                return
            self._prefetch_in_flight.add(key)

        session = get_session()
        try:
            count = (
                session.query(func.count(Quote.id))
                .filter_by(symbol=symbol, provider=provider_name)
                .scalar()
            )
        finally:
            session.close()

        if count and count > 30:
            with self._lock:
                self._prefetch_in_flight.discard(key)
            return

        log.info("Background prefetch triggered for %s (%s)", symbol, provider_name)
        thread = threading.Thread(
            target=self._do_background_prefetch,
            args=(symbol, provider_name, key),
            daemon=True,
        )
        thread.start()

    def _do_background_prefetch(self, symbol: str, provider_name: str, key: tuple):
        try:
            end = date.today()
            start = date(end.year - PREFETCH_YEARS, end.month, end.day)
            count = self.prefetch(symbol, start, end, provider_name=provider_name)
            log.info("Background prefetch finished: %s (%s) — %d quotes", symbol, provider_name, count)
        except Exception:
            log.error(
                "Background prefetch failed: %s (%s)",
                symbol, provider_name,
                exc_info=True,
            )
        finally:
            with self._lock:
                self._prefetch_in_flight.discard(key)

    # ------------------------------------------------------------------
    # Info / diagnostics
    # ------------------------------------------------------------------

    def get_symbol_info(self, symbol: str) -> Optional[dict]:
        symbol = symbol.upper()
        session = get_session()
        try:
            rows = (
                session.query(
                    Quote.provider,
                    func.count(Quote.id).label("cnt"),
                    func.min(Quote.date).label("earliest"),
                    func.max(Quote.date).label("latest"),
                    func.max(Quote.fetched_at).label("last_fetched"),
                )
                .filter_by(symbol=symbol)
                .group_by(Quote.provider)
                .all()
            )
            if not rows:
                return None

            by_provider = {}
            total = 0
            all_earliest = None
            all_latest = None
            providers_list = []
            for r in rows:
                by_provider[r.provider] = {
                    "count": r.cnt,
                    "earliest": r.earliest.isoformat() if r.earliest else None,
                    "latest": r.latest.isoformat() if r.latest else None,
                    "last_fetched": r.last_fetched.isoformat() if r.last_fetched else None,
                }
                total += r.cnt
                providers_list.append(r.provider)
                if all_earliest is None or (r.earliest and r.earliest < all_earliest):
                    all_earliest = r.earliest
                if all_latest is None or (r.latest and r.latest > all_latest):
                    all_latest = r.latest

            return {
                "symbol": symbol,
                "providers": providers_list,
                "total_quotes": total,
                "date_range": {
                    "earliest": all_earliest.isoformat() if all_earliest else None,
                    "latest": all_latest.isoformat() if all_latest else None,
                },
                "by_provider": by_provider,
            }
        finally:
            session.close()

    def get_cache_info(self) -> dict:
        session = get_session()
        try:
            total = session.query(func.count(Quote.id)).scalar() or 0

            symbol_rows = (
                session.query(
                    Quote.symbol,
                    func.count(Quote.id).label("cnt"),
                    func.min(Quote.date).label("earliest"),
                    func.max(Quote.date).label("latest"),
                    func.max(Quote.fetched_at).label("last_fetched"),
                )
                .group_by(Quote.symbol)
                .order_by(Quote.symbol)
                .all()
            )

            symbols = []
            for r in symbol_rows:
                prov_rows = (
                    session.query(Quote.provider)
                    .filter_by(symbol=r.symbol)
                    .distinct()
                    .all()
                )
                symbols.append({
                    "symbol": r.symbol,
                    "total_quotes": r.cnt,
                    "providers": sorted(p[0] for p in prov_rows),
                    "earliest": r.earliest.isoformat() if r.earliest else None,
                    "latest": r.latest.isoformat() if r.latest else None,
                    "last_fetched": r.last_fetched.isoformat() if r.last_fetched else None,
                })

            db_path = DATABASE_URL.replace("sqlite:///", "")
            db_size_mb = 0.0
            if os.path.exists(db_path):
                db_size_mb = round(os.path.getsize(db_path) / (1024 * 1024), 2)

            configured = {}
            for name, prov in list_providers().items():
                configured[name] = prov.is_configured()

            return {
                "total_quotes": total,
                "total_symbols": len(symbol_rows),
                "database_path": db_path,
                "database_size_mb": db_size_mb,
                "providers_configured": configured,
                "prefetch_in_flight": self.prefetch_in_flight,
                "symbols": symbols,
            }
        finally:
            session.close()

    # ------------------------------------------------------------------
    # Dump / load (backup & restore)
    # ------------------------------------------------------------------

    def dump_database(self) -> list[dict]:
        session = get_session()
        try:
            rows = session.query(Quote).order_by(Quote.symbol, Quote.date).all()
            return [r.to_dict() for r in rows]
        finally:
            session.close()

    def load_database(self, records: list[dict]) -> int:
        session = get_session()
        loaded = 0
        skipped = 0
        try:
            for i, rec in enumerate(records):
                try:
                    qd = QuoteData(
                        symbol=rec["symbol"],
                        date=date.fromisoformat(rec["date"]),
                        open=rec.get("open"),
                        high=rec.get("high"),
                        low=rec.get("low"),
                        close=rec.get("close"),
                        volume=rec.get("volume"),
                        adjusted=rec.get("adjusted", True),
                    )
                    _store_quote(session, qd, rec["provider"])
                    session.flush()
                    loaded += 1
                except (KeyError, ValueError, TypeError) as exc:
                    log.warning("Skipping malformed record %d: %s", i, exc)
                    skipped += 1
                except IntegrityError:
                    session.rollback()
            session.commit()
        finally:
            session.close()
        if skipped:
            log.warning("Database load: %d records skipped due to errors", skipped)
        log.info("Database load complete: %d records imported", loaded)
        return loaded
