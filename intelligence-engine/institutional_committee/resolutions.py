"""ICE-01 resolution helpers — conditions and rationale assembly."""

from __future__ import annotations

from typing import Any, Sequence

from institutional_committee.models import CommitteeActionItem, CommitteeVote


def build_rationale(
    *,
    votes: Sequence[CommitteeVote],
    recommendation: str,
    policy_status: str,
    overall_risk: str,
    status: str,
) -> tuple[str, ...]:
    lines: list[str] = [
        f"CIO recommendation: {recommendation or '—'}",
        f"Overall risk: {overall_risk or '—'}; Policy: {policy_status or '—'}",
        f"Committee status: {status}",
    ]
    for v in votes:
        lines.append(f"{v.desk} vote {v.vote}: {v.rationale}")
    return tuple(lines)


def build_conditions(
    *,
    status: str,
    actions: Sequence[CommitteeActionItem],
    policy_violations: Sequence[dict[str, Any]] = (),
) -> tuple[str, ...]:
    if status not in {"Approved with Conditions", "Pending Review"}:
        return ()
    conds: list[str] = []
    for a in actions:
        if a.source in {"policy", "allocation"} and a.priority in {"high", "critical"}:
            conds.append(a.detail or a.title)
    for v in policy_violations:
        text = str(v.get("required_action") or v.get("name") or "")
        if text and text not in conds:
            conds.append(text)
    if not conds and status == "Approved with Conditions":
        conds.append("Complete staged rebalance before declaring full compliance")
    return tuple(conds[:12])


def review_date_for_status(status: str, generated_at: str) -> str | None:
    """Deterministic relative review labels (not calendar scheduling)."""
    if status == "Approved":
        return "Next quarterly review"
    if status in {"Approved with Conditions", "Pending Review"}:
        return "Next committee cycle"
    if status == "Deferred":
        return "After allocation package update"
    if status == "Rejected":
        return "After mandate remediation"
    if status == "Escalated":
        return "Within 5 business days"
    return generated_at or None
