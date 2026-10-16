"""Automated debate moderator summary."""

from __future__ import annotations

from typing import Any


def moderate(
    thesis: dict[str, Any],
    agreement: dict[str, Any],
    disagreement: dict[str, Any],
    evidence_conflicts: list[dict[str, Any]],
    assumption_conflicts: list[dict[str, Any]],
    open_questions: list[str],
) -> dict[str, Any]:
    core = thesis.get("core_thesis") or {}
    if isinstance(core, dict):
        core = core.get("statement")
    critical = sorted(
        disagreement.get("conflicts") or [],
        key=lambda row: (-float(row.get("position_gap") or 0), -float(row.get("confidence_gap") or 0)),
    )[:4]
    return {
        "thesis_under_debate": core,
        "agreement_summary": (
            f"{agreement.get('agreement_count', 0)} analysts support the thesis direction; "
            f"shared risks and assumptions remain explicit."
        ),
        "disagreement_summary": (
            f"{disagreement.get('disagreement_count', 0)} pairwise disagreements were identified, "
            f"including {disagreement.get('material_count', 0)} material conflicts."
        ),
        "critical_issues": [
            {
                "topic": row.get("topic"),
                "analysts": [row.get("analyst_a"), row.get("analyst_b")],
                "position_gap": row.get("position_gap"),
            }
            for row in critical
        ],
        "evidence_issues": [
            {
                "topic": c.get("topic"),
                "quality": c.get("evidence_quality"),
                "required": c.get("required_additional_evidence"),
            }
            for c in evidence_conflicts[:4]
        ],
        "assumption_issues": [
            {
                "topic": c.get("topic"),
                "conflict": f"{c.get('assumption_a')} vs {c.get('assumption_b')}",
            }
            for c in assumption_conflicts[:4]
        ],
        "questions_remaining": open_questions[:10],
        "moderator_conclusion": (
            "Advance only after the most material evidence and assumption conflicts are explicitly addressed."
        ),
    }
