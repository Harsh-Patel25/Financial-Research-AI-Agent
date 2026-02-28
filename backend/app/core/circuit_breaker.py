"""
Circuit Breaker (core/circuit_breaker.py)

Implements the classic 3-state Circuit Breaker pattern to protect the application
from cascading failures when external APIs (like yFinance) are unavailable.

States:
    CLOSED   → Normal operation. Calls pass through.
    OPEN     → API is unhealthy. All calls are blocked immediately (no network hit).
    HALF_OPEN → Recovery probe. One test call is allowed through.
                If it succeeds → back to CLOSED.
                If it fails    → back to OPEN.

Flow diagram:
    CLOSED ──(threshold failures)──► OPEN ──(recovery_timeout expires)──► HALF_OPEN
       ▲                                                                        │
       └───────────────────(probe succeeds)──────────────────────────────────── ┘
"""

import logging
import threading
import time
from enum import Enum
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class CircuitState(str, Enum):
    CLOSED = "CLOSED"       # Normal — calls pass through
    OPEN = "OPEN"           # Tripped — calls blocked
    HALF_OPEN = "HALF_OPEN" # Recovery — one probe allowed


class CircuitBreakerOpenError(RuntimeError):
    """
    Raised when a call is attempted while the circuit is OPEN.
    Routers should catch this and return a 503 Service Unavailable.
    """
    pass


class CircuitBreaker:
    """
    Thread-safe circuit breaker that wraps any callable.

    Args:
        name:             Identifier for logging (e.g., "yfinance").
        failure_threshold: Consecutive failures before opening (default: 3).
        recovery_timeout:  Seconds to wait before testing recovery (default: 30).
        fallback:          Optional callable returning a fallback value when OPEN.
                           If None, raises CircuitBreakerOpenError.

    Usage:
        cb = CircuitBreaker(name="yfinance", failure_threshold=3, recovery_timeout=30)
        result = cb.call(stock_service.get_current_price, "AAPL")
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
        fallback: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.fallback = fallback

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: Optional[float] = None
        self._lock = threading.Lock()  # Thread-safe state transitions

    # ── State Properties ──────────────────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    # ── Core Call Wrapper ─────────────────────────────────────────────────────

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Executes `func(*args, **kwargs)` through the circuit breaker.

        - CLOSED:    Calls func. On failure, increments counter.
                     If counter hits threshold → trips to OPEN.
        - OPEN:      Checks if recovery_timeout has elapsed.
                     If yes → transitions to HALF_OPEN and allows one probe call.
                     If no  → raises CircuitBreakerOpenError (or calls fallback).
        - HALF_OPEN: Allows one probe call.
                     Success → resets to CLOSED.
                     Failure → returns to OPEN (resets timer).

        Args:
            func: The callable to protect (e.g., stock_service.get_current_price).
            *args, **kwargs: Forwarded to func.

        Returns:
            Result of func, or fallback value if circuit is OPEN.

        Raises:
            CircuitBreakerOpenError: If OPEN and no fallback is defined.
        """
        with self._lock:
            if self._state == CircuitState.OPEN:
                elapsed = time.monotonic() - (self._last_failure_time or 0)
                if elapsed >= self.recovery_timeout:
                    # Enough time has passed — allow one probe call
                    self._transition(CircuitState.HALF_OPEN)
                else:
                    # Still OPEN — block the call
                    remaining = round(self.recovery_timeout - elapsed, 1)
                    logger.warning(
                        "Circuit OPEN | name=%s | blocking call | retry_in=%.1fs",
                        self.name, remaining,
                    )
                    if self.fallback:
                        return self.fallback(*args, **kwargs)
                    raise CircuitBreakerOpenError(
                        f"Circuit breaker '{self.name}' is OPEN. "
                        f"Service unavailable. Retry in {remaining}s."
                    )

        # ── Execute the call (outside the lock to avoid deadlock) ─────────────
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except Exception as exc:
            self._on_failure(exc)
            raise

    # ── State Transition Handlers ─────────────────────────────────────────────

    def _on_success(self) -> None:
        """Called when a call succeeds. Resets failures and closes the circuit."""
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                logger.info(
                    "Circuit CLOSED (recovered) | name=%s | probe succeeded", self.name
                )
            elif self._failure_count > 0:
                logger.debug("Circuit CLOSED | name=%s | resetting failure count", self.name)
            self._failure_count = 0
            self._last_failure_time = None
            self._state = CircuitState.CLOSED

    def _on_failure(self, exc: Exception) -> None:
        """Called when a call fails. Increments counter, trips to OPEN if threshold hit."""
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed — snap back to OPEN immediately
                logger.warning(
                    "Circuit OPEN (probe failed) | name=%s | error=%s",
                    self.name, str(exc),
                )
                self._transition(CircuitState.OPEN)

            elif self._failure_count >= self.failure_threshold:
                logger.error(
                    "Circuit OPEN (threshold hit) | name=%s | failures=%d | error=%s",
                    self.name, self._failure_count, str(exc),
                )
                self._transition(CircuitState.OPEN)
            else:
                logger.warning(
                    "Circuit CLOSED (warning) | name=%s | failures=%d/%d | error=%s",
                    self.name, self._failure_count, self.failure_threshold, str(exc),
                )

    def _transition(self, new_state: CircuitState) -> None:
        """Internal state transition with logging. Assumes lock is held."""
        old_state = self._state
        self._state = new_state
        logger.info(
            "Circuit state change | name=%s | %s → %s",
            self.name, old_state.value, new_state.value,
        )

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        """Returns current circuit breaker status as a dict (for health checks)."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout_seconds": self.recovery_timeout,
        }

    def __repr__(self) -> str:
        return f"<CircuitBreaker name={self.name!r} state={self._state.value}>"
