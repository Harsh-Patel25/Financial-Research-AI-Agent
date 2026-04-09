"""
Analysis Schemas (schemas/analysis.py)

Strict Pydantic models for enforcing JSON structure from the LLM.
Task 5 requires structured, deterministic outputs without "creative" fluff.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class TechnicalSignal(BaseModel):
    """A technical indicator score mapped by the deterministic engine."""
    indicator: str = Field(..., description="E.g., 'RSI', 'SMA', 'MACD'")
    value: float = Field(..., description="The raw calculated value.")
    interpretation: str = Field(..., description="How this specifically impacts the momentum.")

class SentimentSignal(BaseModel):
    """A sentiment component evaluated cleanly by the NLP engine."""
    source: str = Field(..., description="E.g., 'News Headlines', 'Earnings Call'")
    score: float = Field(..., description="Sentiment score from -1.0 to +1.0.")
    interpretation: str = Field(..., description="What is driving this emotion.")

class FinancialAnalysisResult(BaseModel):
    """
    The rigid Decision Intelligence Output.
    The LLM aggregates signals into a final verdict rather than guessing.
    """
    verdict: Literal["BULLISH", "BEARISH", "NEUTRAL"] = Field(
        ..., 
        description="Final deterministic verdict driven by the numerical scores."
    )
    confidence: int = Field(
        ..., 
        description="Confidence out of 100% based on indicator alignment.",
        ge=0, le=100
    )
    reasoning_summary: str = Field(
        ..., 
        description="A professional explanation of WHY the signals align or contradict."
    )
    technical_signals: List[TechnicalSignal] = Field(
        ..., 
        description="Direct inclusion of the deterministic technical inputs."
    )
    sentiment_signals: List[SentimentSignal] = Field(
        ..., 
        description="Direct inclusion of the isolated NLP sentiment outputs."
    )
    risk_assessment: str = Field(
        ..., 
        description="Current downside risk evaluation (e.g., Extreme Volatility, Macro drag)."
    )
