"""Level 18 — Overall Institutional IQ rollup."""

from __future__ import annotations

from typing import Any

from academy.certification.grading.scale import band_for


def compute_institutional_iq(analyst_scores: dict[str, float]) -> dict[str, Any]:
    required = [
        "business",
        "financial",
        "valuation",
        "risk",
        "macro",
        "sector",
        "management",
        "ownership",
        "committee",
        "cio",
        "research_writer",
    ]
    present = {a: float(analyst_scores[a]) for a in required if a in analyst_scores}
    # portfolio optional but included when present
    if "portfolio" in analyst_scores:
        present["portfolio"] = float(analyst_scores["portfolio"])
    # Fall back to all provided analyst scores if required set incomplete
    if len(present) < 8:
        present = {a: float(s) for a, s in analyst_scores.items() if a != "general"}
    overall = round(sum(present.values()) / max(1, len(present)), 2)
    band = band_for(overall)
    return {
        "analyst_iq": present,
        "overall_agi_iq": overall,
        "grade": band["label"],
        "letter": band["letter"],
        "components": required,
    }
