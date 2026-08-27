"""IVCE diagnostics — explain readiness, warnings, clarifications."""

from __future__ import annotations

from typing import Any

from validation_engine.readiness_gate import validate_request


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    row = validate_request(question, body)
    return {
        "question": row.get("question"),
        "readiness_state": row.get("readiness_state"),
        "overall_readiness": row.get("overall_readiness"),
        "execution_allowed": row.get("execution_allowed"),
        "component_scores": row.get("component_scores"),
        "warnings": row.get("warnings"),
        "clarifications": row.get("clarifications"),
        "ambiguity": row.get("ambiguity"),
        "readiness_memo": row.get("readiness_memo"),
        "question_status": row.get("question_status"),
        "entity_status": row.get("entity_status"),
        "evidence_status": row.get("evidence_status"),
        "policy_status": row.get("policy_status"),
        "metrics": row.get("metrics"),
    }
