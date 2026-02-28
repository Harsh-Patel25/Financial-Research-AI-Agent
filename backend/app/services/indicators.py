"""
Technical Indicators (services/indicators.py)

Pure calculation functions — no API calls, no DB access, no FastAPI.
Input: pandas Series (close prices). Output: float.

These can be unit-tested with synthetic data without any external dependencies.
"""

from typing import Union
import pandas as pd


PriceSeries = Union[pd.Series, list]


def _to_series(prices: PriceSeries) -> pd.Series:
    """Converts list or Series to a clean float Series for calculations."""
    if isinstance(prices, list):
        return pd.Series(prices, dtype=float)
    return prices.astype(float)


# ── RSI ───────────────────────────────────────────────────────────────────────

def calculate_rsi(prices: PriceSeries, period: int = 14) -> float:
    """
    Relative Strength Index (RSI) using Wilder's Exponential Smoothing.

    Formula:
        RSI = 100 - (100 / (1 + RS))
        RS  = Average Gain / Average Loss over `period` candles

    Args:
        prices: Close price series (oldest → newest). Minimum length = period + 1.
        period: Lookback window. Standard = 14.

    Returns:
        RSI value in range [0, 100]. Rounded to 2 decimal places.

    Raises:
        ValueError: If not enough data points for the requested period.
    """
    series = _to_series(prices)

    if len(series) < period + 1:
        raise ValueError(
            f"RSI requires at least {period + 1} data points. Got {len(series)}."
        )

    delta = series.diff().dropna()
    gains = delta.clip(lower=0)
    losses = -delta.clip(upper=0)

    # Wilder's smoothing (EWM with alpha = 1/period, adjust=False)
    avg_gain = gains.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]
    avg_loss = losses.ewm(alpha=1 / period, adjust=False).mean().iloc[-1]

    if avg_loss == 0:
        return 100.0  # No losses → fully overbought

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi), 2)


# ── SMA ───────────────────────────────────────────────────────────────────────

def calculate_sma(prices: PriceSeries, period: int = 20) -> float:
    """
    Simple Moving Average — arithmetic mean of the last `period` prices.

    Args:
        prices: Close price series. Minimum length = period.
        period: Lookback window. Standard = 20.

    Returns:
        Latest SMA value. Rounded to 4 decimal places.

    Raises:
        ValueError: If not enough data points.
    """
    series = _to_series(prices)

    if len(series) < period:
        raise ValueError(
            f"SMA({period}) requires at least {period} data points. Got {len(series)}."
        )

    sma = series.rolling(window=period).mean().iloc[-1]
    return round(float(sma), 4)


# ── EMA ───────────────────────────────────────────────────────────────────────

def calculate_ema(prices: PriceSeries, period: int = 20) -> float:
    """
    Exponential Moving Average — weights recent prices more heavily.

    Uses pandas EWM with span=period and adjust=False (standard brokers use this).

    Args:
        prices: Close price series. Minimum length = period.
        period: Lookback window. Standard = 20.

    Returns:
        Latest EMA value. Rounded to 4 decimal places.

    Raises:
        ValueError: If not enough data points.
    """
    series = _to_series(prices)

    if len(series) < period:
        raise ValueError(
            f"EMA({period}) requires at least {period} data points. Got {len(series)}."
        )

    ema = series.ewm(span=period, adjust=False).mean().iloc[-1]
    return round(float(ema), 4)


# ── Composite Helper ──────────────────────────────────────────────────────────

def calculate_all(
    prices: PriceSeries,
    rsi_period: int = 14,
    sma_period: int = 20,
    ema_period: int = 20,
) -> dict:
    """
    Calculates RSI, SMA, and EMA in one call.

    Returns a dict with keys: rsi, sma, ema.
    Returns None for any indicator if there is insufficient data (no exception raised).
    """
    series = _to_series(prices)

    def _safe(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ValueError:
            return None

    return {
        "rsi": _safe(calculate_rsi, series, rsi_period),
        "sma": _safe(calculate_sma, series, sma_period),
        "ema": _safe(calculate_ema, series, ema_period),
    }
