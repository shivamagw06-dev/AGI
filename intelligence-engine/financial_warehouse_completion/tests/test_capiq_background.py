from __future__ import annotations

import json
import tempfile

import pytest

from institutional_warehouse import db, gateway
from financial_warehouse_completion import capiq_background as jobs


@pytest.fixture(autouse=True)
def warehouse(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    db.reset_backend()
    db.init(force=True)
    gateway.write(
        "company_master",
        [{"company_id": "AAA", "symbol": "AAA", "company_name": "Alpha Industries", "sector": "Industrials"}],
        source="capital_iq", actor="test",
    )
    yield
    db.reset_backend()


def _job(job_id="capiq_test", status="QUEUED"):
    db.execute(
        "INSERT INTO wh_capiq_import_jobs (job_id, source_file, source_version, code_version, schema_version,"
        " started_at, status, phase, total_rows, approved_rows, quarantined_rows, processed_rows, persisted_rows,"
        " normalized_rows, recalculated_rows, verified_rows, failed_rows, current_chunk, total_chunks, error_count,"
        " heartbeat_at, years) VALUES (?, 'book.xlsx', 'sha', 'code', 'schema', '2026-08-13T00:00:00Z', ?,"
        " 'PERSIST', 2, 2, 0, 0, 0, 0, 0, 0, 0, 0, 2, 0, '2026-08-13T00:00:00Z', ?)",
        (job_id, status, json.dumps([2025])),
    )
    return job_id


def _approved():
    return [{"symbol": "AAA", "fiscal_year": "FY2025", "pat": -10, "assets": 100,
             "equity": -20, "revenue": -5, "statement_type": "UNKNOWN"}]


def test_job_tables_and_progress_are_persistent():
    job_id = _job()
    db.execute(
        "INSERT INTO wh_capiq_import_chunks (chunk_id, job_id, phase, row_start, row_end, status, attempt_count,"
        " processed_count, persisted_count, error_count) VALUES ('c1', ?, 'PERSIST', 0, 2, 'COMPLETED', 1, 2, 2, 0)",
        (job_id,),
    )
    state = jobs.job_status(job_id)
    assert state["status"] == "QUEUED"
    assert state["chunks"][0]["status"] == "COMPLETED"


def test_independent_verifier_detects_missing_approved_record():
    counts = jobs._verification_counts(_approved())
    assert counts == {"expected": 1, "persisted": 0, "normalized": 0, "missing": 1, "duplicate": 0}


def test_negative_equity_revenue_and_earnings_persist_and_normalize():
    result = gateway.write("financials_annual", _approved(), source="capital_iq_workbook",
                           actor="test", reported_unit="inr_million")
    assert result["written"] == 1
    counts = jobs._verification_counts(_approved())
    assert counts["persisted"] == 1
    assert counts["normalized"] == 1


def test_completed_chunk_is_not_selected_for_retry(monkeypatch):
    job_id = _job()
    for chunk_id, status, start in (("done", "COMPLETED", 0), ("todo", "QUEUED", 1)):
        db.execute(
            "INSERT INTO wh_capiq_import_chunks (chunk_id, job_id, phase, row_start, row_end, status, attempt_count,"
            " processed_count, persisted_count, error_count) VALUES (?, ?, 'PERSIST', ?, ?, ?, 0, 0, 0, 0)",
            (chunk_id, job_id, start, start + 1, status),
        )
    called = []
    monkeypatch.setattr(jobs, "_load_approved", lambda job: ([{}, {}], {"audits": [], "identities": []}))
    monkeypatch.setattr(jobs, "_chunk_run", lambda chunk, *_: called.append(chunk["chunk_id"]))
    monkeypatch.setattr(jobs, "_verification_counts", lambda _: {"persisted": 0, "normalized": 0})
    jobs._run(job_id, "test")
    assert called == ["todo"]


def test_failed_chunk_is_reset_for_resume(monkeypatch):
    job_id = _job(status="FAILED")
    db.execute(
        "INSERT INTO wh_capiq_import_chunks (chunk_id, job_id, phase, row_start, row_end, status, attempt_count,"
        " processed_count, persisted_count, error_count) VALUES ('failed', ?, 'PERSIST', 0, 1, 'FAILED', 1, 0, 0, 1)",
        (job_id,),
    )
    monkeypatch.setattr(jobs, "start_worker", lambda *a, **k: {"ok": True})
    state = jobs.resume(job_id)
    chunk = db.query("SELECT status FROM wh_capiq_import_chunks WHERE chunk_id='failed'")[0]
    assert state["status"] == "QUEUED"
    assert chunk["status"] == "QUEUED"


def test_receipt_cannot_be_complete_when_approved_record_is_missing(monkeypatch):
    job = {"job_id": "j", "source_file": "book.xlsx", "source_version": "sha",
           "total_rows": 1, "approved_rows": 1, "quarantined_rows": 0}
    monkeypatch.setattr(jobs, "_verification_counts", lambda _: {
        "expected": 1, "persisted": 0, "normalized": 0, "missing": 1, "duplicate": 0,
    })
    receipt = jobs._verify(job, _approved())
    assert receipt["status"] == "COMPLETED_WITH_WARNINGS"
    assert receipt["verified"] == 0
    assert "missing_approved_records:1" in receipt["quality_warnings"]


def test_quarantine_evidence_is_planned_as_persistent_chunks(monkeypatch):
    monkeypatch.setattr(jobs, "preview", lambda years: {"ok": True})
    monkeypatch.setattr(jobs, "_master_rows", lambda path: [{"fiscal_year": "FY2025"}] * 3)
    monkeypatch.setattr(jobs, "_source_version", lambda: "sha")
    monkeypatch.setattr(jobs, "audit_and_prepare", lambda *a, **k: {
        "accepted": [{"symbol": "AAA"}], "audits": [{"write_status": "READY"},
        {"write_status": "QUARANTINED"}, {"write_status": "QUARANTINED"}], "identities": [],
    })
    monkeypatch.setattr(jobs, "start_worker", lambda *a, **k: {"ok": True})
    created = jobs.create_job(years=[2025])
    phases = [r["phase"] for r in db.query(
        "SELECT phase FROM wh_capiq_import_chunks WHERE job_id=? ORDER BY phase", (created["job_id"],))]
    assert "EVIDENCE" in phases
    assert created["quarantined_rows"] == 2
