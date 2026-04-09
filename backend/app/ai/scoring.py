"""
Deterministic Quantitative Scoring Engine (ai/scoring.py)

Calculates mathematical momentum signals from the pre-computed indicators
already stored on StockDataResponse (rsi, sma, ema).
Outputs a normalized -1.0 to 1.0 score and a momentum label for the LLM Synthesis Node.
"""

from typing import Dict, Any
from ..schemas.stock import StockDataResponse

def compute_technical_signals(stock_data: StockDataResponse) -> Dict[str, Any]:
    """
    Evaluates pre-computed technical indicators from StockDataResponse to produce
    a normalized momentum score and signal string for the LLM synthesis node.

    Uses the rsi, sma, and ema fields already computed by indicators.py and
    stored on the StockDataResponse — there is no raw 'history' list on that schema.
    """
    current_price = stock_data.current_price

    # Use pre-computed values produced by indicators.py; fall back gracefully if None
    rsi  = stock_data.rsi  if stock_data.rsi  is not None else 50.0
    sma  = stock_data.sma  if stock_data.sma  is not None else current_price
    ema  = stock_data.ema  if stock_data.ema  is not None else current_price

    # ── Deterministic Scoring (-1.0 to +1.0) ────────────────────────────────
    score = 0.0

    # Price vs SMA (trend filter)
    if current_price > sma:
        score += 0.3   # Price above SMA → bullish bias
    else:
        score -= 0.3   # Price below SMA → bearish bias

    # Price vs EMA (momentum filter)
    if current_price > ema:
        score += 0.2
    else:
        score -= 0.2

    # RSI mean-reversion signal
    if rsi > 70:
        score -= 0.3   # Overbought → negative forward momentum expected
    elif rsi < 30:
        score += 0.3   # Oversold  → positive bounce expected

    # Cap to [-1.0, +1.0]
    score = max(-1.0, min(1.0, score))

    # ── Momentum label ───────────────────────────────────────────────────────
    if score >= 0.3:
        momentum = "BULLISH"
    elif score <= -0.3:
        momentum = "BEARISH"
    else:
        momentum = "NEUTRAL"

    return {
        "score":           round(score, 2),
        "rsi":             round(rsi, 2),
        "sma_50":          round(sma, 2),   # SMA(20) used as shorter-term proxy
        "sma_200":         round(ema, 2),   # EMA(20) used as longer-term proxy
        "momentum_signal": momentum,
    }
