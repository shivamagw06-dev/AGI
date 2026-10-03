"""Centralised confidence modifiers for FIRE and future engines (FKB-01)."""

from __future__ import annotations

from typing import Any

# Point deltas applied by consumers when scoring High/Medium/Low bands.
CONFIDENCE_MODIFIERS: dict[str, dict[str, Any]] = {
    "coverage_high": {
        "id": "coverage_high",
        "when": "coverage_pct >= 80",
        "points": 1,
        "description": "Strong evidence coverage supports higher confidence.",
    },
    "coverage_low": {
        "id": "coverage_low",
        "when": "coverage_pct < 40",
        "points": -1,
        "description": "Weak coverage reduces confidence.",
    },
    "validation_approved": {
        "id": "validation_approved",
        "when": "validation_status == APPROVED",
        "points": 2,
        "description": "Fully approved warehouse facts raise confidence.",
    },
    "validation_warnings": {
        "id": "validation_warnings",
        "when": "validation_status == APPROVED_WITH_WARNINGS",
        "points": 1,
        "description": "Approved-with-warnings facts partially support confidence.",
    },
    "history_deep": {
        "id": "history_deep",
        "when": "history_n >= 8",
        "points": 2,
        "description": "Deep history improves trend/relationship confidence.",
    },
    "history_moderate": {
        "id": "history_moderate",
        "when": "history_n >= 4",
        "points": 1,
        "description": "Moderate history partially supports confidence.",
    },
    "history_thin": {
        "id": "history_thin",
        "when": "history_n < 2",
        "points": -2,
        "description": "Insufficient history forces low confidence.",
    },
    "missing_periods": {
        "id": "missing_periods",
        "when": "missing_periods > 0",
        "points": -1,
        "description": "Missing periods reduce confidence.",
    },
    "conflicting_evidence": {
        "id": "conflicting_evidence",
        "when": "conflict == True",
        "points": -1,
        "band_downgrade": 1,
        "description": "Conflicting evidence downgrades confidence by one band.",
    },
    "windows_rich": {
        "id": "windows_rich",
        "when": "windows_n >= 3",
        "points": 2,
        "description": "Multiple comparable windows (QoQ/YoY/multi-year) raise confidence.",
    },
}


def all_modifiers() -> list[dict[str, Any]]:
    return [CONFIDENCE_MODIFIERS[k] for k in sorted(CONFIDENCE_MODIFIERS)]


def get_modifier(key: str) -> dict[str, Any] | None:
    k = key.strip().lower().replace(" ", "_")
    row = CONFIDENCE_MODIFIERS.get(k)
    return dict(row) if row else None


def apply_points(
    *,
    history_n: int = 0,
    windows_n: int = 0,
    validation_status: str | None = None,
    coverage_pct: float | None = None,
    missing_periods: int = 0,
    conflict: bool = False,
) -> dict[str, Any]:
    """Compute aggregate modifier points (knowledge helper — does not classify High/Med/Low alone)."""
    points = 0
    applied: list[str] = []
    if coverage_pct is not None:
        if coverage_pct >= 80:
            points += CONFIDENCE_MODIFIERS["coverage_high"]["points"]
            applied.append("coverage_high")
        elif coverage_pct < 40:
            points += CONFIDENCE_MODIFIERS["coverage_low"]["points"]
            applied.append("coverage_low")
    status = (validation_status or "").upper()
    if status == "APPROVED":
        points += CONFIDENCE_MODIFIERS["validation_approved"]["points"]
        applied.append("validation_approved")
    elif status == "APPROVED_WITH_WARNINGS":
        points += CONFIDENCE_MODIFIERS["validation_warnings"]["points"]
        applied.append("validation_warnings")
    if history_n >= 8:
        points += CONFIDENCE_MODIFIERS["history_deep"]["points"]
        applied.append("history_deep")
    elif history_n >= 4:
        points += CONFIDENCE_MODIFIERS["history_moderate"]["points"]
        applied.append("history_moderate")
    elif history_n < 2:
        points += CONFIDENCE_MODIFIERS["history_thin"]["points"]
        applied.append("history_thin")
    if windows_n >= 3:
        points += CONFIDENCE_MODIFIERS["windows_rich"]["points"]
        applied.append("windows_rich")
    if missing_periods > 0:
        points += CONFIDENCE_MODIFIERS["missing_periods"]["points"]
        applied.append("missing_periods")
    band_downgrade = 0
    if conflict:
        points += CONFIDENCE_MODIFIERS["conflicting_evidence"]["points"]
        band_downgrade = int(CONFIDENCE_MODIFIERS["conflicting_evidence"].get("band_downgrade") or 0)
        applied.append("conflicting_evidence")
    return {
        "points": points,
        "band_downgrade": band_downgrade,
        "applied": applied,
        "performs_analysis": False,
    }
