"""Live thesis monitoring conditions with current, threshold and distance."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

_METRICS = {
    "Business Quality": ("Business quality score", 0.45),
    "Financial Quality": ("Financial quality score", 0.45),
    "Capital Allocation": ("Capital allocation score", 0.42),
    "Competitive Position": ("Competitive position score", 0.45),
    "Valuation": ("Valuation support score", 0.40),
    "Macro Alignment": ("Macro alignment score", 0.40),
    "Portfolio Fit": ("Portfolio fit score", 0.40),
}


def build_monitoring_dashboard(
    pillars: list[dict[str, Any]],
    thesis_breaking_conditions: list[dict[str, Any]],
) -> dict[str, Any]:
    conditions = []
    for p in pillars:
        metric, threshold = _METRICS[p["pillar"]]
        current = float(p.get("strength") or 0.5)
        distance = round(current - threshold, 4)
        status = (
            "Healthy"
            if distance >= 0.12
            else "Watch"
            if distance >= 0.04
            else "Pressure"
            if distance >= 0
            else "Breached"
        )
        conditions.append(
            {
                "metric": metric,
                "pillar": p["pillar"],
                "current": round(current, 4),
                "current_pct": round(current * 100),
                "threshold": threshold,
                "threshold_pct": round(threshold * 100),
                "distance": distance,
                "distance_pp": round(distance * 100, 1),
                "status": status,
                "trigger": f"Notify Committee when {metric} falls below {threshold:.0%}",
            }
        )
    return {
        "conditions": conditions,
        "watch_items": [c for c in conditions if c["status"] != "Healthy"],
        "healthy_count": sum(1 for c in conditions if c["status"] == "Healthy"),
        "pressure_count": sum(
            1 for c in conditions if c["status"] in ("Pressure", "Breached")
        ),
        "next_review_at": (
            datetime.now(timezone.utc) + timedelta(days=90)
        ).isoformat(),
        "breaking_conditions": thesis_breaking_conditions,
        "live_monitoring_ready": True,
    }
