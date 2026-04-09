"""
Database Engine & Session Configuration (database.py)

Responsibilities:
1. Create the SQLAlchemy engine using the DATABASE_URL from settings.
2. Configure SessionLocal — the session factory for all DB operations.
3. Expose Base — the shared DeclarativeBase for all future ORM models.
4. Validate DB connection on startup via validate_db_connection().

Switching between SQLite (dev) and PostgreSQL (prod):
- Dev  → DATABASE_URL=sqlite:///./financial_ai.db        (default in .env)
- Prod → DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname

Design decisions:
- SQLite check_same_thread=False is applied only when driver is sqlite.
- autocommit=False + autoflush=False gives explicit transaction control.
- This module has NO FastAPI imports — it is framework-agnostic and reusable.

Do NOT place business logic here.
"""

import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import settings

logger = logging.getLogger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────
# `connect_args` is only needed for SQLite (disables the same-thread check).
# For PostgreSQL the condition evaluates to {} — no extra args needed.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=settings.debug,   # prints all generated SQL when DEBUG=True
    future=True,           # enables SQLAlchemy 2.x style API
)

logger.info("Database engine created | url=%s", settings.database_url)

# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,  # explicit commit required — safer for transactions
    autoflush=False,   # manual flush avoids unintended mid-request DB writes
)


# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Shared base class for all ORM models.

    All future models must inherit from this Base so that
    Base.metadata.create_all(engine) can discover and create their tables.
    """
    pass


# ── Startup DB Validation ─────────────────────────────────────────────────────
def validate_db_connection() -> None:
    """
    Validate the database connection on application startup.

    Runs a lightweight SELECT 1 query to confirm the DB is reachable.

    Works for both SQLite and PostgreSQL — no business logic involved.

    Why this matters:
    - Catches wrong DATABASE_URL before the first user request.
    - For PostgreSQL: verifies host, port, credentials and network access.
    - Implements the fail-fast principle — better to crash at startup than
      silently fail mid-request.

    Raises:
        Exception: Any SQLAlchemy / driver error is re-raised so FastAPI's
                   startup event can log it clearly and stop the process.
    """
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info(
            "✅ Database connection validated | url=%s", settings.database_url
        )
    except Exception as exc:
        logger.critical(
            "❌ Database connection FAILED | url=%s | error=%s",
            settings.database_url,
            str(exc),
        )
        raise
