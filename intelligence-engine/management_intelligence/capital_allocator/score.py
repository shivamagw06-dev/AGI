"""Capital allocation quality — value creating / neutral / destructive."""

from __future__ import annotations

from typing import Any

_VAL = {"value_creating": 90.0, "neutral": 60.0, "value_destructive": 20.0, "unknown": 50.0}


def capital_allocation_score(decisions: list[dict[str, Any]], acquisitions: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    acquisitions = acquisitions or []
    vals = [_VAL.get(str(d.get("value_label") or "unknown"), 50.0) for d in decisions]
    for a in acquisitions:
        impact = str(a.get("shareholder_value_impact") or "unknown")
        if impact == "needs_monitoring":
            vals.append(55.0)
        elif impact in {"positive", "value_creating"}:
            vals.append(85.0)
        elif impact in {"negative", "value_destructive"}:
            vals.append(25.0)
        else:
            vals.append(50.0)
    score = round(sum(vals) / len(vals), 1) if vals else 55.0
    return {
        "capital_allocation": score,
        "decisions": decisions,
        "acquisitions": acquisitions,
        "value_creating": sum(1 for d in decisions if d.get("value_label") == "value_creating"),
        "value_destructive": sum(1 for d in decisions if d.get("value_label") == "value_destructive"),
        "n": len(decisions) + len(acquisitions),
    }
