"""FSE-02.2 Mission Control façades — production verification."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.orchestrator.store import list_workflows, load_workflow
from financial_statements_engine.util import now_iso
from financial_statements_engine.verification.provenance import generate_provenance
from financial_statements_engine.verification.report import generate_workflow_report
from financial_statements_engine.verification.runner import (
    recover_from_dlq,
    verify_company,
    verify_universe,
    verify_workflow,
)
from financial_statements_engine.verification.schema import (
    ISSUES_RECOMMENDATIONS,
    PROGRAMME,
    RECOMMENDATION_POLICY,
    SPEC,
    SUBSYSTEM,
    VERSION,
    WORKSTREAM_ID,
)
from financial_statements_engine.verification.sla import compute_sla_metrics
from financial_statements_engine.verification.store import list_reports, load_provenance, load_report
from financial_statements_engine.verification.universe import resolve_verify_universe, universe_manifest


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "workstream_id": WORKSTREAM_ID,
        "subsystem": SUBSYSTEM,
        "version": VERSION,
        "role": "end_to_end_production_verification",
        "changes_parser": False,
        "changes_vfqe": False,
        "changes_warehouse": False,
        "changes_dme": False,
        "migrates_consumers_from_hd": False,
        "removes_dual_write": False,
        "hd_dual_write_remains_enabled": True,
        "universe": universe_manifest(),
        "issues_recommendations": ISSUES_RECOMMENDATIONS,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def dashboard() -> dict[str, Any]:
    sla = compute_sla_metrics()
    reports = list_reports(limit=500)
    verified_companies = sorted({str(r.get("company") or "").upper() for r in reports if r.get("final_status") == "COMPLETED" and r.get("company")})
    # Also include completed workflows even if report not yet persisted
    for wf in list_workflows(limit=1000):
        if wf.get("state") == "COMPLETED" and wf.get("ticker"):
            verified_companies.append(str(wf["ticker"]).upper())
    verified_companies = sorted(set(verified_companies))

    successful = int((sla.get("counts") or {}).get("completed") or 0)
    failed = int((sla.get("counts") or {}).get("failed") or 0)
    dlq_n = int((sla.get("counts") or {}).get("dead_letter") or 0)
    total = successful + failed + dlq_n
    success_rate = round(100.0 * successful / total, 2) if total else None

    return {
        "status": "ok",
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "verified_companies": verified_companies,
        "verified_companies_n": len(verified_companies),
        "successful_workflows": successful,
        "failed_workflows": failed,
        "dlq_workflows": dlq_n,
        "average_workflow_duration_ms": sla.get("average_workflow_duration_ms"),
        "p95_duration_ms": sla.get("p95_workflow_duration_ms"),
        "average_parse_time_ms": sla.get("average_parse_ms"),
        "average_validation_time_ms": sla.get("average_validation_ms"),
        "average_publish_time_ms": sla.get("average_publish_ms"),
        "average_dme_time_ms": sla.get("average_dme_ms"),
        "current_throughput_per_hour": sla.get("throughput_per_hour_24h"),
        "success_rate_pct": success_rate,
        "sla": sla,
        "universe": resolve_verify_universe(),
        "hd_dual_write_remains_enabled": True,
        "issues_recommendations": False,
        "spec": SPEC,
        "as_of": now_iso(),
    }


def workflows(state: str | None = None, limit: int = 100) -> dict[str, Any]:
    rows = list_workflows(state=state, limit=limit)
    summaries = []
    for wf in rows:
        summaries.append(
            {
                "workflow_id": wf.get("workflow_id"),
                "company": wf.get("ticker"),
                "period": wf.get("period"),
                "state": wf.get("state"),
                "source": wf.get("source"),
                "document_hash": wf.get("document_hash"),
                "retries": wf.get("retries"),
                "in_dlq": wf.get("state") == "DEAD_LETTER",
                "created_at": wf.get("created_at"),
                "finished_at": wf.get("finished_at"),
            }
        )
    return {"ok": True, "n": len(summaries), "workflows": summaries}


def workflow_detail(workflow_id: str) -> dict[str, Any]:
    wf = load_workflow(workflow_id)
    if not wf:
        return {"ok": False, "error": "workflow_not_found", "workflow_id": workflow_id}
    report = load_report(workflow_id) or generate_workflow_report(workflow_id, persist=True).get("report")
    provenance = load_provenance(workflow_id) or generate_provenance(workflow_id, persist=True).get("provenance")
    return {
        "ok": True,
        "workflow": wf,
        "report": report,
        "provenance": provenance,
        "verification": verify_workflow(workflow_id, persist_artifacts=True),
    }


def workflow_report(workflow_id: str) -> dict[str, Any]:
    existing = load_report(workflow_id)
    if existing:
        return {"ok": True, "report": existing, "cached": True}
    return generate_workflow_report(workflow_id, persist=True)


def workflow_provenance(workflow_id: str) -> dict[str, Any]:
    existing = load_provenance(workflow_id)
    if existing:
        return {"ok": True, "provenance": existing, "cached": True}
    return generate_provenance(workflow_id, persist=True)


def run_company(company: str, **kwargs: Any) -> dict[str, Any]:
    return verify_company(company, **kwargs)


def run_universe(universe: str | list[str] | None = None, **kwargs: Any) -> dict[str, Any]:
    return verify_universe(universe, **kwargs)


def recover(workflow_id: str, **kwargs: Any) -> dict[str, Any]:
    return recover_from_dlq(workflow_id, **kwargs)


def sla() -> dict[str, Any]:
    return {"ok": True, "workstream_id": WORKSTREAM_ID, "sla": compute_sla_metrics(), "as_of": now_iso()}
