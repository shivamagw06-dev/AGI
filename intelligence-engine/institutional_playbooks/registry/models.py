"""Compact playbook constructor."""

from __future__ import annotations

from typing import Any


def playbook(
    playbook_id: str,
    *,
    name: str,
    category: str,
    question_types: list[str],
    cues: list[str],
    frameworks: list[str],
    checklist: list[str],
    procedure: list[str],
    evidence_required: list[str],
    knowledge_objects: list[str],
    common_mistakes: list[str],
    output_structure: list[str],
    sectors: list[str] | None = None,
    confidence_rules: dict[str, Any] | None = None,
    priority: int = 50,
) -> dict[str, Any]:
    """Build one Institutional Analytical Playbook object."""
    steps = []
    for i, label in enumerate(checklist):
        steps.append(
            {
                "step_id": f"S{i+1:02d}",
                "label": label,
                "required": True,
                "status": "pending",
            }
        )
    return {
        "playbook_id": playbook_id,
        "name": name,
        "category": category,
        "question_types": question_types,
        "cues": [c.lower() for c in cues],
        "frameworks": frameworks,
        "sectors": sectors or ["*"],
        "checklist": steps,
        "procedure": procedure,
        "evidence_required": evidence_required,
        "knowledge_objects": knowledge_objects,
        "confidence_rules": confidence_rules
        or {
            "min_checklist_coverage": 0.5,
            "penalty_missing_evidence": 10,
            "boost_full_procedure": 8,
        },
        "common_mistakes": common_mistakes,
        "output_structure": output_structure,
        "priority": priority,
        "fabricated": False,
        "llm_used": False,
    }
