"""Uncertainty engine — known / known-unknowns / unknown-unknowns / conflicts."""

from __future__ import annotations

from typing import Any


def build_uncertainty(
    evidence: list[dict[str, Any]],
    *,
    assumptions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    supporting = [e for e in evidence if e.get("effect") in ("Confirms", "Supports", "Weakly Supports")]
    contradicting = [e for e in evidence if e.get("effect") in ("Questions", "Contradicts", "Refutes")]
    missing = [
        e
        for e in evidence
        if e.get("polarity") == "missing" or e.get("kind") == "missing" or "incomplete" in str(e.get("text") or "").lower()
    ]
    neutral = [e for e in evidence if e.get("effect") == "Neutral" and e not in missing]
    assumptions = assumptions or {}

    known = [e.get("text") for e in supporting + contradicting]
    known_unknowns = list(assumptions.get("untested") or []) + [e.get("text") for e in missing]
    unknown_unknowns = [
        "Regime breaks not spanned by historical sample",
        "Undisclosed competitive responses",
    ]
    conflicting = []
    if supporting and contradicting:
        conflicting.append(
            f"{len(supporting)} supporting vs {len(contradicting)} contradicting evidence items"
        )

    return {
        "known": known[:8],
        "known_unknowns": known_unknowns[:8],
        "unknown_unknowns": unknown_unknowns,
        "missing_evidence": [e.get("text") for e in missing],
        "missing_count": len(missing),
        "conflicting_evidence": conflicting,
        "neutral_evidence": [e.get("text") for e in neutral[:5]],
        "conflict_intensity": round(min(1.0, len(contradicting) / max(len(supporting), 1)), 4),
    }
