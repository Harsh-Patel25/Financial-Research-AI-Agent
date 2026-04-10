"""
Transaction Model (transaction.py)

Responsibilities:
1. Records every individual buy or sell event for a stock symbol inside a portfolio.
2. Acts as an immutable audit trail — transactions should never be updated, only appended.
3. Linked to a parent Portfolio via a foreign key.
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Enum as SAEnum, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from ..core.database import Base

# TYPE_CHECKING guard — prevents circular import at runtime.
if TYPE_CHECKING:
    from .portfolio import Portfolio


class TransactionType(str, enum.Enum):
    """
    Enumeration for allowed transaction types.

    Inherits from `str` so it serializes cleanly to JSON as a plain string
    (e.g., "buy" / "sell") without extra conversion.

    Why Enum and not a plain string?
    - Prevents invalid values like "BUY", "Buy", "purchase" from being stored.
    - The DB-level Enum column also enforces this constraint at the database.
    - Makes intent clear and IDE-autocomplete-friendly.
    """
    BUY = "buy"
    SELL = "sell"


class Transaction(Base):
    """
    SQLAlchemy model for the 'transactions' table.

    A Transaction is an immutable record of a single buy or sell event.
    It should never be updated — only inserted and read.

    Fields:
    - id: Primary key (auto-incremented Integer).
    - portfolio_id: FK referencing portfolios.id.
    - symbol: Stock ticker (e.g., 'TSLA'), indexed for fast lookups.
    - transaction_type: Enum restricted to 'buy' or 'sell'.
    - quantity: Number of shares involved in this transaction (float).
    - price: The per-share price at the time of the transaction (float).
    - timestamp: Auto-set by the DB server at insert time.
    """
    __tablename__ = "transactions"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ────────────────────────────────────────────────────────
    # ondelete="CASCADE" → Database deletes all transactions if the parent
    # Portfolio row is deleted. Enforces referential integrity at DB level.
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,  # indexed for "show all AAPL transactions" type queries
    )

    # ── Enum Column ────────────────────────────────────────────────────────
    # SAEnum maps the Python TransactionType enum to a DB-level ENUM type.
    # The DB will REJECT any value not in ('buy', 'sell') — hard constraint.
    transaction_type: Mapped[TransactionType] = mapped_column(
        SAEnum(TransactionType, name="transaction_type_enum", create_type=True),
        nullable=False,
    )

    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)

    # ── Auto Timestamp ─────────────────────────────────────────────────────
    # server_default=func.now() → The DB server sets this at INSERT time.
    # This is more reliable than setting it in Python, because DB time is
    # consistent even across multiple app servers or timezone differences.
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── ORM Relationship ───────────────────────────────────────────────────
    portfolio: Mapped["Portfolio"] = relationship(
        "app.models.portfolio.Portfolio",
        back_populates="transactions",
    )

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, symbol='{self.symbol}', "
            f"type={self.transaction_type.value}, qty={self.quantity}, "
            f"price={self.price})>"
        )
