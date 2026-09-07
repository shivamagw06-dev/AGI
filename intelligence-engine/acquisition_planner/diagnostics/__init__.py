"""IAPE diagnostics — explain every acquire / reuse / skip decision."""

from __future__ import annotations

from typing import Any

from acquisition_planner.acquisition_plan import build_acquisition_plan


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = build_acquisition_plan(question, body)
    return {
        "question": plan.get("question"),
        "primary_objective": plan.get("primary_objective"),
        "evidence_required": [r.get("evidence_key") for r in (plan.get("required_data") or [])],
        "selected_providers": plan.get("selected_providers"),
        "reuse_internal_layers": plan.get("reuse_internal_layers"),
        "skipped_apis": plan.get("skipped_apis"),
        "fallback_chains": plan.get("fallback_chains"),
        "evidence_budget": plan.get("evidence_budget"),
        "freshness_plan": plan.get("freshness_plan"),
        "authority_plan": plan.get("authority_plan"),
        "expected_runtime": plan.get("expected_runtime"),
        "expected_quality": plan.get("expected_quality"),
        "confidence": plan.get("confidence"),
        "visual_plan": plan.get("visual_plan"),
        "metrics": plan.get("metrics"),
        "why": [
            {
                "step": step.get("order"),
                "action": step.get("action"),
                "provider": step.get("provider"),
                "evidence": step.get("evidence_key"),
                "purpose": step.get("why"),
            }
            for step in (plan.get("executed_acquisitions") or [])
        ],
    }
