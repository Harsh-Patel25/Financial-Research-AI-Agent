"""
Analysis Schemas (schemas/analysis.py)

Strict Pydantic models for enforcing JSON structure from the LLM.
Task 5 requires structured, deterministic outputs without "creative" fluff.
"""

from typing import List, Literal
from pydantic import BaseModel, Field


class KeyFinding(BaseModel):
    """A single actionable bullet point from the analysis."""
    topic: str = Field(..., description="High-level category (e.g., 'Momentum', 'Risk', 'Catalyst')")
    detail: str = Field(..., description="1-2 sentences explaining the finding based *strictly* on provided data.")


class FinancialAnalysisResult(BaseModel):
    """
    The strictly enforced JSON schema that the LLM must output.
    Any deviation will fail validation.
    """
    summary: str = Field(
        ..., 
        description="A concise, professional 2-3 sentence overview of the current situation."
    )
    sentiment: Literal["BULLISH", "BEARISH", "NEUTRAL"] = Field(
        ..., 
        description="Overall derived sentiment based on price action and news."
    )
    technical_posture: str = Field(
        ..., 
        description="Analysis of RSI and Moving Averages (e.g., 'Oversold but trending below 20-SMA')."
    )
    key_findings: List[KeyFinding] = Field(
        ..., 
        description="0-5 critical bullet points spanning price action, news catalysts, and risks.",
        min_length=0,
        max_length=5
    )
    risk_factors: List[str] = Field(
        ..., 
        description="1-3 potential downside risks mentioned in news or indicated by extreme technicals."
    )
