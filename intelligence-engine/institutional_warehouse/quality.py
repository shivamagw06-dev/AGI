"""Metric quality classification and row confidence.

Two questions every stored row should be able to answer: where did this come
from, and how much weight should a reasoning engine put on it. Both are recorded
at write time, because after the fact neither can be reconstructed.
"""

from __future__ import annotations

from typing import Any, Optional

# Quality types, in the order a consumer should prefer them.
OBSERVED = "observed"        # a source reported it
VENDOR = "vendor"            # a data vendor's own computed figure
CALCULATED = "calculated"    # the warehouse computed it from stored inputs
DERIVED = "derived"          # inferred from other stored values
ESTIMATED = "estimated"      # modelled, not reported
OVERRIDE = "override"        # an admin corrected it
CONFLICTING = "conflicting"  # sources disagree
MISSING = "missing"          # nothing observed

# Which sources produce which class of value.
_VENDOR_SOURCES = ("yahoo", "capital_iq", "capiq", "groww", "consensus", "upstox")
_CALCULATED_SOURCES = ("formula_engine", "warehouse_reconstruction")
_OBSERVED_SOURCES = ("nse_bhavcopy", "nse", "bse", "lidi", "knowledge_factory", "fse",
                     "research_intelligence", "continuous_gather_learn")

CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW, CONFIDENCE_UNKNOWN = (
    "high", "medium", "low", "unknown")

# How much each source is trusted before any other evidence is considered.
_SOURCE_WEIGHT = {
    "upstox": 0.92, "capital_iq": 0.9, "capiq": 0.9, "yahoo_finance": 0.85, "yahoo": 0.85,
    "nse_bhavcopy": 0.95, "fse_warehouse": 0.85, "formula_engine": 0.8,
    "warehouse_reconstruction": 0.75, "knowledge_factory_hd": 0.6,
    "continuous_gather_learn": 0.55, "lidi": 0.7, "manual": 0.9, "manual_import": 0.85,
}


def classify_source(source: Optional[str]) -> str:
    text = str(source or "").strip().lower()
    if not text:
        return OBSERVED
    if text.startswith("admin") or "override" in text or text == "manual":
        return OVERRIDE
    if any(token in text for token in _CALCULATED_SOURCES):
        return CALCULATED
    if any(token in text for token in _VENDOR_SOURCES):
        return VENDOR
    if any(token in text for token in _OBSERVED_SOURCES):
        return OBSERVED
    return OBSERVED


def source_weight(source: Optional[str]) -> float:
    text = str(source or "").strip().lower()
    for key, weight in _SOURCE_WEIGHT.items():
        if key in text:
            return weight
    return 0.5


def row_quality(
    *,
    source: Optional[str],
    observed_fields: int,
    total_fields: int,
    missing_fields: int,
    has_conflict: bool = False,
    has_override: bool = False,
    validation_status: str = "ok",
) -> dict[str, Any]:
    """The quality block written onto every row."""
    if has_override:
        quality = OVERRIDE
    elif has_conflict:
        quality = CONFLICTING
    elif observed_fields == 0:
        quality = MISSING
    else:
        quality = classify_source(source)

    completeness = (observed_fields / total_fields) if total_fields else 0.0
    score = source_weight(source) * 0.5 + completeness * 0.3
    if validation_status == "ok":
        score += 0.2
    elif validation_status == "warn":
        score += 0.1
    if has_conflict:
        score -= 0.15
    score = round(max(0.0, min(score, 1.0)), 3)

    if observed_fields == 0:
        confidence = CONFIDENCE_UNKNOWN
    elif score >= 0.75:
        confidence = CONFIDENCE_HIGH
    elif score >= 0.5:
        confidence = CONFIDENCE_MEDIUM
    else:
        confidence = CONFIDENCE_LOW

    return {
        "quality_type": quality,
        "confidence": confidence,
        "confidence_score": score,
        "completeness": round(completeness, 3),
        "missing_fields": missing_fields,
        "validation_status": validation_status,
    }


def usable_for_reasoning(quality_type: Optional[str], confidence: Optional[str],
                         *, minimum: str = CONFIDENCE_LOW) -> bool:
    """Whether a reasoning engine should narrate this row.

    Missing rows are never narrated. Conflicting rows are surfaced but not used
    as fact unless a caller asks for them explicitly.
    """
    if quality_type in (MISSING, CONFLICTING):
        return False
    order = {CONFIDENCE_UNKNOWN: 0, CONFIDENCE_LOW: 1, CONFIDENCE_MEDIUM: 2, CONFIDENCE_HIGH: 3}
    return order.get(str(confidence), 0) >= order.get(minimum, 1)
