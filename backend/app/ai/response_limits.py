"""
Response Length Limits (ai/response_limits.py)

Implements Task 6 – Guardrails:
- Enforces maximum character limits on all free-text fields of the LLM output.
- Prevents the model from generating excessively verbose summaries or
  findings that could overwhelm the UI or inflate token costs on re-processing.
- Truncates fields that exceed the limit and appends an ellipsis to signal
  the cut, so the UI still renders cleanly.
- Logs every truncation as a WARNING for observability.

Design Philosophy:
    A financial summary card is not a research paper. If the LLM writes a
    1500-character summary, the user won't read it. Hard limits enforce
    discipline on the output, keep UI cards compact, and prevent any
    accidental prompt injection via inflated text fields.
"""

import logging
from app.schemas.analysis import FinancialAnalysisResult, TechnicalSignal, SentimentSignal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable field-level character limits
# ---------------------------------------------------------------------------

LIMITS = {
    "reasoning_summary":          600,   # ~4-5 readable sentences max
    "technical_interpretation": 250, # 1-2 sentences per bullet
    "sentiment_interpretation":   250, # 1-2 sentences per bullet
    "risk_assessment":       200,  # 1 crisp sentence per risk
}

_ELLIPSIS = "…"


def _truncate(text: str, limit: int, field_name: str) -> str:
    """
    Truncates `text` to `limit` characters if it exceeds the threshold.
    Logs a warning and appends an ellipsis so readers see the cutoff.
    """
    if len(text) > limit:
        truncated = text[:limit - len(_ELLIPSIS)].rstrip() + _ELLIPSIS
        logger.warning(
            "📏 Response length limit triggered | field=%s | original_len=%d | limit=%d",
            field_name,
            len(text),
            limit,
        )
        return truncated
    return text


def run_length_check(result: FinancialAnalysisResult) -> FinancialAnalysisResult:
    """
    Applies character-level limits to every text field inside a
    FinancialAnalysisResult.

    Fields checked:
        - summary
        - technical_posture
        - key_findings[].topic
        - key_findings[].detail
        - risk_factors[]

    Args:
        result: The FinancialAnalysisResult from the LLM (already toxicity-
                and hallucination-checked).

    Returns:
        A new FinancialAnalysisResult with oversized fields truncated.
    """
    changes: dict = {}

    # --- reasoning_summary ---
    clean_summary = _truncate(result.reasoning_summary, LIMITS["reasoning_summary"], "reasoning_summary")
    if clean_summary != result.reasoning_summary:
        changes["reasoning_summary"] = clean_summary

    # --- technical_signals ---
    clean_technicals = []
    techs_changed = False
    for i, finding in enumerate(result.technical_signals):
        clean_interp = _truncate(
            finding.interpretation, LIMITS["technical_interpretation"], f"technical_signals[{i}].interpretation"
        )
        if clean_interp != finding.interpretation:
            techs_changed = True
        clean_technicals.append(TechnicalSignal(indicator=finding.indicator, value=finding.value, interpretation=clean_interp))
    if techs_changed:
        changes["technical_signals"] = clean_technicals

    # --- sentiment_signals ---
    clean_sentiments = []
    sent_changed = False
    for i, finding in enumerate(result.sentiment_signals):
        clean_interp = _truncate(
            finding.interpretation, LIMITS["sentiment_interpretation"], f"sentiment_signals[{i}].interpretation"
        )
        if clean_interp != finding.interpretation:
            sent_changed = True
        clean_sentiments.append(SentimentSignal(source=finding.source, score=finding.score, interpretation=clean_interp))
    if sent_changed:
        changes["sentiment_signals"] = clean_sentiments
        
    # --- risk_assessment ---
    clean_risk = _truncate(result.risk_assessment, LIMITS["risk_assessment"], "risk_assessment")
    if clean_risk != result.risk_assessment:
        changes["risk_assessment"] = clean_risk

    if changes:
        logger.info("Response length enforcement applied %d field change(s).", len(changes))
        return result.model_copy(update=changes)

    logger.debug("✅ Response length check passed — all fields are within limits.")
    return result
