"""
Stock Service (services/stock_service.py)

Responsibilities:
- Fetch real-time and historical stock data using yFinance.
- Return clean, structured Python dictionaries (NOT ORM objects, NOT DataFrames).
- Handle missing/invalid symbols and yFinance failures gracefully.
- Retry transient network failures automatically using tenacity.
- Zero LLM logic here — pure data retrieval and normalization.

Retry Strategy:
- Max 3 attempts (1 original + 2 retries).
- Exponential backoff: 2^n seconds between attempts (2s, 4s).
- Only retries on RuntimeError (network/infrastructure failure).
- Does NOT retry ValueError (bad symbol — retrying would fail every time).
- Logs every retry attempt for observability.
"""

import logging
from typing import Optional

import yfinance as yf
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    before_sleep_log,
)

from app.core.circuit_breaker import CircuitBreaker, CircuitBreakerOpenError  # noqa: F401

logger = logging.getLogger(__name__)

# ── Shared retry policy ───────────────────────────────────────────────────────
# Reused by both get_current_price and get_historical_data as a decorator.
# Only retries RuntimeError (network failures), NOT ValueError (bad symbol).
_stock_retry = retry(
    retry=retry_if_exception_type(RuntimeError),   # Only retry infra failures
    stop=stop_after_attempt(3),                     # 1 original + 2 retries
    wait=wait_exponential(multiplier=1, min=2, max=8),  # 2s → 4s → 8s
    before_sleep=before_sleep_log(logger, logging.WARNING),  # Log each retry
    reraise=True,  # Re-raise the last exception if all attempts exhausted
)


class StockService:
    """
    Thin wrapper around yFinance for fetching stock market data.

    Resilience layers applied (outermost to innermost):
    1. CircuitBreaker → blocks calls when yFinance is repeatedly unavailable.
    2. Tenacity retry  → retries transient failures with exponential backoff.
    3. ValueError guard → rejects bad symbols before hitting the network.

    Error handling contract:
    - Symbol invalid / no data → raises ValueError.
    - Network failure after all retries → raises RuntimeError.
    - Circuit OPEN (too many failures) → raises CircuitBreakerOpenError.
    - Caller converts these to HTTP 404 / 503 as needed.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ) -> None:
        # Shared circuit breaker for all yFinance calls from this instance.
        # Tracks consecutive outer-level failures (after retries are exhausted).
        self._cb = CircuitBreaker(
            name="yfinance",
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
    # ── 1. Current Price ─────────────────────────────────────────────────────

    def get_current_price(self, symbol: str) -> dict:
        """Routes through circuit breaker, then retries on failure."""
        return self._cb.call(self._fetch_current_price, symbol)

    @_stock_retry  # Retries up to 3 times on RuntimeError with exponential backoff
    def _fetch_current_price(self, symbol: str) -> dict:
        """
        Fetches the latest market price for a stock symbol.

        Returns:
            {
                "symbol": "AAPL",
                "price": 175.23,
                "currency": "USD",
                "exchange": "NMS",
                "market_state": "REGULAR",   # REGULAR | PRE | POST | CLOSED
                "previous_close": 174.10,
                "day_high": 176.80,
                "day_low": 174.00,
            }

        Raises:
            ValueError: If symbol is invalid or no data is returned.
            RuntimeError: If yFinance request fails due to a network error.
        """
        symbol = symbol.upper().strip()
        logger.info("Fetching current price | symbol=%s", symbol)

        try:
            ticker = yf.Ticker(symbol)
            info = ticker.fast_info  # faster than .info — avoids full scrape

            # fast_info raises no error on bad symbol — we detect via None price
            price: Optional[float] = getattr(info, "last_price", None)

            if price is None or price == 0.0:
                # Attempt fallback via .info (slower but more reliable)
                full_info = ticker.info
                price = full_info.get("currentPrice") or full_info.get("regularMarketPrice")

            if not price:
                raise ValueError(
                    f"No price data found for symbol '{symbol}'. "
                    "It may be delisted, misspelled, or not supported by yFinance."
                )

            result = {
                "symbol": symbol,
                "price": round(float(price), 4),
                "currency": getattr(info, "currency", "N/A"),
                "exchange": getattr(info, "exchange", "N/A"),
                "market_state": getattr(info, "market_state", "UNKNOWN"),
                "previous_close": round(float(getattr(info, "previous_close", 0) or 0), 4),
                "day_high": round(float(getattr(info, "day_high", 0) or 0), 4),
                "day_low": round(float(getattr(info, "day_low", 0) or 0), 4),
            }
            logger.info("Price fetched | symbol=%s | price=%s", symbol, result["price"])
            return result

        except ValueError:
            raise  # Re-raise our own validation errors
        except Exception as exc:
            logger.error("yFinance request failed | symbol=%s | error=%s", symbol, str(exc))
            raise RuntimeError(
                f"Failed to fetch price for '{symbol}' from yFinance: {exc}"
            ) from exc

    # ── 2. Historical OHLC Data ───────────────────────────────────────────────

    def get_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> dict:
        """Routes through circuit breaker, then retries on failure."""
        return self._cb.call(self._fetch_historical_data, symbol, period, interval)

    @_stock_retry  # Retries up to 3 times on RuntimeError with exponential backoff
    def _fetch_historical_data(
        self,
        symbol: str,
        period: str = "1mo",
        interval: str = "1d",
    ) -> dict:
        """
        Fetches historical OHLC (Open, High, Low, Close) + Volume data.

        Args:
            symbol:   Stock ticker (e.g., "AAPL", "RELIANCE.NS").
            period:   Time range — "1d", "5d", "1mo", "3mo", "6mo", "1y", "5y".
            interval: Candle size — "1m", "5m", "15m", "1h", "1d", "1wk", "1mo".

        Returns:
            {
                "symbol": "AAPL",
                "period": "1mo",
                "interval": "1d",
                "currency": "USD",
                "num_candles": 22,
                "data": [
                    {
                        "date": "2026-01-15",
                        "open": 173.10,
                        "high": 175.80,
                        "low": 172.50,
                        "close": 174.90,
                        "volume": 52000000,
                    },
                    ...
                ]
            }

        Raises:
            ValueError: If the symbol has no historical data.
            RuntimeError: If yFinance request fails.
        """
        symbol = symbol.upper().strip()
        logger.info(
            "Fetching historical data | symbol=%s | period=%s | interval=%s",
            symbol, period, interval,
        )

        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)

            if df.empty:
                raise ValueError(
                    f"No historical data found for symbol '{symbol}' "
                    f"with period='{period}' and interval='{interval}'."
                )

            # Convert DataFrame rows to a clean list of dicts
            # We avoid leaking pandas types (Timestamp, float64) into the response
            records = []
            for timestamp, row in df.iterrows():
                records.append({
                    "date": timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                    "open": round(float(row.get("Open", 0)), 4),
                    "high": round(float(row.get("High", 0)), 4),
                    "low": round(float(row.get("Low", 0)), 4),
                    "close": round(float(row.get("Close", 0)), 4),
                    "volume": int(row.get("Volume", 0)),
                })

            result = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "currency": ticker.fast_info.currency if hasattr(ticker, "fast_info") else "N/A",
                "num_candles": len(records),
                "data": records,
            }
            logger.info(
                "Historical data fetched | symbol=%s | candles=%d", symbol, len(records)
            )
            return result

        except ValueError:
            raise
        except Exception as exc:
            logger.error(
                "yFinance historical request failed | symbol=%s | error=%s", symbol, str(exc)
            )
            raise RuntimeError(
                f"Failed to fetch historical data for '{symbol}': {exc}"
            ) from exc

    # ── 3. Full Stock Data (price + indicators) ───────────────────────────────

    def get_full_stock_data(self, symbol: str) -> dict:
        """
        Combines live price and technical indicators into one structured dict.

        Steps:
        1. Fetch current price via get_current_price() (circuit breaker + retry).
        2. Fetch 3-month daily history via get_historical_data().
        3. Extract close prices and run RSI(14), SMA(20), EMA(20).
        4. Merge into a flat dict ready for StockDataResponse.

        Indicators return None if history is too short to calculate.
        Never raises for missing indicators — only raises for missing price.
        """
        import pandas as pd
        from datetime import datetime, timezone
        from app.services.indicators import calculate_all

        symbol = symbol.upper().strip()
        logger.info("get_full_stock_data | symbol=%s", symbol)

        # Step 1: Live price (raises ValueError / RuntimeError on failure)
        price_data = self.get_current_price(symbol)

        # Step 2: History for indicators (silently skip if unavailable)
        indicators = {"rsi": None, "sma": None, "ema": None}
        volume = None
        try:
            hist = self.get_historical_data(symbol, period="3mo", interval="1d")
            candles = hist.get("data", [])
            if candles:
                closes = pd.Series([c["close"] for c in candles], dtype=float)
                volume = candles[-1].get("volume")  # Most recent volume
                indicators = calculate_all(closes)
        except Exception as exc:
            logger.warning(
                "Indicators skipped | symbol=%s | reason=%s", symbol, str(exc)
            )

        return {
            "symbol": price_data["symbol"],
            "current_price": price_data["price"],
            "currency": price_data.get("currency", "N/A"),
            "exchange": price_data.get("exchange", "N/A"),
            "market_state": price_data.get("market_state", "UNKNOWN"),
            "previous_close": price_data.get("previous_close"),
            "day_high": price_data.get("day_high"),
            "day_low": price_data.get("day_low"),
            "volume": volume,
            "rsi": indicators["rsi"],
            "sma": indicators["sma"],
            "ema": indicators["ema"],
            "timestamp": datetime.now(timezone.utc),
        }


# ── Module-level singleton ────────────────────────────────────────────────────
# A single shared instance for the entire app (circuit breaker state is shared).
# Routers import this: `from app.services.stock_service import stock_service`
stock_service = StockService(failure_threshold=3, recovery_timeout=30.0)


def get_circuit_status() -> dict:
    """Returns circuit breaker status — used by the /health endpoint."""
    return stock_service._cb.status()
