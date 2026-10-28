"""ICE-01 committee agenda generation from risk / policy / decision signals."""

from __future__ import annotations

import hashlib
from typing import Any, Optional, Sequence

from institutional_committee.models import AgendaItem


def _aid(category: str, key: str) -> str:
    digest = hashlib.sha256(f"{category}|{key}".encode()).hexdigest()[:10]
    return f"agenda-{category}-{digest}"


def build_agenda(
    *,
    portfolio_id: str,
    overall_risk: str = "",
    policy_status: str = "",
    violations: Sequence[dict[str, Any]] = (),
    recommendation: str = "",
    allocation_actions: Sequence[dict[str, Any]] = (),
    monitoring_reviews: Sequence[str] = (),
    decision_id: str = "",
    risk_id: str = "",
    policy_id: str = "",
) -> tuple[AgendaItem, ...]:
    items: list[AgendaItem] = []

    if overall_risk in {"High", "Critical"}:
        items.append(
            AgendaItem(
                item_id=_aid("risk", f"{portfolio_id}|{overall_risk}"),
                category="high_risk",
                title=f"High-risk portfolio review ({overall_risk})",
                severity="critical" if overall_risk == "Critical" else "high",
                portfolio_id=portfolio_id,
                reference_id=risk_id,
                detail=f"PRE-01 overall risk {overall_risk}",
            )
        )

    if policy_status in {"Breach", "Critical Breach"} or violations:
        items.append(
            AgendaItem(
                item_id=_aid("policy", f"{portfolio_id}|{policy_status}"),
                category="policy_violation",
                title=f"Active policy violations ({len(violations)})",
                severity="critical" if policy_status == "Critical Breach" else "high",
                portfolio_id=portfolio_id,
                reference_id=policy_id,
                detail=f"PCE-01 status {policy_status}",
            )
        )

    material_actions = [
        a
        for a in allocation_actions
        if abs(float(a.get("to_weight") or 0) - float(a.get("from_weight") or 0)) >= 0.02
    ]
    if material_actions or recommendation in {
        "Reduce Concentration",
        "Increase Diversification",
        "Increase Cash",
        "Reduce Technology",
        "Review Portfolio",
    }:
        items.append(
            AgendaItem(
                item_id=_aid("allocation", f"{portfolio_id}|{recommendation}"),
                category="allocation_change",
                title=f"Material allocation decision: {recommendation or 'review'}",
                severity="medium",
                portfolio_id=portfolio_id,
                reference_id=decision_id,
                detail=f"{len(material_actions)} material allocation actions",
            )
        )

    for rev in list(monitoring_reviews)[:6]:
        items.append(
            AgendaItem(
                item_id=_aid("review", f"{portfolio_id}|{rev}"),
                category="upcoming_review",
                title=str(rev),
                severity="low",
                portfolio_id=portfolio_id,
                reference_id=decision_id,
                detail="Monitoring plan review",
            )
        )

    # Observation dependency placeholder — soft signal when risk/policy elevated
    if overall_risk in {"High", "Critical"} or policy_status in {"Breach", "Critical Breach"}:
        items.append(
            AgendaItem(
                item_id=_aid("observation", portfolio_id),
                category="observation",
                title="Review material observation dependencies",
                severity="medium",
                portfolio_id=portfolio_id,
                detail="Link IO-01 observations for holdings driving risk/policy flags",
            )
        )

    return tuple(items)
