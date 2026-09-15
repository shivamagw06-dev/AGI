"""Institutional review — continuous knowledge assessment."""

from __future__ import annotations

from typing import Any

from institutional_knowledge_factory.schema import REVIEW_QUESTIONS


def institutional_review(
    iko: dict[str, Any],
    changes: list[dict[str, Any]] | None = None,
    quality: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate institutional review from IKO state and recent changes."""
    changes = changes or []
    claims = list(iko.get("claims") or [])
    entity_id = iko.get("entity_id") or "ENTITY"

    supported = [c for c in claims if str(c.get("state")) == "SUPPORTED"]
    weakened = [c for c in changes if c.get("impact") == "material_downgrade"]
    strengthened = [c for c in changes if c.get("impact") in {"material_upgrade", "new"}]
    uncertain = [c for c in claims if str(c.get("state")) in {"UNDER_REVIEW", "CONTRADICTED", "UNKNOWN"}]

    monitoring = [
        c for c in claims
        if isinstance(c.get("monitoring"), dict) and c.get("monitoring")
    ]

    research_updates = []
    if quality and quality.get("metrics", {}).get("unknown_count", 0) > 0:
        research_updates.append(f"Resolve {quality['metrics']['unknown_count']} unknown claims on {entity_id}")
    if weakened:
        research_updates.append(f"Review {len(weakened)} weakened assertions on {entity_id}")
    if quality and quality.get("metrics", {}).get("contradiction_count", 0) > 0:
        research_updates.append(f"Resolve {quality['metrics']['contradiction_count']} contradictions")

    return {
        "entity_id": entity_id,
        "review_questions": list(REVIEW_QUESTIONS),
        "what_do_we_now_know": [c.get("statement") for c in supported[:5]],
        "what_changed": [
            f"{c.get('claim_id')}: {c.get('previous_state')} → {c.get('new_state')}"
            for c in changes
        ],
        "what_became_stronger": [c.get("new_assertion") for c in strengthened[:5]],
        "what_became_weaker": [c.get("new_assertion") for c in weakened[:5]],
        "what_became_uncertain": [c.get("statement") for c in uncertain[:5]],
        "what_should_be_monitored": [
            {"claim_id": c.get("claim_id"), "monitoring": c.get("monitoring")}
            for c in monitoring[:5]
        ],
        "what_research_should_be_updated": research_updates,
        "change_count": len(changes),
    }
