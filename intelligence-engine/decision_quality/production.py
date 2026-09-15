"""IDQ production facade — soft observability surface for routes."""

from __future__ import annotations

from typing import Any

from decision_quality.dashboard import decision_quality_dashboard
from decision_quality.hall import search_hall
from decision_quality.pipeline import run_decision_quality_pipeline
from decision_quality.replay import missing_outcome, replay_decision
from decision_quality.schema import IDQ_VERSION, HALL_CATEGORIES
from decision_quality import store as idq_store


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": "Institutional Decision Quality",
        "layer": "IDQ",
        "version": IDQ_VERSION,
        "observability_only": True,
        "never_reasons": True,
        "not_a_reasoning_engine": True,
        "not_a_planner": True,
        "not_governance": True,
        "not_learning_system": True,
        "phases_1_7_frozen": True,
        "knowledge_factory_frozen": True,
        "historical_sector_macro_frozen": True,
        "hall_categories": list(HALL_CATEGORIES),
        "api_prefix": "/v1/decision-quality",
    }


def dashboard() -> dict[str, Any]:
    # Live ops: auto-prime fixture corpus when store is empty so the website
    # shows operational Decision Quality without a separate cron step.
    if not idq_store.list_decisions():
        try:
            run_decision_quality_pipeline(use_fixtures=True)
        except Exception:
            pass
    return decision_quality_dashboard()


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_decision_quality_pipeline(**kwargs)


def get_decision(decision_id: str) -> dict[str, Any]:
    obj = idq_store.get_decision(decision_id)
    if not obj:
        return {
            "found": False,
            "decision_id": decision_id,
            "reason": "decision_unavailable",
            "insufficient": True,
            "fabricated": False,
        }
    return {"found": True, "decision_id": decision_id, "object": obj}


def list_decisions() -> dict[str, Any]:
    ids = idq_store.list_decisions()
    return {"n": len(ids), "decision_ids": ids, "fabricated": False}


def framework_scorecards() -> dict[str, Any]:
    return idq_store.get_scorecard("framework", "_index") or {
        "found": False,
        "insufficient": True,
        "reason": "scorecards_not_built",
        "fabricated": False,
    }


def sector_scorecards() -> dict[str, Any]:
    return idq_store.get_scorecard("sector", "_index") or {
        "found": False,
        "insufficient": True,
        "reason": "scorecards_not_built",
        "fabricated": False,
    }


def macro_scorecards() -> dict[str, Any]:
    return idq_store.get_scorecard("macro", "_index") or {
        "found": False,
        "insufficient": True,
        "reason": "scorecards_not_built",
        "fabricated": False,
    }


def portfolio_scorecard() -> dict[str, Any]:
    return idq_store.get_scorecard("portfolio", "aggregate") or {
        "found": False,
        "insufficient": True,
        "reason": "scorecards_not_built",
        "fabricated": False,
    }


def calibration() -> dict[str, Any]:
    return idq_store.get_calibration("latest") or {
        "found": False,
        "insufficient": True,
        "reason": "calibration_not_built",
        "fabricated": False,
    }


def hall(category: str | None = None, which: str | None = None) -> dict[str, Any]:
    index = idq_store.get_hall()
    if not index:
        return {"found": False, "insufficient": True, "reason": "hall_not_built", "fabricated": False}
    if category or which:
        return search_hall(category=category, hall=which)
    return {"found": True, **index}


def replay(decision_id: str, as_of: str | None = None) -> dict[str, Any]:
    return replay_decision(decision_id, as_of=as_of)


def outcome_missing(decision_id: str = "dec_tcs_open_no_outcome") -> dict[str, Any]:
    return missing_outcome(decision_id)


def quality_gates() -> dict[str, Any]:
    dash = dashboard()
    kpi = dash.get("kpi") or {}
    fw = framework_scorecards()
    checks = {
        "dashboard_operational": dash.get("status") == "operational",
        "decisions_present": (kpi.get("counts") or {}).get("decisions", 0) > 0,
        "framework_scorecards": bool(fw.get("scorecards")),
        "calibration_present": bool(idq_store.get_calibration("latest")),
        "hall_present": bool(idq_store.get_hall()),
        "observability_only": True,
        "never_reasons": True,
    }
    return {
        "gate": "INSTITUTIONAL_DECISION_QUALITY",
        "version": IDQ_VERSION,
        "passed": all(checks.values()),
        "checks": checks,
        "dashboard": dash,
    }
