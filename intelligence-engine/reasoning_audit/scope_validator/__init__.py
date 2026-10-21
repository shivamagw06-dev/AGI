"""Analyst scope validation."""

from __future__ import annotations

from typing import Any

_ALLOWED = {
    "Business": {"Business Quality", "Competitive Position"},
    "Financial": {"Financial Quality", "Capital Allocation"},
    "Valuation": {"Valuation"},
    "Macro": {"Macro Alignment"},
    "Portfolio": {"Portfolio Fit", "Valuation"},
    "Portfolio Office": {"Portfolio Fit", "Valuation"},
    "Risk": {"Portfolio Fit", "Financial Quality"},
    "Management": {"Capital Allocation", "Business Quality"},
}


def validate_scope(trace: dict[str, Any]) -> dict[str, Any]:
    debate = trace["stage_data"].get("Debate") or {}
    positions = debate.get("analyst_positions") or []
    rows = []
    violations = []
    for position in positions:
        analyst = str(position.get("analyst") or "")
        pillar = str(position.get("pillar") or "")
        allowed = _ALLOWED.get(analyst, set())
        in_scope = pillar in allowed
        row = {
            "analyst": analyst,
            "assigned_pillar": pillar,
            "allowed_pillars": sorted(allowed),
            "in_scope": in_scope,
        }
        rows.append(row)
        if not in_scope:
            violations.append(row)
    score = (
        sum(1 for row in rows if row["in_scope"]) / len(rows)
        if rows
        else 0.0
    )
    return {
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": bool(rows) and not violations,
        "validations": rows,
        "violations": violations,
        "violation_count": len(violations),
    }
