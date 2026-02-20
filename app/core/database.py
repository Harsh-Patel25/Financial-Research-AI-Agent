"""
Database Engine & Session Configuration (database.py)

Responsibilities:
1. Create the SQLAlchemy engine using the DATABASE_URL from settings.
2. Configure SessionLocal — the session factory for all DB operations.
3. Expose Base — the shared DeclarativeBase for all future ORM models.

Design decisions:
- SQLite is used for development (file-based, zero-config).
- `check_same_thread=False` is required for SQLite + FastAPI threading model.
- `autocommit=False` + `autoflush=False` gives explicit transaction control.
- This module has NO FastAPI imports — it is framework-agnostic and reusable.

Do NOT place business logic here.
"""

import logging
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Engine ────────────────────────────────────────────────────────────────────
# `connect_args` is only needed for SQLite (disables same-thread check).
# For PostgreSQL in production, this kwarg is simply ignored via the condition.
_connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(
    settings.database_url,
    connect_args=_connect_args,
    echo=settings.debug,           # logs all SQL when debug=True
    future=True,                   # use SQLAlchemy 2.x-style API
)

logger.info("Database engine created | url=%s", settings.database_url)

# ── Session Factory ───────────────────────────────────────────────────────────
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,   # explicit commit required — safer for transactional ops
    autoflush=False,    # flush manually to avoid unintended DB writes mid-request
)

# ── Declarative Base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """
    Shared base class for all ORM models.

    All future models must inherit from this Base so that
    `Base.metadata.create_all(engine)` can discover and create their tables.
    """
    pass
