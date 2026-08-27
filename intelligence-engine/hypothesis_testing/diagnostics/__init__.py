"""IHTE diagnostics — explain tested hypotheses and reasoning ledgers."""

from __future__ import annotations

from typing import Any


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    from hypothesis_testing.production import generate_for_question

    row = generate_for_question(question, body)
    return {
        "ok": True,
        "question": row.get("question"),
        "tested_count": row.get("tested_count"),
        "matrix": [
            {
                "id": h.get("id"),
                "hypothesis": h.get("hypothesis"),
                "support_score": h.get("support_score"),
                "contradiction_score": h.get("contradiction_score"),
                "missing_evidence": h.get("missing_evidence"),
                "updated_probability": h.get("updated_probability"),
                "status": h.get("status"),
                "confidence": h.get("confidence"),
                "effect_breakdown": h.get("effect_breakdown"),
                "ledger_events": len(h.get("reasoning_ledger") or []),
            }
            for h in (row.get("tested_hypotheses") or [])
        ],
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
    }
