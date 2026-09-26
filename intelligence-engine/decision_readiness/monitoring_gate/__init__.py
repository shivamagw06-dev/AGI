"""Monitoring readiness and objective Go/No-Go decision conditions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any


def evaluate_monitoring(thesis: dict[str, Any]) -> dict[str, Any]:
    monitoring = thesis.get("monitoring") or {}
    conditions = list(monitoring.get("conditions") or [])
    catalysts = list(thesis.get("catalysts") or [])
    breakers = list(thesis.get("thesis_breaking_conditions") or [])
    next_review = monitoring.get("next_review_at") or (
        datetime.now(timezone.utc) + timedelta(days=90)
    ).isoformat()

    # Fall back to thesis structure when the compact soft slice omits conditions.
    if not conditions:
        for pillar in (thesis.get("supporting_pillars") or [])[:7]:
            current = float(pillar.get("strength") or 0.5)
            threshold = 0.45
            conditions.append(
                {
                    "metric": f"{pillar.get('pillar')} score",
                    "pillar": pillar.get("pillar"),
                    "current": current,
                    "current_pct": round(current * 100),
                    "threshold": threshold,
                    "threshold_pct": 45,
                    "distance": round(current - threshold, 4),
                    "distance_pp": round((current - threshold) * 100, 1),
                    "status": "Healthy" if current >= 0.57 else "Watch",
                    "trigger": f"Review if {pillar.get('pillar')} falls below 45%",
                }
            )

    go_no_go = []
    for condition in conditions:
        current = float(condition.get("current") or 0)
        threshold = float(condition.get("threshold") or 0)
        passes = current >= threshold
        go_no_go.append(
            {
                "condition": condition.get("metric"),
                "current": current,
                "current_pct": round(current * 100),
                "threshold": threshold,
                "threshold_pct": round(threshold * 100),
                "distance": round(current - threshold, 4),
                "distance_pp": round((current - threshold) * 100, 1),
                "result": "GO" if passes else "NO-GO",
                "go": passes,
                "failure_action": "Automatic Committee Review",
            }
        )

    active_triggers = [
        condition for condition in conditions if condition.get("trigger")
    ]
    checks = {
        "catalysts_tracked": len(catalysts) >= 3,
        "break_conditions_defined": len(breakers) >= 1,
        "monitoring_triggers_active": len(active_triggers) >= 3,
        "review_schedule_assigned": bool(next_review),
        "evidence_refresh_defined": True,
        "portfolio_review_defined": True,
    }
    score = sum(1 for value in checks.values() if value) / len(checks)
    return {
        "dimension": "Monitoring",
        "score": round(score, 4),
        "score_pct": round(score * 100),
        "passed": all(checks.values()),
        "checks": checks,
        "active_trigger_count": len(active_triggers),
        "decision_conditions": go_no_go,
        "monitoring_plan": {
            "review_frequency": "Quarterly",
            "catalysts": catalysts[:8],
            "break_conditions": breakers[:6],
            "active_triggers": active_triggers[:10],
            "evidence_refresh": "Refresh material evidence each quarter and after catalyst resolution",
            "portfolio_review": "Review sizing after every thesis or pressure-state change",
            "next_review": next_review,
        },
        "breached_conditions": [c for c in go_no_go if not c["go"]],
    }
