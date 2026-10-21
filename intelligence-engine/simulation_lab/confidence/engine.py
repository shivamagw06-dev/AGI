"""Simulation confidence — evidence completeness and assumption clarity."""

from __future__ import annotations

from typing import Any


def simulation_confidence(
    *,
    assumptions: dict[str, Any],
    evidence: dict[str, Any],
    stress_completed: bool,
    distribution_ok: bool,
) -> dict[str, Any]:
    score = 0.45
    evidence_items = evidence.get("items") or assumptions.get("evidence") or []
    score += min(0.25, 0.05 * len(evidence_items))
    if assumptions.get("explicitly_recorded"):
        score += 0.1
    if stress_completed:
        score += 0.1
    if distribution_ok:
        score += 0.08
    if assumptions.get("macro_shock") or assumptions.get("replay"):
        score -= 0.05  # wider uncertainty under analogues
    score = round(max(0.2, min(0.92, score)), 3)
    return {
        "confidence": score,
        "drivers": [
            "assumption_clarity",
            "evidence_linkage",
            "stress_coverage",
            "distributional_not_point",
        ],
        "rule": "Confidence reflects simulation integrity — not conviction to trade",
    }
