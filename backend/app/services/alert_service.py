"""
Real Alert Service (services/alert_service.py)

Production-grade background polling system:
- Fetches live yfinance prices every 5 minutes
- Evaluates user-defined conditions (RSI, Price, SMA cross)
- Triggers and persists alerts to SQLite/PostgreSQL
- Notifies via in-memory queue (UI reads from this)
"""

import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any

import yfinance as yf

from app.core.database import SessionLocal
from app.models.alert import Alert, AlertCondition, AlertStatus
from app.services.indicators import calculate_rsi, calculate_sma

logger = logging.getLogger(__name__)

# In-memory notification queue — Streamlit polls this
_notification_queue: List[Dict[str, Any]] = []
_polling_task = None

# Poll every 5 minutes to avoid API abuse (yfinance rate limits)
POLL_INTERVAL_SECONDS = 300


def _evaluate_condition(condition: AlertCondition, threshold: float,
                         price: float, rsi: float | None, sma: float | None) -> bool:
    """Deterministic threshold evaluation for one alert row."""
    if condition == AlertCondition.PRICE_ABOVE:
        return price > threshold
    if condition == AlertCondition.PRICE_BELOW:
        return price < threshold
    if condition == AlertCondition.RSI_ABOVE and rsi is not None:
        return rsi > threshold
    if condition == AlertCondition.RSI_BELOW and rsi is not None:
        return rsi < threshold
    if condition == AlertCondition.SMA_CROSS_ABOVE and sma is not None:
        return price > sma  # price has crossed above the SMA
    if condition == AlertCondition.SMA_CROSS_BELOW and sma is not None:
        return price < sma  # price has crossed below the SMA
    return False


def _fetch_market_data(symbol: str) -> Dict[str, float | None]:
    """Fetches current price, RSI, and SMA from yfinance for a single symbol."""
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period="3mo", interval="1d")
        if hist.empty:
            return {"price": None, "rsi": None, "sma": None}

        closes = hist["Close"].dropna().tolist()
        price = closes[-1]
        rsi = calculate_rsi(closes, period=14) if len(closes) >= 15 else None
        sma = calculate_sma(closes, period=20) if len(closes) >= 20 else None

        return {"price": price, "rsi": rsi, "sma": sma}
    except Exception as e:
        logger.error("Failed to fetch market data for %s: %s", symbol, e)
        return {"price": None, "rsi": None, "sma": None}


async def fetch_and_evaluate_alerts():
    """
    Background coroutine that:
    1. Reads all ACTIVE alerts from database
    2. Groups them by symbol (single yfinance call per symbol)
    3. Evaluates each alert's condition
    4. Marks triggered alerts as TRIGGERED in DB
    5. Pushes notification to the in-memory queue (UI reads from this)
    """
    while True:
        try:
            db = SessionLocal()
            try:
                active_alerts: List[Alert] = (
                    db.query(Alert)
                    .filter(Alert.status == AlertStatus.ACTIVE)
                    .all()
                )

                if not active_alerts:
                    logger.debug("No active alerts to check.")
                    await asyncio.sleep(POLL_INTERVAL_SECONDS)
                    continue

                # Group symbols to minimize API calls
                symbols = list(set(a.symbol.upper() for a in active_alerts))
                logger.info("Polling %d symbol(s) for %d alert(s)", len(symbols), len(active_alerts))

                market_data = {}
                for symbol in symbols:
                    market_data[symbol] = _fetch_market_data(symbol)
                    # Small delay between symbols to avoid rate limiting
                    await asyncio.sleep(1)

                # Evaluate each alert
                for alert in active_alerts:
                    data = market_data.get(alert.symbol.upper(), {})
                    price = data.get("price")
                    rsi   = data.get("rsi")
                    sma   = data.get("sma")

                    if price is None:
                        continue  # data unavailable, skip

                    triggered = _evaluate_condition(
                        alert.condition, alert.threshold, price, rsi, sma
                    )

                    if triggered:
                        msg = (
                            f"🔔 ALERT TRIGGERED: {alert.symbol} | "
                            f"{alert.condition.value} @ {alert.threshold} "
                            f"(Current: ${price:.2f}"
                            f"{f', RSI: {rsi:.1f}' if rsi else ''}"
                            f"{f', SMA: {sma:.2f}' if sma else ''})"
                        )
                        logger.warning(msg)

                        # Persist to DB
                        alert.status = AlertStatus.TRIGGERED
                        alert.message = msg
                        alert.triggered_at = datetime.now(timezone.utc)

                        # Push to notification queue (UI polls this)
                        _notification_queue.append({
                            "id": alert.id,
                            "symbol": alert.symbol,
                            "condition": alert.condition.value,
                            "threshold": alert.threshold,
                            "current_price": round(price, 2),
                            "rsi": round(rsi, 2) if rsi else None,
                            "sma": round(sma, 2) if sma else None,
                            "message": msg,
                            "triggered_at": datetime.now(timezone.utc).isoformat()
                        })
                        # Cap queue at 50
                        if len(_notification_queue) > 50:
                            _notification_queue.pop(0)

                db.commit()
            finally:
                db.close()

        except asyncio.CancelledError:
            logger.info("Alert polling loop stopped.")
            break
        except Exception as e:
            logger.error("Unexpected error in alert loop: %s", e)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)


def get_recent_alerts() -> List[Dict[str, Any]]:
    """Returns the last 10 triggered alert notifications for the UI."""
    return list(reversed(_notification_queue[-10:]))


def get_all_active_alerts() -> List[Alert]:
    """DB read for all active alert rules."""
    db = SessionLocal()
    try:
        return db.query(Alert).filter(Alert.status == AlertStatus.ACTIVE).all()
    finally:
        db.close()


def create_alert(symbol: str, condition: str, threshold: float) -> Alert:
    """API endpoint helper to create a new alert rule in the DB."""
    db = SessionLocal()
    try:
        alert = Alert(
            symbol=symbol.upper(),
            condition=AlertCondition(condition),
            threshold=threshold,
            status=AlertStatus.ACTIVE
        )
        db.add(alert)
        db.commit()
        db.refresh(alert)
        return alert
    finally:
        db.close()


def delete_alert(alert_id: int) -> bool:
    db = SessionLocal()
    try:
        alert = db.query(Alert).filter(Alert.id == alert_id).first()
        if alert:
            db.delete(alert)
            db.commit()
            return True
        return False
    finally:
        db.close()


def start_scheduler():
    global _polling_task
    _polling_task = asyncio.create_task(fetch_and_evaluate_alerts())
    logger.info("✅ Real Alert Engine started — polling every %ds", POLL_INTERVAL_SECONDS)


def stop_scheduler():
    if _polling_task:
        _polling_task.cancel()
