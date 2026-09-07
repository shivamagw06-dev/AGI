"""Knowledge maturity — institutional grade per company."""

from __future__ import annotations

from typing import Any

DNA_DIMENSIONS: tuple[str, ...] = (
    "identity",
    "business",
    "economic",
    "competitive",
    "management",
    "financial",
    "growth",
    "risk",
    "valuation",
    "investment",
    "monitoring",
)

# Map IKO claim categories → DNA dimensions
CATEGORY_TO_DNA: dict[str, str] = {
    "identity": "identity",
    "business_model": "business",
    "economic_engine": "economic",
    "competitive_position": "competitive",
    "management": "management",
    "financial_quality": "financial",
    "growth": "growth",
    "valuation_context": "valuation",
    "investment_thesis": "investment",
    "risks": "risk",
    "monitoring": "monitoring",
}

STRONG_STATES = frozenset({"SUPPORTED", "ANSWERED"})
PARTIAL_STATES = frozenset({"PARTIAL", "UNDER_REVIEW"})
WEAK_STATES = frozenset({"CONTRADICTED", "STALE", "UNKNOWN"})


def _dimension_status(claims: list[dict[str, Any]], dimension: str) -> str:
    relevant = [c for c in claims if CATEGORY_TO_DNA.get(str(c.get("category")), "") == dimension]
    if not relevant:
        return "unknown"
    states = [str(c.get("state")) for c in relevant]
    if any(s in STRONG_STATES for s in states):
        if all(s in STRONG_STATES for s in states):
            return "complete"
        return "partial"
    if any(s in PARTIAL_STATES for s in states):
        return "partial"
    return "unknown"


def _institutional_grade(
    *,
    complete: int,
    partial: int,
    unknown: int,
    contradictions: int,
    total_dims: int,
) -> str:
    score = (complete * 100 + partial * 55) / max(total_dims, 1)
    score -= contradictions * 8
    score -= unknown * 5
    if score >= 90:
        return "A"
    if score >= 80:
        return "A-"
    if score >= 70:
        return "B+"
    if score >= 60:
        return "B"
    if score >= 50:
        return "B-"
    if score >= 40:
        return "C+"
    return "C"


def calculate_maturity(iko: dict[str, Any]) -> dict[str, Any]:
    """Knowledge maturity replaces arbitrary completion percentages."""
    claims = list(iko.get("claims") or [])
    dimensions: dict[str, str] = {}
    for dim in DNA_DIMENSIONS:
        dimensions[dim] = _dimension_status(claims, dim)

    complete = sum(1 for v in dimensions.values() if v == "complete")
    partial = sum(1 for v in dimensions.values() if v == "partial")
    unknown_dims = sum(1 for v in dimensions.values() if v == "unknown")

    contradictions = sum(1 for c in claims if str(c.get("state")) == "CONTRADICTED")
    unknowns = sum(1 for c in claims if str(c.get("state")) == "UNKNOWN")

    grade = _institutional_grade(
        complete=complete,
        partial=partial,
        unknown=unknown_dims,
        contradictions=contradictions,
        total_dims=len(DNA_DIMENSIONS),
    )

    return {
        "entity_id": iko.get("entity_id"),
        "knowledge_maturity": dimensions,
        "institutional_grade": grade,
        "complete_dimensions": complete,
        "partial_dimensions": partial,
        "unknown_dimensions": unknown_dims,
        "unknown_count": unknowns,
        "contradiction_count": contradictions,
        "no_percentages": True,
    }
