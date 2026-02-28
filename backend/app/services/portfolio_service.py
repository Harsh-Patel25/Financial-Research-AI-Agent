"""
Portfolio Service (services/portfolio_service.py)

Responsibilities:
- Contains ALL business logic for portfolio operations.
- Routers call this service and stay thin (no logic inside routers).
- Handles: duplicate name detection, holding upsert, transaction recording,
  holdings update on buy/sell, and negative quantity guard.

This module is database-aware but NOT FastAPI-aware.
No HTTP concepts (HTTPException, status codes) except when raised for the router.
"""

import logging
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.portfolio import Portfolio
from app.models.holding import Holding
from app.models.transaction import Transaction, TransactionType

logger = logging.getLogger(__name__)


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_portfolio_or_404(db: Session, portfolio_id: int) -> Portfolio:
    """
    Fetches a Portfolio by ID or raises HTTP 404.
    Centralizes the lookup so every endpoint uses the same error response.
    """
    portfolio = db.query(Portfolio).filter(Portfolio.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Portfolio with id={portfolio_id} not found.",
        )
    return portfolio


# ── Service Functions ─────────────────────────────────────────────────────────

def create_portfolio(db: Session, name: str) -> Portfolio:
    """
    Creates a new Portfolio row in the database.

    Raises:
        HTTPException 409: If a portfolio with the same name already exists.
    """
    # Requirement 4: Handle duplicate names safely
    existing = db.query(Portfolio).filter(Portfolio.name == name).first()
    if existing:
        logger.warning("Duplicate portfolio name attempted: '%s'", name)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A portfolio named '{name}' already exists.",
        )

    portfolio = Portfolio(name=name)
    db.add(portfolio)
    db.flush()  # Flush to get the auto-generated ID before commit
    logger.info("Portfolio created | id=%s | name='%s'", portfolio.id, portfolio.name)
    return portfolio


def add_holding(
    db: Session, portfolio_id: int, symbol: str, quantity: float, price: float
) -> Portfolio:
    """
    Adds or updates a Holding within a portfolio.

    - If a holding for this symbol already exists → update quantity and recalculate average price.
    - If it does not exist → create a new Holding row.

    Returns the parent Portfolio (for building the response).
    """
    portfolio = _get_portfolio_or_404(db, portfolio_id)

    existing_holding: Optional[Holding] = (
        db.query(Holding)
        .filter(Holding.portfolio_id == portfolio_id, Holding.symbol == symbol)
        .first()
    )

    if existing_holding:
        # Requirement 2: If holding exists, update quantity and recalculate avg price
        # Weighted average: (old_qty * old_avg + new_qty * new_price) / total_qty
        total_qty = existing_holding.quantity + quantity
        new_avg = (
            (existing_holding.quantity * existing_holding.average_price) + (quantity * price)
        ) / total_qty
        existing_holding.quantity = total_qty
        existing_holding.average_price = round(new_avg, 4)
        logger.info(
            "Holding updated | portfolio=%s | symbol=%s | qty=%s | avg_price=%s",
            portfolio_id, symbol, total_qty, new_avg,
        )
    else:
        # Requirement 3: If holding doesn't exist, create new
        new_holding = Holding(
            portfolio_id=portfolio_id,
            symbol=symbol,
            quantity=quantity,
            average_price=price,
        )
        db.add(new_holding)
        db.flush()
        logger.info(
            "Holding created | portfolio=%s | symbol=%s | qty=%s",
            portfolio_id, symbol, quantity,
        )

    return portfolio


def record_transaction(
    db: Session,
    portfolio_id: int,
    symbol: str,
    transaction_type: str,
    quantity: float,
    price: float,
) -> Transaction:
    """
    Records a buy or sell transaction and updates the corresponding holding.

    Buy  → increases holding quantity, recalculates average price.
    Sell → decreases holding quantity.

    Raises:
        HTTPException 422: If a SELL would result in negative quantity (oversell).
    """
    portfolio = _get_portfolio_or_404(db, portfolio_id)

    txn_enum = TransactionType(transaction_type)  # validated by schema already

    existing_holding: Optional[Holding] = (
        db.query(Holding)
        .filter(Holding.portfolio_id == portfolio_id, Holding.symbol == symbol)
        .first()
    )

    if txn_enum == TransactionType.BUY:
        # BUY → upsert holding
        if existing_holding:
            total_qty = existing_holding.quantity + quantity
            new_avg = (
                (existing_holding.quantity * existing_holding.average_price) + (quantity * price)
            ) / total_qty
            existing_holding.quantity = total_qty
            existing_holding.average_price = round(new_avg, 4)
        else:
            db.add(Holding(
                portfolio_id=portfolio_id,
                symbol=symbol,
                quantity=quantity,
                average_price=price,
            ))

    elif txn_enum == TransactionType.SELL:
        # Requirement 4: Handle negative quantity edge case
        if not existing_holding or existing_holding.quantity < quantity:
            available = existing_holding.quantity if existing_holding else 0
            logger.warning(
                "Oversell attempted | portfolio=%s | symbol=%s | sell=%s | held=%s",
                portfolio_id, symbol, quantity, available,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=(
                    f"Cannot sell {quantity} shares of {symbol}. "
                    f"Only {available} shares available."
                ),
            )
        existing_holding.quantity -= quantity
        # If quantity reaches 0, keep the record (audit trail stays intact)

    # Insert the immutable transaction record
    txn = Transaction(
        portfolio_id=portfolio_id,
        symbol=symbol,
        transaction_type=txn_enum,
        quantity=quantity,
        price=price,
    )
    db.add(txn)
    db.flush()

    logger.info(
        "Transaction recorded | id=%s | portfolio=%s | type=%s | symbol=%s | qty=%s | price=%s",
        txn.id, portfolio_id, transaction_type, symbol, quantity, price,
    )
    return txn


def get_portfolio_summary(db: Session, portfolio_id: int) -> dict:
    """
    Aggregates portfolio data for the summary endpoint.

    Calculates:
    1. total_holdings: Number of distinct stock positions in the portfolio.
    2. total_invested: Sum of (quantity × average_price) for every holding.
    3. market_value: Placeholder — returns None until Stock Service (Task 3)
                     provides real-time prices to calculate current market value.

    Returns a plain dict that the router maps into PortfolioSummaryResponse.
    """
    portfolio = _get_portfolio_or_404(db, portfolio_id)

    holdings = portfolio.holdings  # ORM loads via relationship

    # Requirement 1: Aggregate holdings
    total_holdings = len(holdings)

    # Requirement 2: Calculate total invested amount
    total_invested = round(
        sum(h.quantity * h.average_price for h in holdings), 2
    )

    # Requirement 3: Market value — placeholder for now (Task 3 will fill this)
    market_value = None  # Will be: sum(h.quantity * live_price) once StockService exists

    logger.info(
        "Portfolio summary fetched | id=%s | holdings=%s | invested=%.2f",
        portfolio_id, total_holdings, total_invested,
    )

    return {
        "id": portfolio.id,
        "name": portfolio.name,
        "created_at": portfolio.created_at,
        "total_holdings": total_holdings,
        "total_invested": total_invested,
        "market_value": market_value,
        "holdings": [
            {
                "symbol": h.symbol,
                "quantity": h.quantity,
                "average_price": h.average_price,
                "total_invested": round(h.quantity * h.average_price, 2),
            }
            for h in holdings
        ],
    }
