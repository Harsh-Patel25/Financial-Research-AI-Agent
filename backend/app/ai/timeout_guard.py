"""
AI Timeout Guard (ai/timeout_guard.py)

Wraps synchronous LLM calls with a configurable timeout.
If the LLM doesn't respond within the deadline, returns a deterministic
fallback FinancialAnalysisResult so the UI never freezes.

Architecture:
  - Runs the blocking LLM call inside a ThreadPoolExecutor
  - asyncio.wait_for enforces the wall-clock deadline
  - On timeout: returns a pre-built fallback payload built from the
    deterministic scoring.py scores (so at minimum the math is still shown)
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Optional

from ..schemas.analysis import FinancialAnalysisResult, TechnicalSignal, SentimentSignal

logger = logging.getLogger(__name__)

# Single shared executor — prevents thread explosion
_executor = ThreadPoolExecutor(max_workers=4)

# Wall-clock timeout for LLM synthesis (seconds)
LLM_TIMEOUT_SECONDS = 20


def build_fallback_verdict(tech_scores: dict) -> FinancialAnalysisResult:
    """
    Builds a deterministic fallback verdict using only the pre-calculated
    quantitative scores when the LLM is too slow or unavailable.
    """
    score = tech_scores.get("score", 0.0)
    rsi   = tech_scores.get("rsi", 50.0)
    sma50 = tech_scores.get("sma_50", 0.0)
    sma200 = tech_scores.get("sma_200", 0.0)
    signal = tech_scores.get("momentum_signal", "NEUTRAL")

    # Map signal to verdict
    verdict = signal  # BULLISH | BEARISH | NEUTRAL
    # Raw confidence from score magnitude
    confidence = int(min(100, abs(score) * 100))

    return FinancialAnalysisResult(
        verdict=verdict,
        confidence=confidence,
        reasoning_summary=(
            f"⚡ Fast-Mode Analysis: LLM synthesis timed out. Showing deterministic signals only. "
            f"Momentum score: {score:+.2f} | Technical Signal: {signal}."
        ),
        technical_signals=[
            TechnicalSignal(
                indicator="RSI (14)",
                value=rsi,
                interpretation="Oversold" if rsi < 30 else "Overbought" if rsi > 70 else "Neutral"
            ),
            TechnicalSignal(
                indicator="SMA Cross (50 vs 200)",
                value=round(sma50 - sma200, 2),
                interpretation=(
                    "Golden Cross — bullish trend" if sma50 > sma200
                    else "Death Cross — bearish trend" if sma200 > 0
                    else "Insufficient data"
                )
            )
        ],
        sentiment_signals=[
            SentimentSignal(
                source="LLM Synthesis",
                score=0.0,
                interpretation="LLM timed out. Sentiment unavailable."
            )
        ],
        risk_assessment="LLM synthesis timed out. Risk assessment based on technical signals only."
    )


async def run_with_timeout(
    fn: Callable,
    tech_scores: dict,
    timeout: int = LLM_TIMEOUT_SECONDS,
    *args,
    **kwargs,
) -> FinancialAnalysisResult:
    """
    Runs a blocking LLM function inside a thread with a hard timeout.
    
    Args:
        fn: The blocking function to run (e.g., analyst_agent.analyze_stock)
        tech_scores: Pre-calculated deterministic scores for fallback
        timeout: Max seconds to wait before returning fallback
        *args, **kwargs: Forwarded to fn
        
    Returns:
        FinancialAnalysisResult from LLM or deterministic fallback
    """
    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(_executor, lambda: fn(*args, **kwargs)),
            timeout=timeout
        )
        return result
    except asyncio.TimeoutError:
        logger.warning(
            "⏱️ LLM timeout after %ds — returning deterministic fallback verdict.", timeout
        )
        return build_fallback_verdict(tech_scores)
    except Exception as e:
        logger.error("LLM call failed: %s — returning fallback.", e)
        return build_fallback_verdict(tech_scores)
