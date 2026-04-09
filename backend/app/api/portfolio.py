"""
Portfolio Router (api/portfolio.py)

Responsibilities:
- Define HTTP endpoints for portfolio operations.
- Validate requests via Pydantic schemas.
- Delegate ALL business logic to portfolio_service.
- Return structured JSON responses.

This router is THIN — no business logic lives here.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from ..core.dependencies import get_db
from ..schemas.portfolio import (
    CreatePortfolioRequest,
    AddHoldingRequest,
    RecordTransactionRequest,
    PortfolioResponse,
    PortfolioSummaryResponse,
    TransactionResponse,
    HoldingSummary,
)
from ..services import portfolio_service
from ..services.mpt_service import optimize_portfolio

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolios", tags=["portfolio"])


# ── 1. Create Portfolio ───────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=List[PortfolioResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all portfolios",
)
def get_all_portfolios(db: Session = Depends(get_db)) -> List[PortfolioResponse]:
    """
    Returns a list of all portfolios.
    """
    logger.info("GET /portfolios")
    portfolios = portfolio_service.get_all_portfolios(db=db)
    return [_build_portfolio_response(p) for p in portfolios]


@router.post(
    "/",
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new portfolio",
)
def create_portfolio(
    payload: CreatePortfolioRequest,
    db: Session = Depends(get_db),
) -> PortfolioResponse:
    """
    Creates a new portfolio with the given name.
    Returns 409 Conflict if the name already exists.
    """
    logger.info("POST /portfolios | name='%s'", payload.name)
    portfolio = portfolio_service.create_portfolio(db=db, name=payload.name)
    return _build_portfolio_response(portfolio)


# ── 2. Add Holding ────────────────────────────────────────────────────────────

@router.post(
    "/{portfolio_id}/holdings",
    response_model=PortfolioResponse,
    status_code=status.HTTP_200_OK,
    summary="Add or update a holding in a portfolio",
)
def add_holding(
    portfolio_id: int,
    payload: AddHoldingRequest,
    db: Session = Depends(get_db),
) -> PortfolioResponse:
    """
    Adds a new holding or updates quantity + average price if the symbol exists.
    Returns the full updated portfolio summary.
    Returns 404 if the portfolio doesn't exist.
    """
    logger.info(
        "POST /portfolios/%s/holdings | symbol=%s | qty=%s",
        portfolio_id, payload.symbol, payload.quantity,
    )
    portfolio = portfolio_service.add_holding(
        db=db,
        portfolio_id=portfolio_id,
        symbol=payload.symbol,
        quantity=payload.quantity,
        price=payload.price,
    )
    return _build_portfolio_response(portfolio)


# ── 3. Record Transaction ─────────────────────────────────────────────────────

@router.post(
    "/{portfolio_id}/transactions",
    response_model=TransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record a buy or sell transaction",
)
def record_transaction(
    portfolio_id: int,
    payload: RecordTransactionRequest,
    db: Session = Depends(get_db),
) -> TransactionResponse:
    """
    Records a buy or sell transaction.
    For BUY: adds to or creates the holding.
    For SELL: reduces the holding quantity. Returns 422 if overselling.
    Returns 404 if the portfolio doesn't exist.
    """
    logger.info(
        "POST /portfolios/%s/transactions | type=%s | symbol=%s | qty=%s",
        portfolio_id, payload.transaction_type, payload.symbol, payload.quantity,
    )
    txn = portfolio_service.record_transaction(
        db=db,
        portfolio_id=portfolio_id,
        symbol=payload.symbol,
        transaction_type=payload.transaction_type,
        quantity=payload.quantity,
        price=payload.price,
    )
    return TransactionResponse(
        id=txn.id,
        portfolio_id=txn.portfolio_id,
        symbol=txn.symbol,
        transaction_type=txn.transaction_type.value,
        quantity=txn.quantity,
        price=txn.price,
        timestamp=txn.timestamp,
    )


# ── Response Builder ──────────────────────────────────────────────────────────

def _build_portfolio_response(portfolio) -> PortfolioResponse:
    """
    Constructs a PortfolioResponse from a Portfolio ORM object.
    Kept here to avoid leaking response-building logic into the service.
    """
    holdings = [
        HoldingSummary(
            symbol=h.symbol,
            quantity=h.quantity,
            average_price=h.average_price,
            total_invested=round(h.quantity * h.average_price, 2),
        )
        for h in portfolio.holdings
    ]
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        created_at=portfolio.created_at,
        holdings=holdings,
    )


# ── 4. Portfolio Summary ──────────────────────────────────────────────────────────

@router.get(
    "/{portfolio_id}/summary",
    response_model=PortfolioSummaryResponse,
    status_code=200,
    summary="Fetch aggregated portfolio summary",
)
def get_portfolio_summary(
    portfolio_id: int,
    db: Session = Depends(get_db),
) -> PortfolioSummaryResponse:
    """
    Returns an aggregated summary of the portfolio:
    - All holdings with per-holding totals.
    - total_invested: Sum of cost basis across all positions.
    - total_holdings: Number of distinct stock positions.
    - market_value: None (placeholder until Stock Service is integrated in Task 3).

    Returns 404 if the portfolio doesn't exist.
    """
    logger.info("GET /portfolios/%s/summary", portfolio_id)
    data = portfolio_service.get_portfolio_summary(db=db, portfolio_id=portfolio_id)
    return PortfolioSummaryResponse(**data)

# ── 5. Optimize Portfolio (MPT) ──────────────────────────────────────────────────

@router.get(
    "/{portfolio_id}/optimize",
    status_code=200,
    summary="Optimize portfolio weights using Modern Portfolio Theory",
)
def optimize_user_portfolio(
    portfolio_id: int,
    db: Session = Depends(get_db),
):
    logger.info("GET /portfolios/%s/optimize", portfolio_id)
    portfolio = portfolio_service._get_portfolio_or_404(db, portfolio_id)
    
    symbols = [h.symbol for h in portfolio.holdings if h.quantity > 0]
    if len(symbols) < 2:
        return {"status": "error", "message": "At least 2 active holdings required to optimize."}
        
    return optimize_portfolio(symbols)

