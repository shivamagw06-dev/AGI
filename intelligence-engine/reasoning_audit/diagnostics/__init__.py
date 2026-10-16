"""IRAE diagnostics."""

from __future__ import annotations

from typing import Any


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    from reasoning_audit.production import generate_for_question

    row = generate_for_question(question, body)
    return {
        "ok": True,
        "question": row.get("question"),
        "audit_status": row.get("audit_status"),
        "reasoning_score": row.get("reasoning_score"),
        "traceability_pct": (row.get("traceability") or {}).get(
            "traceability_pct"
        ),
        "orphan_count": (row.get("traceability") or {}).get(
            "orphan_count"
        ),
        "logic_issues": (row.get("logic") or {}).get(
            "inconsistent_conclusions"
        ),
        "assumption_issues": (row.get("assumptions") or {}).get("issues"),
        "calibration_issues": (row.get("calibration") or {}).get("issues"),
        "scope_violations": (row.get("scope") or {}).get("violations"),
        "policy_violations": (row.get("policy") or {}).get("violations"),
        "required_actions": row.get("required_actions"),
        "replay_id": (row.get("reasoning_replay") or {}).get("replay_id"),
        "registry": row.get("registry"),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
        "final_reasoning_certification_gate": True,
    }
