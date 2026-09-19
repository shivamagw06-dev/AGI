"""BBCE diagnostics — explain belief updates and drift."""

from __future__ import annotations

from typing import Any


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    from belief_engine.production import generate_for_question

    row = generate_for_question(question, body)
    return {
        "ok": True,
        "question": row.get("question"),
        "belief_count": row.get("belief_count"),
        "beliefs": [
            {
                "hypothesis_id": b.get("hypothesis_id"),
                "hypothesis": b.get("hypothesis"),
                "prior_belief": b.get("prior_belief"),
                "posterior_belief": b.get("posterior_belief"),
                "belief_state": b.get("belief_state"),
                "confidence": b.get("confidence"),
                "uncertainty": (b.get("uncertainty") or {}).get("overall_uncertainty"),
                "drift": b.get("drift"),
                "calibration": (b.get("calibration") or {}).get("confidence_band"),
            }
            for b in (row.get("beliefs") or [])
        ],
        "drift_summary": row.get("drift_summary"),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
    }
