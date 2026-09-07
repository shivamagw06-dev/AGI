"""Research status — completion markers, not percentages."""

from __future__ import annotations

from typing import Any

from research_workflow_framework.schema import STATUS_COMPLETE, STATUS_NEEDS_REVIEW, STATUS_PENDING


def build_research_status(
    workflow: dict[str, Any],
    *,
    completed_labels: list[str],
    needs_review_labels: list[str] | None = None,
    evidence_gaps: list[str] | None = None,
) -> dict[str, Any]:
    """Build institutional research status (no percentages)."""
    completed = set(completed_labels or [])
    needs_review = set(needs_review_labels or [])
    items: list[dict[str, Any]] = []

    for row in workflow.get("playbooks") or []:
        label = row.get("status_label") or row.get("label")
        if not label:
            continue
        if label in completed:
            status = STATUS_COMPLETE
            symbol = "✓"
        elif label in needs_review:
            status = STATUS_NEEDS_REVIEW
            symbol = "⚠"
        else:
            status = STATUS_PENDING
            symbol = "□"

        note = None
        if status == STATUS_NEEDS_REVIEW:
            note = f"{label} Needs Review"
        items.append(
            {
                "label": label,
                "playbook_key": row.get("playbook_key"),
                "status": status,
                "symbol": symbol,
                "note": note,
            }
        )

    next_pending = next((i for i in items if i["status"] == STATUS_PENDING), None)
    next_review = next((i for i in items if i["status"] == STATUS_NEEDS_REVIEW), None)
    next_item = next_review or next_pending

    overall = STATUS_COMPLETE
    if evidence_gaps or needs_review:
        overall = STATUS_NEEDS_REVIEW
    elif next_pending:
        overall = STATUS_PENDING

    return {
        "display": "Research Status",
        "items": items,
        "next_activity": next_item.get("label") if next_item else None,
        "overall_status": overall,
        "needs_further_investigation": bool(evidence_gaps or needs_review),
        "evidence_gaps": list(evidence_gaps or [])[:6],
        "no_percentages": True,
    }
