"""Priority engine — Critical / Important / Supporting / Optional."""

from __future__ import annotations

from typing import Any

_PRIORITY_RANK = {"Critical": 0, "Important": 1, "Supporting": 2, "Optional": 3}


def normalise_priority(priority: str, decision_impact: int | float | None = None) -> str:
    p = (priority or "Supporting").strip().title()
    if p not in _PRIORITY_RANK:
        # Derive from impact when missing/invalid
        impact = int(decision_impact or 5)
        if impact >= 9:
            return "Critical"
        if impact >= 7:
            return "Important"
        if impact >= 4:
            return "Supporting"
        return "Optional"
    # Align priority band with decision impact when provided
    if decision_impact is not None:
        impact = int(decision_impact)
        if impact >= 9:
            return "Critical"
        if impact <= 3 and p == "Critical":
            return "Supporting"
    return p


def prioritise(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scored = []
    for q in questions:
        impact = int(q.get("decision_impact") or 5)
        priority = normalise_priority(str(q.get("priority") or ""), impact)
        scored.append({**q, "priority": priority, "decision_impact": impact})
    scored.sort(
        key=lambda x: (
            _PRIORITY_RANK.get(str(x.get("priority")), 9),
            -int(x.get("decision_impact") or 0),
            str(x.get("id") or ""),
        )
    )
    return scored


def priority_breakdown(questions: list[dict[str, Any]]) -> dict[str, int]:
    out = {k: 0 for k in _PRIORITY_RANK}
    for q in questions:
        p = str(q.get("priority") or "Supporting")
        out[p] = out.get(p, 0) + 1
    return out
