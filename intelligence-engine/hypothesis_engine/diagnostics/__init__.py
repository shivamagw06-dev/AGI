"""IHG diagnostics — explain generated hypotheses and quality compliance."""

from __future__ import annotations

from typing import Any


def diagnose(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    # Lazy import avoids circular dependency with production.
    from hypothesis_engine.production import generate_for_question

    row = generate_for_question(question, body)
    return {
        "ok": True,
        "question": row.get("question"),
        "hypotheses": [
            {
                "id": h.get("id"),
                "type": h.get("type"),
                "statement": h.get("statement") or h.get("hypothesis"),
                "confidence": h.get("confidence"),
                "confidence_pct": h.get("confidence_pct"),
                "responsible_analysts": h.get("responsible_analysts"),
                "analyst_owner": h.get("analyst_owner"),
                "required_evidence": h.get("required_evidence"),
                "status": h.get("status"),
                "quality_compliant": h.get("quality_compliant"),
                "failed_rules": (h.get("quality_rules") or {}).get("failed_rules"),
                "assumptions": h.get("assumptions"),
            }
            for h in (row.get("hypotheses") or [])
        ],
        "ranking_by_type": row.get("ranking"),
        "evidence_map": row.get("evidence_map"),
        "contradictions": row.get("contradictions"),
        "overall_confidence": row.get("overall_confidence"),
        "metrics": row.get("metrics"),
        "five_quality_rules": row.get("five_quality_rules"),
        "not_a_top_level_intelligence_layer": True,
    }


def build_diagnostics(plan: dict[str, Any]) -> dict[str, Any]:
    """Lightweight diagnostics from an existing plan row."""
    hyps = plan.get("hypotheses") or []
    return {
        "hypothesis_count": len(hyps),
        "quality_compliant_count": sum(1 for h in hyps if h.get("quality_compliant")),
        "ranking_by_type": plan.get("ranking") or plan.get("ranking_by_type"),
        "contradiction_count": (plan.get("contradictions") or {}).get("contradiction_count"),
        "overall_confidence": plan.get("overall_confidence"),
        "generation_ms": plan.get("generation_ms"),
    }
