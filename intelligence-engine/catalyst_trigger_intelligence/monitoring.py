"""Monitoring Office integration — CTI outputs prioritise reviews and alerts."""

from __future__ import annotations

from typing import Any

from catalyst_trigger_intelligence.evaluation import evaluate_company, trigger_matrix_report
from catalyst_trigger_intelligence.schema import CTI_VERSION
from catalyst_trigger_intelligence.triggers import build_company_triggers


def monitoring_pack(
    ticker: str,
    *,
    observations: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Package CTI state for Institutional Monitoring Office consumption."""
    triggers = build_company_triggers(ticker, persist=True)
    evaluation = evaluate_company(ticker, observations=observations or {}, auto_confirm=bool(observations))
    high_priority = [
        t
        for t in triggers.get("triggers") or []
        if t.get("priority") in {"Critical", "High"} and t.get("state") in {"Scheduled", "Watching", "Triggered", "Confirmed"}
    ]
    upcoming = sorted(
        triggers.get("triggers") or [],
        key=lambda t: (0 if t.get("priority") == "Critical" else 1 if t.get("priority") == "High" else 2, t.get("expected_date") or ""),
    )[:12]

    events = []
    for r in evaluation.get("results") or []:
        if r.get("condition_met") is True:
            assessment = r.get("scenario_assessment") or {}
            events.append(
                {
                    "type": "cti_trigger_activated",
                    "trigger_id": r.get("trigger_id"),
                    "entity": r.get("entity"),
                    "severity": "critical" if assessment.get("recommended_action") == "Committee Review" else "high",
                    "recommended_action": assessment.get("recommended_action") or "Review",
                    "scenario_assessment": assessment,
                    "mutates_thesis": False,
                    "source": "CTI",
                }
            )

    return {
        "module": "CTI→IMO",
        "ticker": (ticker or "").upper(),
        "cti_version": CTI_VERSION,
        "upcoming_catalysts": upcoming,
        "active_triggers": [t for t in triggers.get("triggers") or [] if t.get("state") == "Watching"],
        "high_priority_events": high_priority,
        "activated_events": events,
        "trigger_matrix": trigger_matrix_report(ticker).get("matrix"),
        "review_queue": [
            {
                "entity": (ticker or "").upper(),
                "reason": e.get("recommended_action"),
                "trigger_id": e.get("trigger_id"),
                "priority": e.get("severity"),
            }
            for e in events
        ],
        "institutional_guarantee": (
            "Monitoring Office consumes CTI to prioritise reviews. "
            "Never auto-rewrites investment theses or governance decisions."
        ),
        "mutates_thesis": False,
        "mutates_governance": False,
    }


def emit_to_imo(ticker: str, *, observations: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    """Soft-wire into IMO when available; always returns CTI monitoring pack."""
    pack = monitoring_pack(ticker, observations=observations)
    imo_result: dict[str, Any] | None = None
    try:
        from institutional_monitoring_office.production import create_api

        # Create review-only monitoring events for activated CTI triggers
        for event in pack.get("activated_events") or []:
            imo_result = create_api(
                {
                    "question": f"CTI trigger activated for {ticker}: {event.get('trigger_id')}",
                    "idea": {"idea_id": f"CTI-{ticker}", "ticker": ticker},
                    "thesis": {"thesis_id": f"THESIS-{ticker}", "ticker": ticker},
                    "decision": {"decision_id": f"DEC-{ticker}"},
                    "metadata": {
                        "source": "CTI",
                        "cti_event": event,
                        "recommended_action": event.get("recommended_action"),
                    },
                }
            )
    except Exception as exc:  # noqa: BLE001
        imo_result = {"imo_soft_wire": "unavailable", "error": str(exc)}
    return {**pack, "imo": imo_result}
