"""
Holding Model (holding.py)

Responsibilities:
1. Represents a single stock position inside a portfolio.
2. Stores the stock symbol, number of shares, and average buy price.
3. Linked to a parent Portfolio via a foreign key.

Relationships:
- Many Holdings → One Portfolio (many-to-one).
- Cascade: If a Portfolio is deleted, all its Holdings are deleted automatically.
"""

from sqlalchemy import String, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from app.core.database import Base

# TYPE_CHECKING guard prevents circular imports at runtime.
# The import is only resolved by mypy / IDEs for type hints.
if TYPE_CHECKING:
    from app.models.portfolio import Portfolio


class Holding(Base):
    """
    SQLAlchemy model for the 'holdings' table.

    A Holding represents how many shares of a single stock symbol
    a portfolio currently owns, and at what average cost.

    Fields:
    - id: Primary key (Integer, auto-incremented).
    - portfolio_id: Foreign key referencing portfolios.id.
    - symbol: Stock ticker (e.g., 'AAPL'), indexed for fast lookups.
    - quantity: Number of shares held (supports fractional shares).
    - average_price: The average cost per share across all buy transactions.
    """
    __tablename__ = "holdings"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)

    # ── Foreign Key ────────────────────────────────────────────────────────
    # ondelete="CASCADE" → If the parent Portfolio row is deleted from the DB,
    # all child Holding rows for that portfolio are automatically deleted.
    # This enforces referential integrity at the DATABASE level.
    portfolio_id: Mapped[int] = mapped_column(
        ForeignKey("portfolios.id", ondelete="CASCADE"),
        nullable=False,
        index=True,  # indexed for fast joins when fetching all holdings for a portfolio
    )

    symbol: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,  # indexed for fast lookups like "find all portfolios holding AAPL"
    )
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    average_price: Mapped[float] = mapped_column(Float, nullable=False)

    # ── ORM Relationship ───────────────────────────────────────────────────
    # `back_populates="holdings"` wires this side of the relationship to the
    # `holdings` attribute on the Portfolio model (defined in portfolio.py).
    # cascade="all, delete-orphan" → If a Portfolio object is deleted in Python
    # (in-session), SQLAlchemy will also delete its Holding objects.
    # This is the ORM-level mirror of the DB-level ondelete="CASCADE".
    portfolio: Mapped["Portfolio"] = relationship(
        "Portfolio",
        back_populates="holdings",
    )

    def __repr__(self) -> str:
        return (
            f"<Holding(id={self.id}, symbol='{self.symbol}', "
            f"qty={self.quantity}, avg_price={self.average_price})>"
        )
