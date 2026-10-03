"""Run end-to-end production verification for companies / workflows."""

from __future__ import annotations

import base64
from typing import Any, Callable

from financial_statements_engine.collection.writer import write_evidence
from financial_statements_engine.orchestrator.engine import (
    create_workflow,
    replay_workflow,
    retry_workflow,
    run_workflow,
)
from financial_statements_engine.orchestrator.stages import DEFAULT_STAGE_FNS, StageFn
from financial_statements_engine.orchestrator.store import load_workflow
from financial_statements_engine.raw_evidence import content_sha256
from financial_statements_engine.util import now_iso
from financial_statements_engine.verification.fixtures import filing_meta, verification_filing_bytes
from financial_statements_engine.verification.provenance import generate_provenance
from financial_statements_engine.verification.report import generate_workflow_report
from financial_statements_engine.verification.schema import VERSION, WORKSTREAM_ID
from financial_statements_engine.verification.universe import resolve_verify_universe


def _store_raw_filing(
    ticker: str,
    content: bytes,
    *,
    period_end: str,
    document_type: str,
    source: str,
) -> dict[str, Any]:
    return write_evidence(
        ticker=ticker,
        data=content,
        source=source,
        document_type=document_type,
        period_type="annual",
        period_end=period_end,
        entity=ticker,
    )


def verify_company(
    company: str,
    *,
    period_end: str = "2025-03-31",
    content: bytes | None = None,
    stage_fns: dict[str, StageFn] | None = None,
    sleep_fn: Callable[[float], None] | None = None,
    persist_artifacts: bool = True,
) -> dict[str, Any]:
    """Ingest a verification filing and run the full orchestrated pipeline.

    Uses real ``DEFAULT_STAGE_FNS`` unless ``stage_fns`` is injected (tests).
    Does not change parser/VFQE/warehouse/DME implementations.
    """
    ticker = company.upper().strip()
    meta = filing_meta(ticker, period_end=period_end)
    raw = content if content is not None else verification_filing_bytes(ticker=ticker, period_end=period_end)
    digest = content_sha256(raw)

    write = _store_raw_filing(
        ticker,
        raw,
        period_end=period_end,
        document_type=meta["document_type"],
        source=meta["source"],
    )

    payload = {
        "ticker": ticker,
        "company_id": f"nse:{ticker}",
        "period": period_end,
        "filing_type": meta["filing_type"],
        "document_hash": write.get("content_sha256") or digest,
        "evidence_id": write.get("evidence_id") or f"sha256:{digest}",
        "document_type": meta["document_type"],
        "source": meta["source"],
        # Fallback for environments where raw read path is unavailable
        "inline_bytes_b64": base64.b64encode(raw).decode("ascii"),
    }
    created = create_workflow(payload, auto_queue=True)
    wid = str(created["workflow"]["workflow_id"])
    fns = stage_fns or DEFAULT_STAGE_FNS
    wf = created["workflow"]
    if not created.get("duplicate") or wf.get("state") not in ("COMPLETED", "RUNNING"):
        wf = run_workflow(wid, stage_fns=fns, sleep_fn=sleep_fn or (lambda _s: None))

    report_out = generate_workflow_report(wid, persist=persist_artifacts)
    prov_out = generate_provenance(wid, persist=persist_artifacts)
    report = report_out.get("report") or {}
    checklist = report.get("checklist") or {}

    return {
        "ok": wf.get("state") == "COMPLETED" and bool(checklist.get("all_stages_ok")),
        "workstream_id": WORKSTREAM_ID,
        "version": VERSION,
        "company": ticker,
        "workflow_id": wid,
        "created": created.get("created"),
        "duplicate_workflow": bool(created.get("duplicate")),
        "raw_write": {
            "action": write.get("action"),
            "evidence_id": write.get("evidence_id"),
            "content_sha256": write.get("content_sha256"),
        },
        "workflow_state": wf.get("state"),
        "checklist": checklist,
        "report": report,
        "provenance": prov_out.get("provenance"),
        "hd_dual_write_remains_enabled": True,
        "as_of": now_iso(),
    }


def verify_workflow(
    workflow_id: str,
    *,
    persist_artifacts: bool = True,
) -> dict[str, Any]:
    """Inspect an existing workflow: checklist + report + provenance."""
    wf = load_workflow(workflow_id)
    if not wf:
        return {"ok": False, "error": "workflow_not_found", "workflow_id": workflow_id}
    report_out = generate_workflow_report(workflow_id, persist=persist_artifacts)
    prov_out = generate_provenance(workflow_id, persist=persist_artifacts)
    report = report_out.get("report") or {}
    checklist = report.get("checklist") or {}
    return {
        "ok": wf.get("state") == "COMPLETED" and bool(checklist.get("all_stages_ok")),
        "workstream_id": WORKSTREAM_ID,
        "workflow_id": workflow_id,
        "workflow_state": wf.get("state"),
        "checklist": checklist,
        "report": report,
        "provenance": prov_out.get("provenance"),
        "as_of": now_iso(),
    }


def verify_universe(
    universe: str | list[str] | None = None,
    *,
    stage_fns: dict[str, StageFn] | None = None,
    persist_artifacts: bool = True,
) -> dict[str, Any]:
    tickers = resolve_verify_universe(universe)
    rows = [
        verify_company(t, stage_fns=stage_fns, persist_artifacts=persist_artifacts) for t in tickers
    ]
    ok_n = sum(1 for r in rows if r.get("ok"))
    return {
        "ok": ok_n == len(rows),
        "workstream_id": WORKSTREAM_ID,
        "universe": tickers,
        "n": len(rows),
        "successful": ok_n,
        "failed": len(rows) - ok_n,
        "rows": rows,
        "hd_dual_write_remains_enabled": True,
        "as_of": now_iso(),
    }


def recover_from_dlq(
    workflow_id: str,
    *,
    stage_fns: dict[str, StageFn] | None = None,
    from_stage: str | None = None,
    mode: str = "replay",
) -> dict[str, Any]:
    """Manual recovery: replay (default) or retry a DEAD_LETTER / FAILED workflow."""
    fns = stage_fns or DEFAULT_STAGE_FNS
    if mode == "retry":
        wf = retry_workflow(workflow_id, stage_fns=fns, sleep_fn=lambda _s: None)
    else:
        wf = replay_workflow(workflow_id, from_stage=from_stage, stage_fns=fns, sleep_fn=lambda _s: None)
    report_out = generate_workflow_report(workflow_id, persist=True)
    return {
        "ok": wf.get("state") == "COMPLETED",
        "workflow_id": workflow_id,
        "workflow_state": wf.get("state"),
        "mode": mode,
        "report": report_out.get("report"),
        "as_of": now_iso(),
    }
