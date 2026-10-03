"""ICE-01 action item generation from decisions, policy, and conditions."""

from __future__ import annotations

import hashlib
from typing import Any, Sequence

from institutional_committee.models import CommitteeActionItem


def _aid(source: str, key: str) -> str:
    digest = hashlib.sha256(f"{source}|{key}".encode()).hexdigest()[:10]
    return f"action-{source}-{digest}"


def build_action_items(
    *,
    allocation_actions: Sequence[Any] = (),
    policy_actions: Sequence[str] = (),
    policy_violations: Sequence[dict[str, Any]] = (),
    status: str = "",
    recommendation: str = "",
) -> tuple[CommitteeActionItem, ...]:
    items: list[CommitteeActionItem] = []

    for a in allocation_actions:
        if hasattr(a, "to_dict"):
            row = a.to_dict()
        else:
            row = dict(a or {})
        ticker = str(row.get("ticker") or "")
        if not ticker:
            continue
        frm = float(row.get("from_weight") or 0.0)
        to = float(row.get("to_weight") or 0.0)
        if abs(to - frm) < 0.005:
            continue
        verb = "Reduce" if to < frm else "Increase"
        owner = "Portfolio Manager"
        due = "Next rebalance"
        priority = "high" if abs(to - frm) >= 0.03 else "medium"
        items.append(
            CommitteeActionItem(
                action_id=_aid("allocation", f"{ticker}|{frm}|{to}"),
                title=f"{verb} {ticker}",
                detail=f"{ticker} {frm:.0%} → {to:.0%} — {row.get('reason') or recommendation}",
                owner=owner,
                due=due,
                ticker=ticker,
                from_value=frm,
                to_value=to,
                priority=priority,
                source="allocation",
            )
        )

    for v in policy_violations:
        name = str(v.get("name") or "Policy constraint")
        action = str(v.get("required_action") or "")
        ticker = str(v.get("action_ticker") or "")
        items.append(
            CommitteeActionItem(
                action_id=_aid("policy", str(v.get("constraint_id") or name)),
                title=f"Remediate: {name}",
                detail=action or name,
                owner="Portfolio Manager",
                due="Before next committee",
                ticker=ticker,
                from_value=float(v.get("from_value") or v.get("actual") or 0.0),
                to_value=float(v.get("to_value") or v.get("limit") or 0.0),
                priority="critical" if v.get("severity") == "critical" else "high",
                source="policy",
            )
        )

    # Deduplicate by title+detail
    seen: set[str] = set()
    unique: list[CommitteeActionItem] = []
    for item in items:
        key = f"{item.title}|{item.detail}"
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)

    # Soft policy text actions not already covered
    for text in policy_actions:
        if any(text in u.detail or text == u.title for u in unique):
            continue
        unique.append(
            CommitteeActionItem(
                action_id=_aid("policy_text", text),
                title="Policy remediation",
                detail=str(text),
                owner="Investment Team",
                due="Before next committee",
                priority="high",
                source="policy",
            )
        )

    if status == "Deferred":
        unique.append(
            CommitteeActionItem(
                action_id=_aid("followup", recommendation or "defer"),
                title="Prepare deferred decision package",
                detail=f"Clarify allocation actions for '{recommendation}'",
                owner="Investment Team",
                due="Next committee cycle",
                priority="medium",
                source="monitoring",
            )
        )

    if status == "Escalated":
        unique.append(
            CommitteeActionItem(
                action_id=_aid("escalate", recommendation or "risk"),
                title="Escalate to senior investment committee",
                detail="Critical risk posture requires senior review",
                owner="CIO Office",
                due="Immediate",
                priority="critical",
                source="risk",
            )
        )

    return tuple(unique)


def follow_up_schedule(
    *,
    status: str,
    agenda_categories: Sequence[str] = (),
    has_banking: bool = False,
) -> tuple[str, ...]:
    items: list[str] = []
    if status in {"Approved with Conditions", "Pending Review", "Deferred"}:
        items.append("Re-table at next Investment Committee")
    if status == "Rejected":
        items.append("Resubmit after mandate remediation")
    if status == "Escalated":
        items.append("Schedule senior committee session within 5 business days")
    if "policy_violation" in agenda_categories:
        items.append("Policy compliance re-check after rebalance")
    if has_banking or "high_risk" in agenda_categories:
        items.append("Review banking allocation after next RBI meeting")
    if not items:
        items.append("Standard quarterly portfolio review")
    return tuple(items)
