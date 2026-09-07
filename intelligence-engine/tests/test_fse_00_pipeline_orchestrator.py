"""FSE-00 — Pipeline Orchestrator tests (coordination only; engines mocked)."""

from __future__ import annotations

import pytest

from financial_statements_engine.collection.event_bus import get_bus, reset_bus_for_tests
from financial_statements_engine.events import EVENT_TYPES
from financial_statements_engine.orchestrator.engine import (
    cancel_workflow,
    create_workflow,
    replay_workflow,
    retry_workflow,
    run_workflow,
)
from financial_statements_engine.orchestrator.production import dashboard, dlq, health, history, queue, workflows
from financial_statements_engine.orchestrator.retry import backoff_seconds, should_retry
from financial_statements_engine.orchestrator.schema import MAX_RETRIES, ORCHESTRATOR_EVENTS, STAGES, WORKSTREAM_ID
from financial_statements_engine.orchestrator.state_machine import IllegalTransition, can_transition, transition
from financial_statements_engine.orchestrator.stages import StageError
from financial_statements_engine.orchestrator.store import load_workflow
from financial_statements_engine.orchestrator.subscriber import bind_orchestrator_subscriber, on_evidence_stored
from financial_statements_engine.orchestrator.workflow_id import make_workflow_id, normalize_identity
from financial_statements_engine.collection.event_bus import publish


@pytest.fixture()
def fse_tmp(tmp_path, monkeypatch):
    monkeypatch.setenv("FSE_STORE_ROOT", str(tmp_path / "fse"))
    reset_bus_for_tests()
    return tmp_path / "fse"


def _payload(**kwargs):
    base = {
        "ticker": "TCS",
        "company_id": "nse:TCS",
        "period": "2025-03-31",
        "filing_type": "annual",
        "document_hash": "abc123hash",
        "evidence_id": "sha256:abc123hash",
    }
    base.update(kwargs)
    return base


def _ok_stages():
    def raw(wf):
        return {"ok": True, "stage": "RAW_EVIDENCE_STORED"}

    def parse(wf):
        return {"ok": True, "stage": "PARSE", "draft_id": "d1", "draft": {"draft_id": "d1", "ticker": wf["ticker"]}}

    def validate(wf):
        return {
            "ok": True,
            "stage": "VALIDATE",
            "validation_id": "val:1",
            "approval_status": "APPROVED",
            "validated_pack": {"validation_id": "val:1", "approval": {"approval_status": "APPROVED"}},
            "draft": (wf.get("artifacts") or {}).get("draft"),
        }

    def warehouse(wf):
        return {"ok": True, "stage": "WAREHOUSE_PUBLISH", "publish_result": {"published": True}}

    def dme(wf):
        return {"ok": True, "stage": "DERIVED_METRICS", "metrics_calculated": 3}

    return {
        "RAW_EVIDENCE_STORED": raw,
        "PARSE": parse,
        "VALIDATE": validate,
        "WAREHOUSE_PUBLISH": warehouse,
        "DERIVED_METRICS": dme,
    }


def test_health(fse_tmp):
    h = health()
    assert h["workstream_id"] == WORKSTREAM_ID
    assert h["coordinates_only"] is True
    assert h["never_parses"] is True
    assert h["auto_start_on_evidence_stored"] is True
    assert h["dead_letter_queue"] is True
    assert h["stages"] == list(STAGES)
    assert "DEAD_LETTER" in h["workflow_states"]


def test_orchestrator_events_registered():
    for e in ORCHESTRATOR_EVENTS:
        assert e in EVENT_TYPES


def test_state_machine_deterministic():
    assert can_transition("RECEIVED", "QUEUED")
    assert transition("QUEUED", "RUNNING") == "RUNNING"
    with pytest.raises(IllegalTransition):
        transition("COMPLETED", "RUNNING")


def test_workflow_creation_and_duplicate(fse_tmp):
    a = create_workflow(_payload(), auto_queue=False)
    assert a["created"] is True
    b = create_workflow(_payload(), auto_queue=False)
    assert b["created"] is False
    assert b["duplicate"] is True
    assert a["workflow"]["workflow_id"] == b["workflow"]["workflow_id"]
    events = {e["event_type"] for e in get_bus().tail(50)}
    assert "workflow.created.v1" in events


def test_full_pipeline_happy_path(fse_tmp):
    created = create_workflow(_payload(), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    wf = run_workflow(wid, stage_fns=_ok_stages())
    assert wf["state"] == "COMPLETED"
    assert wf["current_stage"] is None
    for s in STAGES:
        assert wf["stages"][s]["status"] == "COMPLETED"
    events = [e["event_type"] for e in get_bus().tail(200)]
    assert "stage.started.v1" in events
    assert "stage.completed.v1" in events
    assert "workflow.completed.v1" in events


def test_idempotent_skip_on_replay(fse_tmp):
    calls = {s: 0 for s in STAGES}

    def wrap(name, fn):
        def inner(wf):
            calls[name] += 1
            return fn(wf)

        return inner

    base = _ok_stages()
    fns = {k: wrap(k, v) for k, v in base.items()}
    created = create_workflow(_payload(), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    run_workflow(wid, stage_fns=fns)
    assert all(v == 1 for v in calls.values())
    # second run should skip via completed markers
    run_workflow(wid, stage_fns=fns)
    assert all(v == 1 for v in calls.values())


def test_retry_transient_then_succeed(fse_tmp):
    attempts = {"PARSE": 0}
    base = _ok_stages()

    def flaky_parse(wf):
        attempts["PARSE"] += 1
        if attempts["PARSE"] < 2:
            raise StageError("TIMEOUT", "temporary", transient=True)
        return base["PARSE"](wf)

    fns = dict(base)
    fns["PARSE"] = flaky_parse
    created = create_workflow(_payload(document_hash="retry1"), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    wf = run_workflow(wid, stage_fns=fns, sleep_fn=lambda _s: None)
    assert wf["state"] == "COMPLETED"
    assert attempts["PARSE"] == 2
    assert wf["retries"] >= 1
    events = {e["event_type"] for e in get_bus().tail(200)}
    assert "workflow.retrying.v1" in events


def test_permanent_failure_enters_dead_letter(fse_tmp):
    base = _ok_stages()

    def bad_validate(wf):
        raise StageError("VALIDATION_NOT_APPROVED", "REJECTED", transient=False)

    fns = dict(base)
    fns["VALIDATE"] = bad_validate
    created = create_workflow(_payload(document_hash="fail1"), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    wf = run_workflow(wid, stage_fns=fns)
    assert wf["state"] == "DEAD_LETTER"
    assert "VALIDATE" in (wf.get("failure_reason") or "")
    assert wf.get("dead_letter", {}).get("stage") == "VALIDATE"
    assert wf.get("dead_letter", {}).get("manual_replay") is True
    events = {e["event_type"] for e in get_bus().tail(100)}
    assert "workflow.failed.v1" in events
    assert "workflow.dead_letter.v1" in events
    assert "stage.failed.v1" in events
    board = dlq()
    assert board["n"] >= 1
    assert board["dead_letter_queue"][0]["workflow_id"] == wid
    assert board["dead_letter_queue"][0]["manual_replay_action"]


def test_retry_exhausted_goes_dead_letter(fse_tmp):
    base = _ok_stages()

    def always_timeout(wf):
        raise StageError("TIMEOUT", "still_down", transient=True)

    fns = dict(base)
    fns["PARSE"] = always_timeout
    created = create_workflow(_payload(document_hash="dlq_retry"), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    wf = run_workflow(wid, stage_fns=fns, sleep_fn=lambda _s: None)
    assert wf["state"] == "DEAD_LETTER"
    assert int(wf.get("retries") or 0) >= MAX_RETRIES
    assert wf.get("last_retry_at")
    dash = dashboard()
    assert dash["dead_letter"] >= 1
    assert any(r["workflow_id"] == wid for r in dash["dead_letter_queue"])


def test_replay_from_stage(fse_tmp):
    created = create_workflow(_payload(document_hash="replay1"), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    run_workflow(wid, stage_fns=_ok_stages())
    calls = {"VALIDATE": 0}
    base = _ok_stages()

    def count_validate(wf):
        calls["VALIDATE"] += 1
        return base["VALIDATE"](wf)

    fns = dict(base)
    fns["VALIDATE"] = count_validate
    wf = replay_workflow(wid, from_stage="VALIDATE", stage_fns=fns)
    assert wf["state"] == "COMPLETED"
    assert calls["VALIDATE"] == 1


def test_retry_api_from_dead_letter(fse_tmp):
    base = _ok_stages()

    def bad(wf):
        raise StageError("NETWORK", "down", transient=False)

    # permanent fail → DLQ
    fns = dict(base)
    fns["PARSE"] = bad
    created = create_workflow(_payload(document_hash="retryapi"), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    wf = run_workflow(wid, stage_fns=fns)
    assert wf["state"] == "DEAD_LETTER"
    # operator retry from DLQ
    wf = retry_workflow(wid, stage_fns=_ok_stages())
    assert wf["state"] == "COMPLETED"


def test_auto_start_on_evidence_stored(fse_tmp, monkeypatch):
    """Lifespan binds subscriber; evidence.stored must create + run a workflow."""
    from financial_statements_engine.orchestrator import subscriber as sub

    sub._BOUND = False  # allow re-bind in test
    calls = {"run": 0}
    real_run = run_workflow

    def tracking_run(wid, **kwargs):
        calls["run"] += 1
        return real_run(wid, stage_fns=_ok_stages(), sleep_fn=lambda _s: None)

    monkeypatch.setattr(sub, "run_workflow", tracking_run)
    bind_orchestrator_subscriber()
    publish(
        "evidence.stored",
        {
            "ticker": "INFY",
            "period_end": "2025-03-31",
            "period_type": "annual",
            "document_type": "xbrl",
            "content_sha256": "autostart_hash_1",
            "evidence_id": "sha256:autostart_hash_1",
            "source": "nse_xbrl",
        },
    )
    assert calls["run"] >= 1
    wfs = workflows()
    assert any(w.get("document_hash") == "autostart_hash_1" for w in wfs["workflows"])


def test_cancel(fse_tmp):
    created = create_workflow(_payload(document_hash="cancel1"), auto_queue=False)
    wid = created["workflow"]["workflow_id"]
    wf = cancel_workflow(wid)
    assert wf["state"] == "CANCELLED"


def test_dashboard_and_history(fse_tmp):
    created = create_workflow(_payload(document_hash="dash1"), auto_queue=True)
    run_workflow(created["workflow"]["workflow_id"], stage_fns=_ok_stages())
    dash = dashboard()
    assert dash["completed"] >= 1
    assert "average_duration_ms" in dash
    q = queue()
    assert q["ok"] is True
    hist = history()
    assert hist["ok"] is True
    assert hist["history"]
    wfs = workflows(state="COMPLETED")
    assert wfs["n"] >= 1


def test_backoff_policy():
    assert should_retry(0, error_code="TIMEOUT") is True
    assert should_retry(99, error_code="TIMEOUT") is False
    assert should_retry(0, error_code="VALIDATION_NOT_APPROVED", detail="REJECTED") is False
    assert backoff_seconds(0) == 1.0
    assert backoff_seconds(2) == 4.0


def test_workflow_id_stable():
    a = normalize_identity(ticker="tcs", period="2025-03-31", filing_type="annual", document_hash="h1")
    b = normalize_identity(ticker="TCS", period="2025-03-31", filing_type="annual", document_hash="h1")
    assert make_workflow_id(a) == make_workflow_id(b)


def test_load_after_run(fse_tmp):
    created = create_workflow(_payload(document_hash="load1"), auto_queue=True)
    wid = created["workflow"]["workflow_id"]
    run_workflow(wid, stage_fns=_ok_stages())
    loaded = load_workflow(wid)
    assert loaded is not None
    assert loaded["state"] == "COMPLETED"
