"""
DataProvider Interface (services/data_provider.py)

Defines the abstract contract that all stock data sources must fulfil.
Business logic (StockService, indicators, portfolio summary) depends on
DataProvider, NOT on yFinance directly — so swapping YFinanceProvider for
AlphaVantageProvider requires zero changes to any other module.

Pattern: Strategy / Pluggable Provider
"""

from abc import ABC, abstractmethod


# ── Abstract Interface ────────────────────────────────────────────────────────

class DataProvider(ABC):
    """
    Abstract base class defining the minimum contract for any stock data source.

    Every concrete provider (yFinance, AlphaVantage, mock) MUST implement
    all methods below. Callers program to this interface, not to the implementation.
    """

    @abstractmethod
    def get_stock_data(self, symbol: str) -> dict:
        """
        Fetch the latest price and metadata for a stock symbol.

        Args:
            symbol: Stock ticker (e.g., "AAPL", "RELIANCE.NS").

        Returns:
            dict with at minimum:
            {
                "symbol": str,
                "price": float,
                "currency": str,
                "exchange": str,
            }

        Raises:
            ValueError:     Symbol not found or no data available.
            RuntimeError:   Network or provider-level failure.
        """
        ...

    @abstractmethod
    def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> dict:
        """
        Fetch historical OHLC + volume data.

        Args:
            symbol:   Stock ticker.
            period:   Time range string (e.g., "1mo", "3mo", "1y").
            interval: Candle size (e.g., "1d", "1h").

        Returns:
            dict with at minimum:
            {
                "symbol": str,
                "period": str,
                "interval": str,
                "num_candles": int,
                "data": list[dict],  # each dict: date, open, high, low, close, volume
            }

        Raises:
            ValueError:   No data found.
            RuntimeError: Provider failure.
        """
        ...


# ── YFinance Provider ─────────────────────────────────────────────────────────

class YFinanceProvider(DataProvider):
    """
    Concrete DataProvider backed by yFinance (via StockService).

    Delegates to the existing StockService singleton which already has:
    - Tenacity retry (3 attempts, exponential backoff)
    - Circuit breaker (CLOSED / OPEN / HALF_OPEN)
    - Clean dict output (no pandas types leaked)
    """

    def __init__(self) -> None:
        # Import here (not at module top) to avoid circular import issues
        # if data_provider.py is imported before stock_service.py is ready.
        from app.services.stock_service import stock_service
        self._service = stock_service

    def get_stock_data(self, symbol: str) -> dict:
        return self._service.get_current_price(symbol)

    def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> dict:
        return self._service.get_historical_data(symbol, period=period, interval=interval)


# ── Module-level default provider ─────────────────────────────────────────────
# Routers and services import this singleton.
# To switch to AlphaVantage:
#   1. Create AlphaVantageProvider(DataProvider)
#   2. Change: default_provider = AlphaVantageProvider()
#   — No other file needs to change.
default_provider: DataProvider = YFinanceProvider()
