"""Monitoring engine — watch items, metrics, review date, triggers."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any


def build_monitoring_plan(
    *,
    ticker: str,
    gate: dict[str, Any],
    inputs: dict[str, Any],
    conflicts: dict[str, Any],
) -> dict[str, Any]:
    summary = inputs.get("stack_summary") or {}
    review = (date.today() + timedelta(days=30)).isoformat()
    watch = [
        "FIL/FDI material change signal",
        "Management guidance vs MII trust score",
        "ACI manipulation / quality drift",
        "FIE scenario probability mass shift",
        "SSL assumption drift vs recorded baseline",
    ]
    if conflicts.get("conflict_count", 0):
        watch.append("Unresolved conflict matrix items")
    metrics = [
        {"metric": "forecast_confidence", "baseline": summary.get("forecast_confidence")},
        {"metric": "portfolio_quality", "baseline": summary.get("portfolio_quality")},
        {"metric": "memory_lesson_count", "baseline": summary.get("memory_lesson_count")},
        {"metric": "simulation_expected_return", "baseline": summary.get("simulation_expected_return")},
    ]
    triggers = [
        "Automatic re-evaluation on FDI material change",
        "Automatic re-evaluation if ACI manipulation risk elevates",
        "Automatic re-evaluation if SSL stress bands breach p05 monitor",
        "Committee review if conflict_count increases",
    ]
    return {
        "ticker": (ticker or "").upper(),
        "watch_items": watch,
        "key_metrics": metrics,
        "review_date": review,
        "risk_triggers": triggers,
        "catalysts": [
            summary.get("forecast_most_likely") or "scenario_path_update",
            "earnings_print",
            "policy_rate_decision",
        ],
        "recommendation_status": gate.get("status"),
        "automatic_reevaluation": True,
        "rule": "Every decision creates a monitoring plan with re-evaluation triggers",
    }
