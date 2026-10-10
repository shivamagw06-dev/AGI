"""FSE-02.2 — End-to-End Production Verification tests."""

from __future__ import annotations

import pytest

from financial_statements_engine.collection.event_bus import reset_bus_for_tests
from financial_statements_engine.orchestrator.engine import create_workflow, run_workflow
from financial_statements_engine.orchestrator.schema import MAX_RETRIES, STAGES
from financial_statements_engine.orchestrator.stages import StageError
from financial_statements_engine.orchestrator.store import load_workflow
from financial_statements_engine.raw_evidence import content_sha256, read_raw_bytes
from financial_statements_engine.verification.fixtures import verification_filing_bytes
from financial_statements_engine.verification.production import dashboard, health, sla, workflows
from financial_statements_engine.verification.provenance import generate_provenance
from financial_statements_engine.verification.report import generate_workflow_report
from financial_statements_engine.verification.runner import recover_from_dlq, verify_company, verify_workflow
from financial_statements_engine.verification.schema import WORKSTREAM_ID
from financial_statements_engine.verification.sla import compute_sla_metrics
from financial_statements_engine.verification.store import load_report, load_provenance
from financial_statements_engine.verification.universe import resolve_verify_universe


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    monkeypatch.delenv("FSE_VERIFY_UNIVERSE", raising=False)
    reset_bus_for_tests()
    return tmp_path / "fse"


def _ok_stages():
    def raw(wf):
        return {"ok": True, "stage": "RAW_EVIDENCE_STORED", "raw_acked": True}

    def parse(wf):
        return {
            "ok": True,
            "stage": "PARSE",
            "draft_id": "d1",
            "manifest_id": "m1",
            "draft": {"draft_id": "d1", "manifest_id": "m1", "ticker": wf["ticker"], "ok": True},
        }

    def validate(wf):
        return {
            "ok": True,
            "stage": "VALIDATE",
            "validation_id": "val:1",
            "approval_status": "APPROVED",
            "validated_pack": {
                "validation_id": "val:1",
                "approval": {"approval_status": "APPROVED"},
                "approval_status": "APPROVED",
            },
            "draft": (wf.get("artifacts") or {}).get("draft"),
        }

    def warehouse(wf):
        return {"ok": True, "stage": "WAREHOUSE_PUBLISH", "publish_result": {"published": True, "version": 1}}

    def dme(wf):
        return {"ok": True, "stage": "DERIVED_METRICS", "metrics_calculated": 3}

    return {
        "RAW_EVIDENCE_STORED": raw,
        "PARSE": parse,
        "VALIDATE": validate,
        "WAREHOUSE_PUBLISH": warehouse,
        "DERIVED_METRICS": dme,
    }


def test_health_observability_only(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["changes_parser"] is False
    assert h["changes_vfqe"] is False
    assert h["changes_warehouse"] is False
    assert h["changes_dme"] is False
    assert h["removes_dual_write"] is False
    assert h["hd_dual_write_remains_enabled"] is True


def test_universe_configurable(monkeypatch):
    assert "TCS" in resolve_verify_universe()
    monkeypatch.setenv("FSE_VERIFY_UNIVERSE", "TCS,INFY")
    assert resolve_verify_universe() == ["TCS", "INFY"]
    assert resolve_verify_universe("HDFCBANK") == ["HDFCBANK"]


def test_successful_workflow_report_and_provenance(fse_tmp):
    result = verify_company("TCS", stage_fns=_ok_stages())
    assert result["ok"] is True
    assert result["workflow_state"] == "COMPLETED"
    assert result["checklist"]["all_stages_ok"] is True
    for item in result["checklist"]["items"]:
        assert item["ok"] is True
        assert item["status"] == "COMPLETED"
        assert "started_at" in item or item.get("duration_ms") is not None or item["attempts"] >= 1

    wid = result["workflow_id"]
    report = load_report(wid)
    assert report is not None
    assert report["final_status"] == "COMPLETED"
    assert report["company"] == "TCS"
    assert report["document_hash"]
    assert report["stage_timestamps"]["PARSE"]["status"] == "COMPLETED"
    assert "dlq_status" in report

    prov = load_provenance(wid)
    assert prov is not None
    nodes = [n["node"] for n in prov["lineage"]]
    assert nodes == [
        "workflow",
        "raw_evidence",
        "parse_manifest",
        "coverage_matrix",
        "validation_report",
        "warehouse_version",
        "derived_metrics_version",
    ]
    assert prov["lineage"][0]["present"] is True
    assert prov["lineage"][1]["present"] is True  # raw evidence stored


def test_failed_workflow_and_dlq_transition(fse_tmp):
    base = _ok_stages()
    attempts = {"PARSE": 0}

    def always_timeout(wf):
        attempts["PARSE"] += 1
        raise StageError("TIMEOUT", "synthetic", transient=True)

    fns = dict(base)
    fns["PARSE"] = always_timeout
    result = verify_company("INFY", stage_fns=fns, content=verification_filing_bytes(ticker="INFY"))
    assert result["ok"] is False
    wf = load_workflow(result["workflow_id"])
    assert wf["state"] == "DEAD_LETTER"
    assert attempts["PARSE"] >= MAX_RETRIES + 1
    assert wf.get("dead_letter")
    report = generate_workflow_report(result["workflow_id"])["report"]
    assert report["dlq_status"]["in_dlq"] is True


def test_manual_replay_recovery(fse_tmp):
    base = _ok_stages()
    fail_once = {"n": 0}

    def flaky_validate(wf):
        fail_once["n"] += 1
        if fail_once["n"] <= MAX_RETRIES + 1:
            raise StageError("TIMEOUT", "down", transient=True)
        return base["VALIDATE"](wf)

    # Force permanent path into DLQ with non-retryable then recover via replay
    def permanent(wf):
        raise StageError("VALIDATION_NOT_APPROVED", "REJECTED", transient=False)

    fns = dict(base)
    fns["VALIDATE"] = permanent
    result = verify_company("RELIANCE", stage_fns=fns)
    assert load_workflow(result["workflow_id"])["state"] == "DEAD_LETTER"

    recovered = recover_from_dlq(result["workflow_id"], stage_fns=_ok_stages(), mode="replay", from_stage="VALIDATE")
    assert recovered["ok"] is True
    assert recovered["workflow_state"] == "COMPLETED"


def test_idempotent_replay_no_duplicates(fse_tmp):
    content = verification_filing_bytes(ticker="HDFCBANK")
    a = verify_company("HDFCBANK", content=content, stage_fns=_ok_stages())
    assert a["ok"] is True
    digest = a["raw_write"]["content_sha256"]
    wid = a["workflow_id"]

    b = verify_company("HDFCBANK", content=content, stage_fns=_ok_stages())
    assert b["raw_write"]["action"] == "duplicate_skipped"
    assert b["duplicate_workflow"] is True
    assert b["workflow_id"] == wid
    assert b["raw_write"]["content_sha256"] == digest

    # Raw bytes unchanged / single evidence
    raw = read_raw_bytes("HDFCBANK", a["raw_write"]["evidence_id"])
    assert raw is not None
    assert content_sha256(raw) == digest

    # Re-run completed workflow — stages stay completed (idempotent)
    wf = run_workflow(wid, stage_fns=_ok_stages())
    assert wf["state"] == "COMPLETED"
    for s in STAGES:
        assert wf["stages"][s]["status"] == "COMPLETED"


def test_dashboard_and_sla_aggregation(fse_tmp):
    verify_company("TCS", stage_fns=_ok_stages())
    verify_company("INFY", stage_fns=_ok_stages())
    # one failure
    fns = dict(_ok_stages())
    fns["PARSE"] = lambda wf: (_ for _ in ()).throw(StageError("PARSE_FAILED", "bad", transient=False))
    verify_company("ICICIBANK", stage_fns=fns)

    dash = dashboard()
    assert dash["workstream_id"] == WORKSTREAM_ID
    assert dash["successful_workflows"] >= 2
    assert dash["dlq_workflows"] >= 1
    assert "TCS" in dash["verified_companies"]
    assert dash["hd_dual_write_remains_enabled"] is True
    assert "average_workflow_duration_ms" in dash
    assert "success_rate_pct" in dash

    metrics = compute_sla_metrics()
    assert "queue_depth" in metrics
    assert "p95_workflow_duration_ms" in metrics
    assert "retry_rate_pct" in metrics
    assert "dlq_rate_pct" in metrics
    assert "workflow_success_pct" in metrics
    assert "stage_success_pct" in metrics
    assert sla()["ok"] is True
    assert workflows()["n"] >= 3


def test_verify_workflow_and_report_cli_surfaces(fse_tmp):
    result = verify_company("TCS", stage_fns=_ok_stages())
    checked = verify_workflow(result["workflow_id"])
    assert checked["ok"] is True
    assert checked["report"]["workflow_id"] == result["workflow_id"]
    gen = generate_provenance(result["workflow_id"])
    assert gen["ok"] is True


def test_real_engine_pipeline_e2e(fse_tmp):
    """A real JSON filing traverses DEFAULT_STAGE_FNS end-to-end (no mocks)."""
    result = verify_company("TCS")  # real parser / vfqe / warehouse / dme
    assert result["ok"] is True
    assert result["raw_write"]["action"] in {"stored", "restatement_candidate"}
    assert result["workflow_state"] == "COMPLETED"
    assert result["checklist"]["all_stages_ok"] is True
    assert load_report(result["workflow_id"])["final_status"] == "COMPLETED"
    assert load_provenance(result["workflow_id"])["lineage"][1]["present"] is True
