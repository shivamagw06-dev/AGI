"""Support engine — score evidence that strengthens a hypothesis."""

from __future__ import annotations

from typing import Any


def score_support(evidence: list[dict[str, Any]]) -> dict[str, Any]:
    supporting = [
        e
        for e in evidence
        if e.get("effect") in ("Confirms", "Supports", "Weakly Supports")
        or (e.get("polarity") in ("support", "supports") and e.get("effect") != "Neutral")
    ]
    # Prefer effect-tagged
    if not supporting:
        supporting = [e for e in evidence if str(e.get("polarity") or "").startswith("support")]
    scores = [int(e.get("support_score") or e.get("strength") or 0) for e in supporting]
    avg = round(sum(scores) / len(scores), 2) if scores else 0.0
    return {
        "supporting_evidence": [
            {
                "id": e.get("id"),
                "text": e.get("text"),
                "effect": e.get("effect"),
                "support_score": int(e.get("support_score") or e.get("strength") or 0),
                "kind": e.get("kind"),
            }
            for e in supporting
        ],
        "support_count": len(supporting),
        "support_score": avg,
        "max_support": max(scores) if scores else 0,
    }
