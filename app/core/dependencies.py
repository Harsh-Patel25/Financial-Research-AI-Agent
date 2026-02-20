"""
FastAPI Dependency Injection Layer (dependencies.py)

Responsibilities:
1. Provide `get_db()` — a generator dependency that yields a SQLAlchemy session.
2. Guarantee the session is always closed after the request lifecycle ends.
3. Keep dependency logic isolated from business logic and route handlers.

Usage in a route:
    from app.core.dependencies import get_db

    @router.get("/example")
    def example(db: Session = Depends(get_db)):
        ...

Design decisions:
- Uses `try / finally` to ensure the session always closes, even on exceptions.
- No commit/rollback is performed here — that responsibility belongs to the
  service layer to maintain proper transaction boundaries.
- Kept framework-aware (FastAPI) but logically decoupled from business code.
"""

import logging
from typing import Generator

from sqlalchemy.orm import Session

from app.core.database import SessionLocal

logger = logging.getLogger(__name__)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency that provides a SQLAlchemy database session.

    Yields a session bound to the current request.
    Closes the session in the `finally` block to prevent connection leaks,
    regardless of whether the request succeeded or raised an exception.
    """
    db: Session = SessionLocal()
    logger.debug("DB session opened")
    try:
        yield db
    finally:
        db.close()
        logger.debug("DB session closed")
