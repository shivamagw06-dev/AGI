"""FSE-FDO Mission Control façades."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.fdo.alerts import generate_alerts
from financial_statements_engine.fdo.coverage import company_completeness, universe_coverage
from financial_statements_engine.fdo.metrics import live_ingestion_metrics, ops_bundle, source_health_metrics
from financial_statements_engine.fdo.scheduler import plan_gap_schedule
from financial_statements_engine.fdo.schema import (
    ISSUES_RECOMMENDATIONS,
    PHASE,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.util import now_iso


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "phase": PHASE,
        "role": "financial_data_operations",
        "redesigns_engines": False,
        "bypasses_fse": False,
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def dashboard(universe: str = "gold") -> dict[str, Any]:
    cov = universe_coverage(universe)
    ops = ops_bundle()
    schedule = plan_gap_schedule(universe, limit=20)
    alerts = generate_alerts(coverage=cov, ops=ops)
    ing = ops.get("ingestion") or {}
    wf = ops.get("workflows") or {}
    raw = ops.get("raw_evidence") or {}
    most_active = list((raw.get("by_company") or {}).items())[:10]
    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "phase": PHASE,
        "coverage_pct": cov.get("average_coverage_pct"),
        "completeness_pct": cov.get("average_completeness_pct"),
        "workflow_throughput": wf.get("throughput_completed"),
        "queue_depth": wf.get("queue_depth"),
        "dlq_size": wf.get("dlq_size"),
        "average_workflow_duration_ms": wf.get("average_workflow_duration_ms") or ing.get("average_e2e_workflow_duration_ms"),
        "raw_evidence_growth": {
            "files": raw.get("raw_evidence_files"),
            "storage_mb": raw.get("total_storage_mb"),
            "growth_stored_today_proxy": raw.get("growth_stored_today_proxy"),
            "annual_filings": raw.get("annual_filings"),
            "quarterly_filings": raw.get("quarterly_filings"),
        },
        "top_missing_companies": cov.get("top_missing_companies"),
        "most_active_companies": [{"ticker": t, "raw_files": n} for t, n in most_active],
        "source_health": (ops.get("sources") or {}).get("sources"),
        "ingestion": ing,
        "gap_schedule": schedule.get("queue"),
        "alerts": alerts.get("alerts"),
        "universe": universe,
        "issues_recommendations": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def coverage(universe: str = "gold") -> dict[str, Any]:
    return universe_coverage(universe)


def coverage_company(company: str) -> dict[str, Any]:
    return company_completeness(company)


def source_health() -> dict[str, Any]:
    return {"ok": True, "workstream_id": WORKSTREAM_ID, **source_health_metrics()}


def schedule(universe: str = "gold", limit: int = 50) -> dict[str, Any]:
    return plan_gap_schedule(universe, limit=limit)


def alerts(universe: str = "gold") -> dict[str, Any]:
    return generate_alerts(coverage=universe_coverage(universe))


def ingestion_metrics() -> dict[str, Any]:
    return {"ok": True, "workstream_id": WORKSTREAM_ID, **live_ingestion_metrics()}
