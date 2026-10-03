"""IDE V2 report — constitutional institutional decision package."""

from __future__ import annotations

from typing import Any


def build_report(pack: dict[str, Any]) -> dict[str, Any]:
    return {
        "executive_decision": pack.get("institutional_judgement"),
        "decision_readiness": (pack.get("recommendation_gate") or {}).get("status"),
        "evidence_summary": pack.get("evidence_summary"),
        "reasoning_chain": (pack.get("reasoning") or {}).get("reasoning_chain"),
        "trade_offs": (pack.get("reasoning") or {}).get("trade_offs"),
        "portfolio_context": pack.get("portfolio_context"),
        "scenario_context": (pack.get("reasoning") or {}).get("scenario_impact"),
        "committee_position": pack.get("committee_position"),
        "minority_view": pack.get("minority_view"),
        "conflicts": pack.get("conflicts"),
        "uncertainty": pack.get("uncertainty"),
        "monitoring_plan": pack.get("monitoring"),
        "confidence": pack.get("confidence"),
        "evidence_coverage": (pack.get("evidence_summary") or {}).get("coverage"),
        "learning_history": (pack.get("reasoning") or {}).get("learning_history"),
        "cio_brief": (
            f"Constitutional package for {pack.get('ticker')}: "
            f"{(pack.get('recommendation_gate') or {}).get('status')} · "
            f"conf {(pack.get('confidence') or {}).get('confidence')} · "
            f"conflicts {(pack.get('conflicts') or {}).get('conflict_count')} · "
            f"audit {(pack.get('audit') or {}).get('audit_id')}"
        ),
        "committee_package": {
            "unified": True,
            "replaces_isolated_reports": True,
            "gate": pack.get("recommendation_gate"),
            "conflicts": (pack.get("conflicts") or {}).get("matrix"),
        },
        "portfolio_office": pack.get("portfolio_context"),
        "writer_blocks": {
            "tables": ["weights", "conflict_matrix", "uncertainty_classes", "monitoring_metrics"],
            "sections": [
                "executive_decision",
                "evidence_summary",
                "reasoning_chain",
                "trade_offs",
                "monitoring_plan",
            ],
        },
        "never_recommendation": True,
        "architecture_frozen": True,
    }
