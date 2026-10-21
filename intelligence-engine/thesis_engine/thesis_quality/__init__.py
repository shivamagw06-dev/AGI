"""Thesis quality — institutional minima and logical consistency checks."""

from __future__ import annotations

from typing import Any

from thesis_engine.schema import (
    MIN_CATALYSTS,
    MIN_MAJOR_CONTRADICTIONS,
    MIN_SUPPORTING_PILLARS,
    MIN_THESIS_BREAKING_CONDITIONS,
    THESIS_STATES,
)


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def audit_thesis(thesis: dict[str, Any]) -> dict[str, Any]:
    pillars = _safe_list(thesis.get("supporting_pillars"))
    supported = [p for p in pillars if p.get("supported") or p.get("evidence_backed")]
    contradictions = thesis.get("contradictions") or {}
    major = _safe_list(contradictions.get("major"))
    catalysts = _safe_list(thesis.get("catalysts"))
    breakers = _safe_list(thesis.get("thesis_breaking_conditions"))

    checks = {
        "min_supporting_pillars": len(supported) >= MIN_SUPPORTING_PILLARS,
        "min_major_contradictions": len(major) >= MIN_MAJOR_CONTRADICTIONS,
        "min_catalysts": len(catalysts) >= MIN_CATALYSTS,
        "min_thesis_breaking_conditions": len(breakers) >= MIN_THESIS_BREAKING_CONDITIONS,
        "core_thesis_present": bool((thesis.get("core_thesis") or {}).get("statement")),
        "valid_state": str(thesis.get("status")) in THESIS_STATES,
    }

    # Logical consistency: state must align with conviction band
    conviction = float((thesis.get("conviction") or {}).get("overall") or 0.5)
    status = str(thesis.get("status") or "")
    consistent = True
    if status in ("Very Strong", "Strong") and conviction < 0.52:
        consistent = False
    if status in ("Rejected", "Broken") and conviction >= 0.55:
        consistent = False
    checks["logical_consistency"] = consistent

    return {
        "checks": checks,
        "passed": all(checks.values()),
        "counts": {
            "supporting_pillars": len(supported),
            "major_contradictions": len(major),
            "catalysts": len(catalysts),
            "thesis_breaking_conditions": len(breakers),
        },
        "targets": {
            "supporting_pillars": MIN_SUPPORTING_PILLARS,
            "major_contradictions": MIN_MAJOR_CONTRADICTIONS,
            "catalysts": MIN_CATALYSTS,
            "thesis_breaking_conditions": MIN_THESIS_BREAKING_CONDITIONS,
        },
    }
