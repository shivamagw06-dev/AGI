"""FDI confidence — evidence linkage + non-cosmetic material changes."""

from __future__ import annotations

from typing import Any


def score_diff(changes: list[dict[str, Any]]) -> dict[str, Any]:
    material = [c for c in changes if not c.get("cosmetic") and c.get("materiality") != "ignore"]
    if not material:
        return {
            "confidence": 40.0,
            "breakdown": {"evidence_link": 50, "materiality_clarity": 40, "cause_coverage": 30},
            "explain": "No material changes detected",
        }
    linked = sum(1 for c in material if c.get("current_doc_id") and c.get("previous_period"))
    evidence_link = 100.0 * linked / len(material)
    with_cause = sum(1 for c in material if c.get("why_changed") or c.get("drivers"))
    cause_coverage = 100.0 * with_cause / len(material)
    critical_high = sum(1 for c in material if c.get("materiality") in {"critical", "high"})
    materiality_clarity = min(100.0, 50.0 + critical_high * 8.0)
    conf = round(evidence_link * 0.40 + materiality_clarity * 0.30 + cause_coverage * 0.30, 1)
    return {
        "confidence": conf,
        "breakdown": {
            "evidence_link": round(evidence_link, 1),
            "materiality_clarity": round(materiality_clarity, 1),
            "cause_coverage": round(cause_coverage, 1),
        },
        "weights": {"evidence_link": 0.40, "materiality_clarity": 0.30, "cause_coverage": 0.30},
        "explain": (
            f"Evidence {evidence_link:.0f}×40% + Materiality {materiality_clarity:.0f}×30% + "
            f"Cause {cause_coverage:.0f}×30% = {conf:.0f}"
        ),
        "material_count": len(material),
    }
