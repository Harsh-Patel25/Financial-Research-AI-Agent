"""
Portfolio Model (portfolio.py)

Responsibilities:
1. Stores top-level metadata about a user's portfolio.
2. Acts as the parent entity for Holdings and Transactions.
"""

from datetime import datetime
from typing import TYPE_CHECKING, List
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.holding import Holding
    from app.models.transaction import Transaction


class Portfolio(Base):
    """
    SQLAlchemy model for the 'portfolios' table.

    Fields:
    - id: Primary key (Integer, auto-incremented).
    - name: Unique name for the portfolio (Indexed for fast lookups).
    - created_at: Timestamp auto-set by the database server.

    Relationships:
    - holdings: List of Holding objects belonging to this portfolio.
                cascade='all, delete-orphan' means if this Portfolio object
                is deleted in a session, all related Holding objects are
                also deleted automatically (ORM-level cascade).
    """
    __tablename__ = "portfolios"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── ORM Relationship ───────────────────────────────────────────────────
    # One Portfolio → Many Holdings
    # `back_populates="portfolio"` links to the `portfolio` attribute in Holding.
    # `cascade="all, delete-orphan"` → deleting a Portfolio in Python also
    # deletes all its child Holdings from the session.
    holdings: Mapped[List["Holding"]] = relationship(
        "Holding",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )

    # One Portfolio → Many Transactions (immutable audit trail)
    # cascade="all, delete-orphan" → deleting a Portfolio removes its transactions
    transactions: Mapped[List["Transaction"]] = relationship(
        "Transaction",
        back_populates="portfolio",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Portfolio(id={self.id}, name='{self.name}')>"
