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
from app.schemas.analysis import FinancialAnalysisResult, KeyFinding

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configurable field-level character limits
# ---------------------------------------------------------------------------

LIMITS = {
    "summary":          600,   # ~4-5 readable sentences max
    "technical_posture": 300,  # 2-3 sentences
    "key_finding_topic": 60,   # Short label, not a paragraph
    "key_finding_detail": 250, # 1-2 sentences per bullet
    "risk_factor":       200,  # 1 crisp sentence per risk
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

    # --- summary ---
    clean_summary = _truncate(result.summary, LIMITS["summary"], "summary")
    if clean_summary != result.summary:
        changes["summary"] = clean_summary

    # --- technical_posture ---
    clean_posture = _truncate(
        result.technical_posture, LIMITS["technical_posture"], "technical_posture"
    )
    if clean_posture != result.technical_posture:
        changes["technical_posture"] = clean_posture

    # --- key_findings (rebuild list if any field was trimmed) ---
    clean_findings = []
    findings_changed = False
    for i, finding in enumerate(result.key_findings):
        clean_topic = _truncate(
            finding.topic, LIMITS["key_finding_topic"], f"key_findings[{i}].topic"
        )
        clean_detail = _truncate(
            finding.detail, LIMITS["key_finding_detail"], f"key_findings[{i}].detail"
        )
        if clean_topic != finding.topic or clean_detail != finding.detail:
            findings_changed = True
        clean_findings.append(KeyFinding(topic=clean_topic, detail=clean_detail))
    if findings_changed:
        changes["key_findings"] = clean_findings

    # --- risk_factors ---
    clean_risks = []
    risks_changed = False
    for i, risk in enumerate(result.risk_factors):
        clean_risk = _truncate(risk, LIMITS["risk_factor"], f"risk_factors[{i}]")
        if clean_risk != risk:
            risks_changed = True
        clean_risks.append(clean_risk)
    if risks_changed:
        changes["risk_factors"] = clean_risks

    if changes:
        logger.info("Response length enforcement applied %d field change(s).", len(changes))
        return result.model_copy(update=changes)

    logger.debug("✅ Response length check passed — all fields are within limits.")
    return result
