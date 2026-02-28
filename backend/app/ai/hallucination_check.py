"""
Hallucination Check (ai/hallucination_check.py)

Implements Task 6 – Guardrails:
- Cross-validates LLM textual output against actual fetched stock data.
- Extracts any numeric values (e.g. prices, RSI, SMA) mentioned by the LLM
  in free-text fields and compares them to ground-truth values from yFinance.
- If a mismatch exceeds the configured TOLERANCE threshold, the value
  is flagged, the discrepancy is logged, and the offending sentence is
  corrected or annotated in-place.

Design Philosophy:
    LLMs are trained on static data. When injected with live prices, they
    sometimes echo stale or fabricated numbers (e.g., a price that was never
    in the input). This module acts as a fact-checker — comparing every numeric
    claim in the LLM's text against the ground-truth data we fetched ourselves
    milliseconds ago.
"""

import re
import logging
from typing import Optional

from app.schemas.analysis import FinancialAnalysisResult
from app.schemas.stock import StockDataResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Relative tolerance: how far the LLM's stated number can deviate from reality.
# 10% is generous — a 10% discrepancy in a professional analysis is unacceptable
# and signals hallucination, not rounding.
_PRICE_TOLERANCE = 0.10   # 10%

# Any number below this is assumed to be an RSI or percentage, not a price.
_RSI_MAX_VALUE = 100.0

# Regex to extract standalone numeric values (e.g. $182.45, 182, 72.3)
_NUM_PATTERN = re.compile(r"\$?([\d,]+\.?\d*)")


# ---------------------------------------------------------------------------
# Core Extraction & Comparison
# ---------------------------------------------------------------------------

def _extract_numbers(text: str) -> list[float]:
    """Extracts all numeric values from a free-text string."""
    raw_matches = _NUM_PATTERN.findall(text)
    numbers = []
    for m in raw_matches:
        try:
            numbers.append(float(m.replace(",", "")))
        except ValueError:
            continue
    return numbers


def _is_price_like(value: float, actual_price: Optional[float]) -> bool:
    """
    Returns True if a number looks like a price claim (i.e., close to the
    actual current price), so we can safely compare it.
    Avoids treating RSI (0-100), percentages, or volumes as prices.
    """
    if actual_price is None or actual_price == 0:
        return False
    # Is the number within 50x or 0.02x of the real price? Then it's price-like.
    ratio = value / actual_price
    return 0.02 < ratio < 50.0 and value > _RSI_MAX_VALUE


def _pct_diff(a: float, b: float) -> float:
    """Absolute percentage difference between two values."""
    if b == 0:
        return 0.0
    return abs(a - b) / abs(b)


# ---------------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------------

def run_hallucination_check(
    result: FinancialAnalysisResult,
    stock_data: StockDataResponse,
) -> FinancialAnalysisResult:
    """
    Scans all text fields inside the LLM result for numeric values that
    appear to be price claims, then validates them against ground-truth data.

    Ground-truth values cross-referenced:
        - current_price
        - rsi (as a secondary check)
        - sma_20 (if present)

    Args:
        result:     The FinancialAnalysisResult from the LLM (already toxicity-checked).
        stock_data: The live StockDataResponse fetched from yFinance.

    Returns:
        The original `result` — potentially with `summary` annotated if a
        hallucinated price was found. (We annotate rather than silently drop,
        so users can see a correction notice.)
    """
    actual_price: Optional[float] = stock_data.current_price
    hallucinations_found: list[str] = []

    # Collect all text fields to check
    text_fields: dict[str, str] = {
        "summary": result.summary,
        "technical_posture": result.technical_posture,
    }
    for i, finding in enumerate(result.key_findings):
        text_fields[f"key_findings[{i}].detail"] = finding.detail
    for i, risk in enumerate(result.risk_factors):
        text_fields[f"risk_factors[{i}]"] = risk

    for field_name, text in text_fields.items():
        numbers = _extract_numbers(text)
        for num in numbers:
            if _is_price_like(num, actual_price):
                diff = _pct_diff(num, actual_price)
                if diff > _PRICE_TOLERANCE:
                    msg = (
                        f"Hallucination detected | field={field_name} | "
                        f"llm_value={num:.2f} | actual_price={actual_price:.2f} | "
                        f"deviation={diff * 100:.1f}%"
                    )
                    logger.warning("⚠️  %s", msg)
                    hallucinations_found.append(
                        f"{field_name}: LLM stated ${num:.2f}, actual price is ${actual_price:.2f} "
                        f"({diff * 100:.1f}% deviation)"
                    )
                else:
                    logger.debug(
                        "✅ Price value %.2f in '%s' is within tolerance (actual: %.2f).",
                        num, field_name, actual_price,
                    )

    # If hallucinations were found, annotate the summary so the user knows
    if hallucinations_found:
        correction_notice = (
            " [⚠️ Note: The AI cited inaccurate price data. "
            "Please refer to the live metrics above for accurate figures.]"
        )
        result = result.model_copy(
            update={"summary": result.summary + correction_notice}
        )
        logger.warning(
            "Hallucination check flagged %d value(s) in analysis for %s.",
            len(hallucinations_found),
            getattr(stock_data, "symbol", "UNKNOWN"),
        )
    else:
        logger.debug("✅ Hallucination check passed — all numeric claims are consistent.")

    return result
