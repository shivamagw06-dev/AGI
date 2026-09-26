"""Launch readiness report — evidence before starting v1.1 (L-01)."""

from __future__ import annotations

from typing import Any

from institutional_launch.feature_flags.registry import list_flags
from institutional_launch.feedback.engine import feedback_summary
from institutional_launch.product_metrics.adoption import product_dashboard
from institutional_launch.sla.targets import evaluate_slas


def build_launch_report() -> dict[str, Any]:
    metrics = product_dashboard()
    feedback = feedback_summary()
    slas = evaluate_slas()
    flags = list_flags()

    adopt = metrics.get("adoption") or {}
    ask = metrics.get("ask_agi") or {}
    criteria = {
        "stable_availability": (slas.get("all_met") is True)
        or any(
            c.get("metric") == "availability_pct" and c.get("met")
            for c in slas.get("checks") or []
        ),
        "conformance_100": any(
            c.get("metric") == "architecture_conformance_pct" and c.get("met")
            for c in slas.get("checks") or []
        ),
        "core_workflows_reliable": (ask.get("success_rate") or 0) >= 0.8
        or (ask.get("questions_day") or 0) == 0,  # no traffic yet ≠ fail hard
        "positive_feedback_trend": (feedback.get("helpful_rate") or 1.0) >= 0.6
        or (feedback.get("total") or 0) == 0,
        "v11_flags_still_gated": bool(flags.get("all_disabled")),
    }
    # Ready for v1.1 only when we have evidence of usage + SLAs
    has_usage = (adopt.get("daily_active_users") or 0) > 0 or (ask.get("questions_day") or 0) > 0
    ready = (
        has_usage
        and criteria["conformance_100"]
        and criteria["stable_availability"]
        and criteria["v11_flags_still_gated"]
        and slas.get("breach_count", 0) == 0
    )

    return {
        "title": "AGIB Launch-01 Report",
        "mission": "Validate real analyst workflows before expanding the product",
        "metrics": metrics,
        "feedback": feedback,
        "slas": slas,
        "feature_flags": flags,
        "success_criteria": criteria,
        "has_usage_evidence": has_usage,
        "ready_for_v11": ready,
        "recommendation": (
            "Begin AGIB v1.1 product roadmap (collaboration → automation → markets → integrations → AI productivity)"
            if ready
            else "Continue Launch-01 — gather usage evidence, keep SLAs green, keep v1.1 flags gated"
        ),
        "architecture_frozen": True,
        "adds_intelligence_engines": False,
    }


def launch_center_board() -> dict[str, Any]:
    report = build_launch_report()
    metrics = report["metrics"]
    slas = report["slas"]
    feedback = report["feedback"]
    return {
        "launch_center": True,
        "daily_active_users": (metrics.get("adoption") or {}).get("daily_active_users"),
        "weekly_active_users": (metrics.get("adoption") or {}).get("weekly_active_users"),
        "ask_questions": (metrics.get("ask_agi") or {}).get("questions_day"),
        "ask_p95_ms": (metrics.get("ask_agi") or {}).get("p95_response_ms"),
        "publication_generated": (metrics.get("publications") or {}).get("generated"),
        "helpful_rate": feedback.get("helpful_rate"),
        "feedback_total": feedback.get("total"),
        "sla_all_met": slas.get("all_met"),
        "sla_breach_count": slas.get("breach_count"),
        "sla_checks": slas.get("checks"),
        "feature_flags_all_disabled": (report.get("feature_flags") or {}).get("all_disabled"),
        "ready_for_v11": report.get("ready_for_v11"),
        "recommendation": report.get("recommendation"),
        "funnel": (metrics.get("journey") or {}).get("funnel"),
        "recent_feedback": feedback.get("recent"),
        "architecture_frozen": True,
        "is_usage_validation": True,
        "is_feature_expansion": False,
    }
