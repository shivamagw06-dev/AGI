"""Contradiction engine — score evidence that weakens a hypothesis."""

from __future__ import annotations

from typing import Any


def score_contradictions(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    contradicting = [
        e
        for e in evidence
        if e.get("effect") in ("Questions", "Contradicts", "Refutes")
        or str(e.get("polarity") or "").startswith("contradict")
    ]
    scores = [int(e.get("contradiction_score") or e.get("strength") or 0) for e in contradicting]
    avg = round(sum(scores) / len(scores), 2) if scores else 0.0
    return {
        "contradicting_evidence": [
            {
                "id": e.get("id"),
                "text": e.get("text"),
                "effect": e.get("effect"),
                "contradiction_score": int(e.get("contradiction_score") or e.get("strength") or 0),
                "kind": e.get("kind"),
            }
            for e in contradicting
        ],
        "contradiction_count": len(contradicting),
        "contradiction_score": avg,
        "max_contradiction": max(scores) if scores else 0,
        "has_refutation": any(e.get("effect") == "Refutes" for e in contradicting),
    }
