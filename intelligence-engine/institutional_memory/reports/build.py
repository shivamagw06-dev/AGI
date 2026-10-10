"""ILM report builder — learning summary for desks / committee / CIO / writer."""

from __future__ import annotations

from typing import Any


def build_report(pack: dict[str, Any]) -> dict[str, Any]:
    ticker = pack.get("ticker")
    learning = pack.get("learning") or {}
    il = learning.get("institutional_learning") or {}
    mistakes = pack.get("mistakes") or {}
    accuracy = pack.get("accuracy") or {}
    theses = pack.get("thesis") or {}
    return {
        "executive_summary": (
            f"Institutional learning for {ticker}: "
            f"{il.get('lesson_count') or 0} lessons, "
            f"{mistakes.get('mistake_count') or 0} classified mistakes, "
            f"thinking_improved={il.get('thinking_improved')}. "
            "Memory is evaluated against outcomes — not archived passively."
        ),
        "historical_thesis": theses.get("evolution"),
        "analyst_evolution": (pack.get("analysts") or {}).get("historical_evolution"),
        "committee_evolution": (pack.get("committee") or {}).get("evolution"),
        "forecast_history": (pack.get("forecasts") or {}).get("history"),
        "portfolio_history": pack.get("portfolio"),
        "management_history": (pack.get("management") or {}).get("history"),
        "decision_journal": (pack.get("decisions") or {}).get("entries"),
        "lessons_learned": learning.get("lessons"),
        "institutional_learning": il,
        "confidence_evolution": (pack.get("confidence") or {}).get("history"),
        "evidence_evolution": (pack.get("evidence") or {}).get("history"),
        "mistake_intelligence": mistakes,
        "accuracy": accuracy,
        "committee": {
            "historical_votes": (pack.get("committee") or {}).get("decisions"),
            "minority_accuracy": (pack.get("committee") or {}).get("minority_accuracy_cases"),
            "consensus_accuracy": (pack.get("committee") or {}).get("consensus_accuracy"),
            "decision_quality": (pack.get("committee") or {}).get("decision_quality"),
        },
        "cio_brief": (
            f"Learning summary for {ticker}: improved={il.get('thinking_improved')}. "
            f"Dominant mistakes: "
            + ", ".join(
                f"{x.get('type')}×{x.get('count')}" for x in (mistakes.get("dominant_error_types") or [])[:3]
            )
            + ". Use lessons to update future FIE priors and committee challenges — never as price calls."
        ),
        "writer_blocks": {
            "historical_comparison_tables": theses.get("evolution"),
            "timeline_charts": (pack.get("timeline") or {}).get("events"),
            "learning_reports": learning.get("lessons"),
            "decision_history": (pack.get("decisions") or {}).get("entries"),
            "mistake_tables": mistakes.get("mistakes"),
        },
        "portfolio_office": {
            "historical_allocation_decisions": (pack.get("portfolio") or {}).get("rebalances"),
            "success_rate": (pack.get("portfolio") or {}).get("success_rate"),
            "mistakes": (pack.get("portfolio") or {}).get("mistakes"),
            "repeated_errors": (pack.get("portfolio") or {}).get("repeated_errors"),
        },
        "text": f"What have we learned on {ticker}? Lessons={il.get('lesson_count')}; mistakes classified via MIE.",
    }
