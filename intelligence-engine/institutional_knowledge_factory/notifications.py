"""Research workflow notifications."""

from __future__ import annotations

from typing import Any


def notify_research_workflows(
    entity_id: str,
    *,
    changes: list[dict[str, Any]] | None = None,
    thesis: dict[str, Any] | None = None,
    review: dict[str, Any] | None = None,
    quality: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Emit research notifications for downstream workflows."""
    notifications: list[dict[str, Any]] = []
    changes = changes or []

    for change in changes:
        if change.get("impact") in {"material_upgrade", "material_downgrade", "new"}:
            notifications.append({
                "type": "assertion_change",
                "entity_id": entity_id.upper(),
                "claim_id": change.get("claim_id"),
                "impact": change.get("impact"),
                "message": f"Assertion {change.get('claim_id')} changed: {change.get('impact')}",
                "priority": "high" if change.get("impact") == "material_downgrade" else "medium",
            })

    if thesis and thesis.get("re_evaluated"):
        notifications.append({
            "type": "thesis_re_evaluation",
            "entity_id": entity_id.upper(),
            "thesis_status": thesis.get("thesis_status"),
            "message": f"Investment thesis re-evaluated for {entity_id}",
            "priority": "high",
        })

    if review:
        for item in review.get("what_research_should_be_updated") or []:
            notifications.append({
                "type": "research_update",
                "entity_id": entity_id.upper(),
                "message": item,
                "priority": "medium",
            })

    if quality:
        status = (quality.get("metrics") or {}).get("review_status")
        if status in {"needs_review", "stale"}:
            notifications.append({
                "type": "quality_alert",
                "entity_id": entity_id.upper(),
                "review_status": status,
                "message": f"Knowledge quality for {entity_id}: {status}",
                "priority": "high" if status == "needs_review" else "medium",
            })

    return notifications
