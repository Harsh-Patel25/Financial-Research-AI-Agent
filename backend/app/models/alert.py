"""
Alert Model (models/alert.py)
SQLAlchemy model for persisting user-defined market alerts.
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Enum
from sqlalchemy.sql import func
import enum
from app.core.database import Base


class AlertCondition(str, enum.Enum):
    PRICE_ABOVE = "price_above"
    PRICE_BELOW = "price_below"
    RSI_ABOVE   = "rsi_above"
    RSI_BELOW   = "rsi_below"
    SMA_CROSS_ABOVE = "sma_cross_above"  # price crosses above SMA
    SMA_CROSS_BELOW = "sma_cross_below"  # price crosses below SMA


class AlertStatus(str, enum.Enum):
    ACTIVE    = "active"
    TRIGGERED = "triggered"
    EXPIRED   = "expired"


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = {"extend_existing": True}

    id          = Column(Integer, primary_key=True, index=True)
    symbol      = Column(String, nullable=False, index=True)
    condition   = Column(Enum(AlertCondition), nullable=False)
    threshold   = Column(Float, nullable=False)
    status      = Column(Enum(AlertStatus), default=AlertStatus.ACTIVE)
    message     = Column(String, nullable=True)          # Last triggered message
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    triggered_at = Column(DateTime(timezone=True), nullable=True)
