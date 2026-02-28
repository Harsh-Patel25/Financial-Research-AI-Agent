"""
Portfolio Pydantic Schemas (schemas/portfolio.py)

Responsibilities:
- Define request bodies (input validation).
- Define response shapes (output contracts).
- Keep all data validation rules here, not in routers or services.
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# ── Request Schemas ───────────────────────────────────────────────────────────

class CreatePortfolioRequest(BaseModel):
    """Request body for POST /portfolios — creates a new portfolio."""
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Unique name for the portfolio",
        examples=["My NIFTY50 Portfolio"],
    )


class AddHoldingRequest(BaseModel):
    """Request body for POST /portfolios/{portfolio_id}/holdings."""
    symbol: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="Stock ticker symbol (e.g., AAPL, RELIANCE)",
        examples=["AAPL"],
    )
    quantity: float = Field(..., gt=0, description="Number of shares to add (must be > 0)")
    price: float = Field(..., gt=0, description="Per-share price at time of purchase")

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        """Normalize symbol to uppercase for consistency."""
        return v.upper().strip()


class RecordTransactionRequest(BaseModel):
    """Request body for POST /portfolios/{portfolio_id}/transactions."""
    symbol: str = Field(..., min_length=1, max_length=20, examples=["TSLA"])
    transaction_type: str = Field(
        ...,
        pattern="^(buy|sell)$",
        description="Must be exactly 'buy' or 'sell' (lowercase)",
        examples=["buy"],
    )
    quantity: float = Field(..., gt=0, description="Number of shares (must be > 0)")
    price: float = Field(..., gt=0, description="Per-share price at time of transaction")

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v: str) -> str:
        return v.upper().strip()

    @field_validator("transaction_type")
    @classmethod
    def lowercase_type(cls, v: str) -> str:
        return v.lower().strip()


# ── Response Schemas ──────────────────────────────────────────────────────────

class HoldingSummary(BaseModel):
    """A single holding entry in the portfolio summary."""
    symbol: str
    quantity: float
    average_price: float
    total_invested: float

    model_config = {"from_attributes": True}


class PortfolioResponse(BaseModel):
    """Structured JSON response for portfolio operations."""
    id: int
    name: str
    created_at: datetime
    holdings: List[HoldingSummary] = []

    model_config = {"from_attributes": True}


class PortfolioSummaryResponse(BaseModel):
    """
    Aggregated portfolio summary response.

    Includes:
    - All holdings with per-holding totals.
    - total_invested: Sum of (quantity × average_price) across all holdings.
    - total_holdings: Count of distinct stock positions.
    - market_value: Placeholder (None until Stock Service is integrated in Task 3).
    """
    id: int
    name: str
    created_at: datetime
    total_holdings: int
    total_invested: float
    market_value: Optional[float] = None  # Placeholder — populated by Stock Service (Task 3)
    holdings: List[HoldingSummary] = []

    model_config = {"from_attributes": True}


class TransactionResponse(BaseModel):
    """Structured JSON response for a recorded transaction."""
    id: int
    portfolio_id: int
    symbol: str
    transaction_type: str
    quantity: float
    price: float
    timestamp: datetime

    model_config = {"from_attributes": True}
