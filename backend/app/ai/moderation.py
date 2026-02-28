"""
Toxicity & Safety Moderation Filter (ai/moderation.py)

Implements Task 6 – Guardrails:
- Runs a keyword-based toxicity screen on LLM output fields before
  the analysis is sent to the client.
- Blocks harmful, abusive, or non-financial language.
- Returns a safe fallback response if flagged content is detected.
- Logs every interception with the exact reason.

Design Philosophy:
    A financial AI assistant must only ever respond in a calm, data-driven,
    professional tone. Any LLM hallucination that produces threatening or
    harmful language is immediately quarantined — the client only ever sees
    a clean, neutralized fallback.
"""

import logging
from app.schemas.analysis import FinancialAnalysisResult

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Toxic keyword registry
# These are terms that should NEVER appear in a professional financial analysis.
# The list is intentionally broad: profanity, violent threats, and highly
# emotive/manipulative terms that could constitute illegal financial advice.
# ---------------------------------------------------------------------------
_TOXIC_KEYWORDS = [
    # Profanity / Abuse
    "fuck", "shit", "asshole", "bitch", "bastard", "crap", "damn it",
    # Violent / Threatening Language
    "kill", "murder", "threat", "attack", "bomb", "destroy",
    # Manipulative / Illegal financial advice
    "guaranteed profit", "100% return", "risk-free", "get rich quick",
    "buy now before it's too late", "act fast or lose everything",
    # Hateful / Discriminatory content
    "racist", "sexist", "bigot", "hate",
]


def _contains_toxic_content(text: str) -> tuple[bool, str]:
    """
    Scans a text string for the presence of any registered toxic keyword.
    Returns a (flagged: bool, reason: str) tuple.
    Case-insensitive matching.
    """
    lowered = text.lower()
    for keyword in _TOXIC_KEYWORDS:
        if keyword in lowered:
            return True, f"Blocked keyword detected: '{keyword}'"
    return False, ""


def _build_safe_fallback(reason: str) -> FinancialAnalysisResult:
    """
    Constructs a sanitized, professional FinancialAnalysisResult that is
    safe to return to the client when toxic content is detected.
    """
    return FinancialAnalysisResult(
        summary=(
            "The AI-generated analysis for this symbol was flagged by the "
            "content safety filter and could not be displayed. "
            "Please try again or contact support."
        ),
        sentiment="NEUTRAL",
        technical_posture="Technical analysis data is currently unavailable.",
        key_findings=[],
        risk_factors=[
            "The analysis output was quarantined due to a content policy violation.",
            "This does not reflect market conditions. Please consult reliable sources.",
        ],
    )


def run_toxicity_check(result: FinancialAnalysisResult) -> FinancialAnalysisResult:
    """
    Main moderation entry point. Scans all text fields inside a
    FinancialAnalysisResult for toxic content.

    Fields checked (in order):
      1. summary
      2. technical_posture
      3. key_findings (each Detail text)
      4. risk_factors (each string)

    Args:
        result: The parsed, schema-valid output from the LLM.

    Returns:
        The original `result` if clean.
        A safe fallback FinancialAnalysisResult if any toxic content is found.
    """
    checks: list[tuple[str, str]] = [
        ("summary", result.summary),
        ("technical_posture", result.technical_posture),
    ]

    # Add each key_finding's detail to the check list
    for i, finding in enumerate(result.key_findings):
        checks.append((f"key_findings[{i}].topic", finding.topic))
        checks.append((f"key_findings[{i}].detail", finding.detail))

    # Add each risk factor to the check list
    for i, risk in enumerate(result.risk_factors):
        checks.append((f"risk_factors[{i}]", risk))

    for field_name, text in checks:
        flagged, reason = _contains_toxic_content(text)
        if flagged:
            logger.warning(
                "🚨 Toxicity filter triggered | field=%s | reason=%s",
                field_name,
                reason,
            )
            return _build_safe_fallback(reason)

    logger.debug("✅ Toxicity check passed — all fields are clean.")
    return result
