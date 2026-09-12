"""Evidence map — required evidence linked to each hypothesis."""

from __future__ import annotations

from typing import Any


def build_evidence_map(hypotheses: list[dict[str, Any]]) -> dict[str, Any]:
    by_hypothesis = []
    all_evidence: list[str] = []
    for h in hypotheses:
        items = list(h.get("required_evidence") or [])
        all_evidence.extend(items)
        by_hypothesis.append(
            {
                "hypothesis_id": h.get("id"),
                "type": h.get("type"),
                "required_evidence": items,
                "responsible_analysts": h.get("responsible_analysts"),
            }
        )
    # unique preserve order
    seen = set()
    unique = []
    for e in all_evidence:
        if e not in seen:
            seen.add(e)
            unique.append(e)
    return {
        "by_hypothesis": by_hypothesis,
        "unique_evidence_required": unique,
        "evidence_count": len(unique),
        "minimum_independent_evidence_target": max(5, len(unique)),
    }
