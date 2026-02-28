"""
FastAPI Dependency Injection Layer (dependencies.py)

Responsibilities:
1. Provide get_db() — a generator dependency that yields a SQLAlchemy session.
2. Commit the session transaction when the route completes successfully.
3. Rollback the session transaction if any exception occurs mid-request.
4. Guarantee the session is always closed after the request lifecycle ends.
5. Keep all transaction management here — route handlers stay business-logic-only.

Usage in a route:
    from fastapi import Depends
    from sqlalchemy.orm import Session
    from app.core.dependencies import get_db

    @router.post("/portfolios")
    def create_portfolio(db: Session = Depends(get_db)):
        # db is already open
        # If this function returns normally → get_db() commits
        # If this function raises an exception → get_db() rolls back
        ...

Design decisions:
- `try / except / finally` pattern is the industry standard for safe DB sessions.
- Commit happens INSIDE the dependency (not the route) so every route
  automatically gets atomic transaction behavior without writing boilerplate.
- Rollback is triggered by ANY exception — including HTTP exceptions raised by
  FastAPI (e.g., HTTPException 404) and SQLAlchemy integrity errors.
- Session closes in `finally` → zero connection leaks, even on crashes.
- No business logic here — this file only manages lifecycle.
"""

import logging
from typing import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy session with full transaction management.

    Transaction lifecycle:
    1. Open  → SessionLocal() creates a new session bound to the engine.
    2. Yield → The session is given to the route handler for use.
    3. Commit → If the route returns normally, all pending changes are committed.
    4. Rollback → If ANY exception is raised (HTTP or DB), all changes are undone.
    5. Close  → The session is always closed to release the DB connection.

    Example behaviour:
        Route inserts 3 rows → route raises HTTPException(404)
        → get_db() catches exception → rollback() → 0 rows inserted
        → DB remains consistent.
    """
    db: Session = SessionLocal()
    logger.debug("DB session opened")
    try:
        yield db
        # ── Commit ────────────────────────────────────────────────────────
        # Reached only if the route handler completed WITHOUT raising an error.
        # Flushes all pending ORM changes to the DB and makes them permanent.
        db.commit()
        logger.debug("DB session committed")
    except Exception as exc:
        # ── Rollback ──────────────────────────────────────────────────────
        # Triggered by ANY exception: DB IntegrityError, HTTPException, etc.
        # Undoes all changes made in this session since the last commit.
        # This prevents partial writes from corrupting the database.
        db.rollback()
        logger.warning("DB session rolled back | reason: %s", str(exc))
        raise  # Re-raise so FastAPI's exception handlers still process it
    finally:
        # ── Close ─────────────────────────────────────────────────────────
        # Always runs — success or failure.
        # Returns the connection back to the connection pool.
        # Prevents connection exhaustion under high load.
        db.close()
        logger.debug("DB session closed")
