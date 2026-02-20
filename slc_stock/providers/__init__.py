from abc import ABC, abstractmethod
from datetime import date
from typing import Optional


class QuoteData:
    """Normalized quote returned by every provider."""

    def __init__(
        self,
        symbol: str,
        date: date,
        open: Optional[float],
        high: Optional[float],
        low: Optional[float],
        close: Optional[float],
        volume: Optional[float],
    ):
        self.symbol = symbol.upper()
        self.date = date
        self.open = open
        self.high = high
        self.low = low
        self.close = close
        self.volume = volume


class StockProvider(ABC):
    """Common interface every data provider must implement."""

    name: str = ""

    @abstractmethod
    def get_quote(self, symbol: str, day: date) -> Optional[QuoteData]:
        """Fetch a single day's OHLCV. Return None if unavailable."""

    @abstractmethod
    def get_history(
        self, symbol: str, start: date, end: date
    ) -> list[QuoteData]:
        """Fetch daily OHLCV for a date range."""

    def is_configured(self) -> bool:
        """Return True if this provider has all required credentials."""
        return True


_registry: dict[str, type[StockProvider]] = {}


def register(cls: type[StockProvider]) -> type[StockProvider]:
    _registry[cls.name] = cls
    return cls


def get_provider(name: str) -> StockProvider:
    if name not in _registry:
        raise ValueError(
            f"Unknown provider '{name}'. Available: {list(_registry.keys())}"
        )
    return _registry[name]()


def list_providers() -> dict[str, StockProvider]:
    return {name: cls() for name, cls in _registry.items()}
