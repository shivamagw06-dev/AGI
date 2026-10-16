"""DRBE diagnostics — explain report type, sections, owners, suppressions."""

from __future__ import annotations

from typing import Any

from research_blueprint.dynamic_layout import build_research_blueprint


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    plan = build_research_blueprint(question, body)
    return {
        "question": plan.get("question"),
        "report_type": plan.get("report_type"),
        "report_name": plan.get("report_name"),
        "selection_reason": plan.get("selection_reason"),
        "section_order": plan.get("section_order"),
        "section_owner": plan.get("section_owner"),
        "mandatory_sections": plan.get("mandatory_sections"),
        "optional_sections": plan.get("optional_sections"),
        "hidden_sections": plan.get("hidden_sections"),
        "suppressed_sections": plan.get("suppressed_sections"),
        "quality_rules": plan.get("quality_rules"),
        "assignment_book_summary": [
            {
                "owner": a.get("owner"),
                "mission": a.get("mission"),
                "sections": a.get("assigned_sections"),
            }
            for a in ((plan.get("assignment_book") or {}).get("assignments") or [])
        ],
        "visual_view": plan.get("visual_view"),
        "metrics": plan.get("metrics"),
    }
