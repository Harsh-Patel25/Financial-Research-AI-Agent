"""
Stock Schemas (schemas/stock.py)

Pydantic request/response contracts for stock-related endpoints.
All technical indicator fields are Optional — they are None if the
historical data has insufficient candles to calculate the indicator.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class StockDataResponse(BaseModel):
    """
    Structured JSON response for a full stock data query.

    Aggregates real-time price data (from StockService) with
    technical indicators (from indicators.py) into one clean object.

    Fields:
        symbol          Stock ticker (e.g., "AAPL", "RELIANCE.NS")
        current_price   Latest market price
        currency        Currency of the price (e.g., "USD", "INR")
        exchange        Exchange name (e.g., "NMS", "NSE")
        market_state    "REGULAR" | "PRE" | "POST" | "CLOSED" | "UNKNOWN"
        previous_close  Previous day's closing price
        day_high        Intraday high
        day_low         Intraday low
        volume          Trading volume (None if not available at time of fetch)
        rsi             RSI(14) — None if < 15 historical candles available
        sma             SMA(20) — None if < 20 historical candles available
        ema             EMA(20) — None if < 20 historical candles available
        timestamp       UTC datetime when this response was generated
    """

    symbol: str
    current_price: float = Field(..., gt=0)
    currency: str = "N/A"
    exchange: str = "N/A"
    market_state: str = "UNKNOWN"
    previous_close: Optional[float] = None
    day_high: Optional[float] = None
    day_low: Optional[float] = None
    volume: Optional[int] = None
    rsi: Optional[float] = Field(None, ge=0, le=100)
    sma: Optional[float] = None
    ema: Optional[float] = None
    timestamp: datetime

    model_config = {"from_attributes": True}
