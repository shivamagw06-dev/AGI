"""IDRE diagnostics."""

from __future__ import annotations

from typing import Any


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    from decision_readiness.production import generate_for_question

    row = generate_for_question(question, body)
    return {
        "ok": True,
        "question": row.get("question"),
        "decision_status": row.get("decision_status"),
        "readiness_score": row.get("readiness_score"),
        "heat_map": row.get("decision_heat_map"),
        "failed_gates": [
            name
            for name, gate in (row.get("dimensions") or {}).items()
            if not gate.get("passed")
        ],
        "capital_allocation_readiness": row.get(
            "capital_allocation_readiness"
        ),
        "missing_evidence": row.get("missing_evidence"),
        "open_questions": row.get("open_questions"),
        "remaining_conflicts": row.get("remaining_conflicts"),
        "audit": row.get("audit"),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
        "final_pre_committee_quality_gate": True,
    }
