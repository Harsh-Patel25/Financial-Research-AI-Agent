"""
Alert API Router (api/alerts.py)
CRUD endpoints for creating, reading, and deleting market alert rules.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List
from app.services import alert_service

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


class CreateAlertRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol e.g. AAPL, RELIANCE.NS")
    condition: str = Field(..., description="price_above | price_below | rsi_above | rsi_below | sma_cross_above | sma_cross_below")
    threshold: float = Field(..., description="The numeric threshold to trigger on")


@router.post("/", status_code=201)
def create_alert(body: CreateAlertRequest):
    """Create a new market alert rule."""
    valid_conditions = [
        "price_above", "price_below", "rsi_above", "rsi_below",
        "sma_cross_above", "sma_cross_below"
    ]
    if body.condition not in valid_conditions:
        raise HTTPException(status_code=400, detail=f"Invalid condition. Must be one of: {valid_conditions}")
    alert = alert_service.create_alert(body.symbol, body.condition, body.threshold)
    return {"id": alert.id, "symbol": alert.symbol, "condition": alert.condition, "threshold": alert.threshold, "status": alert.status}


@router.get("/active")
def list_active_alerts():
    """List all currently active alert rules."""
    alerts = alert_service.get_all_active_alerts()
    return [
        {"id": a.id, "symbol": a.symbol, "condition": a.condition, "threshold": a.threshold}
        for a in alerts
    ]


@router.get("/notifications")
def get_notifications():
    """Get the last 10 triggered alert notifications (UI polls this)."""
    return {"notifications": alert_service.get_recent_alerts()}


@router.delete("/{alert_id}")
def delete_alert(alert_id: int):
    """Delete an alert rule by ID."""
    deleted = alert_service.delete_alert(alert_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "deleted", "id": alert_id}
