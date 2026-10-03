"""Management DNA — evidence-driven operating-style classification.

Evolves as guidance accuracy, capital allocation and execution outcomes accumulate.
Not a static label.
"""

from __future__ import annotations

from typing import Any

from management_intelligence.schema import DNA_ARCHETYPES


def classify_dna(
    *,
    priors: list[str] | None,
    capital: dict[str, Any],
    execution: dict[str, Any],
    guidance: dict[str, Any],
    credibility: dict[str, Any],
    acquisitions: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    scores = {a: 0.0 for a in DNA_ARCHETYPES}
    for p in priors or []:
        if p in scores:
            scores[p] += 25.0

    # Capital Allocator — value-creating capital decisions, buybacks/dividends discipline
    scores["Capital Allocator"] += float(capital.get("capital_allocation") or 0) * 0.25
    if (capital.get("value_creating") or 0) >= 1:
        scores["Capital Allocator"] += 10
        scores["Value Creator"] += 15

    if (capital.get("value_destructive") or 0) >= 1:
        scores["Value Destroyer"] += 30
        scores["Empire Builder"] += 10

    # Operator — execution delivery
    scores["Operator"] += float(execution.get("execution") or 0) * 0.30
    if (execution.get("completed") or 0) >= 1:
        scores["Operator"] += 8

    # Growth Builder — growth guidance delivered / initiatives exceeded
    if any(i.get("status") == "exceeded" for i in execution.get("items") or []):
        scores["Growth Builder"] += 20
    if (guidance.get("historical_accuracy") or 0) >= 70:
        scores["Growth Builder"] += 8
        scores["Professional Steward"] += 10

    # Professional Steward — credibility + governance-friendly profile
    scores["Professional Steward"] += float(credibility.get("credibility") or 0) * 0.20

    # Empire Builder / Turnaround — acquisitions
    acq = acquisitions or capital.get("acquisitions") or []
    if acq:
        scores["Empire Builder"] += 15
        if any(a.get("integration_progress", "").startswith("legal complete") for a in acq):
            scores["Turnaround Specialist"] += 8
        if any(a.get("shareholder_value_impact") == "needs_monitoring" for a in acq):
            scores["Empire Builder"] += 5
            scores["Value Destroyer"] += 5

    # Financial Engineer — sparse in V1 unless capital raises dominate
    if any("raise" in str(d.get("decision") or "").lower() for d in capital.get("decisions") or []):
        scores["Financial Engineer"] += 12

    # Founder-led Visionary — not default for professional banks
    # Value Creator already boosted

    ranked = sorted(scores.items(), key=lambda kv: -kv[1])
    primary = ranked[0][0]
    secondary = [a for a, s in ranked[1:4] if s > 0]

    return {
        "primary": primary,
        "secondary": secondary,
        "scores": {k: round(v, 1) for k, v in ranked if v > 0},
        "evolving": True,
        "rule": "DNA is evidence-driven and must evolve with new decisions/outcomes — not a permanent brand label",
        "archetypes": list(DNA_ARCHETYPES),
    }
