"""Pipeline Orchestrator engine — coordinates stages; never implements engine logic."""

from __future__ import annotations

import time
from typing import Any, Callable

from financial_statements_engine.collection.event_bus import publish
from financial_statements_engine.orchestrator.retry import backoff_seconds, should_retry
from financial_statements_engine.orchestrator.schema import (
    ORCH_VERSION,
    STAGES,
    WORKSTREAM_ID,
)
from financial_statements_engine.orchestrator.state_machine import IllegalTransition, transition
from financial_statements_engine.orchestrator.stages import (
    DEFAULT_STAGE_FNS,
    IDEMPOTENCY_CHECKS,
    StageError,
    next_stage,
    stage_already_completed,
)
from financial_statements_engine.orchestrator.store import load_workflow, save_workflow
from financial_statements_engine.orchestrator.workflow_id import identity_from_payload, make_workflow_id
from financial_statements_engine.util import now_iso

StageFn = Callable[[dict[str, Any]], dict[str, Any]]


def _emit(event_type: str, payload: dict[str, Any]) -> None:
    try:
        publish(event_type, payload)
    except ValueError:
        # Event catalogue not yet extended in some test harnesses — ignore
        pass


def _new_stage_map() -> dict[str, dict[str, Any]]:
    return {s: {"status": "PENDING", "attempts": 0, "started_at": None, "finished_at": None} for s in STAGES}


def create_workflow(payload: dict[str, Any], *, auto_queue: bool = True) -> dict[str, Any]:
    """Create or return existing workflow for identity. Duplicate-safe."""
    identity = identity_from_payload(payload)
    wid = make_workflow_id(identity)
    existing = load_workflow(wid)
    if existing is not None:
        return {"ok": True, "created": False, "workflow": existing, "duplicate": True}

    wf: dict[str, Any] = {
        "workflow_id": wid,
        "workstream_id": WORKSTREAM_ID,
        "orch_version": ORCH_VERSION,
        **identity,
        "evidence_id": payload.get("evidence_id"),
        "document_type": payload.get("document_type"),
        "source": payload.get("source"),
        "inline_bytes_b64": payload.get("inline_bytes_b64"),
        "state": "RECEIVED",
        "current_stage": STAGES[0],
        "stages": _new_stage_map(),
        "artifacts": {},
        "retries": 0,
        "failure_reason": None,
        "created_at": now_iso(),
        "updated_at": now_iso(),
        "started_at": None,
        "finished_at": None,
        "history": [{"state": "RECEIVED", "at": now_iso()}],
    }
    save_workflow(wf)
    _emit("workflow.created.v1", {"workflow_id": wid, "ticker": wf.get("ticker"), "period": wf.get("period")})
    if auto_queue:
        wf = enqueue(wid)
        return {"ok": True, "created": True, "workflow": wf, "duplicate": False}
    return {"ok": True, "created": True, "workflow": wf, "duplicate": False}


def _set_state(wf: dict[str, Any], target: str) -> dict[str, Any]:
    prev = str(wf.get("state"))
    wf["state"] = transition(prev, target)
    wf["updated_at"] = now_iso()
    wf.setdefault("history", []).append({"state": target, "from": prev, "at": wf["updated_at"]})
    return wf


def enqueue(workflow_id: str) -> dict[str, Any]:
    wf = load_workflow(workflow_id)
    if not wf:
        raise KeyError(f"workflow_not_found:{workflow_id}")
    if wf["state"] in ("COMPLETED", "CANCELLED"):
        return wf
    if wf["state"] == "RECEIVED":
        _set_state(wf, "QUEUED")
    elif wf["state"] in ("FAILED", "RETRYING", "DEAD_LETTER"):
        _set_state(wf, "QUEUED")
    save_workflow(wf)
    _emit("workflow.queued.v1", {"workflow_id": workflow_id})
    return wf


def run_workflow(
    workflow_id: str,
    *,
    stage_fns: dict[str, StageFn] | None = None,
    max_stages: int | None = None,
    sleep_fn: Callable[[float], None] | None = None,
) -> dict[str, Any]:
    """Execute pending stages in order until completed/failed or max_stages hit."""
    fns = stage_fns or DEFAULT_STAGE_FNS
    sleeper = sleep_fn or (lambda s: None)  # tests inject; prod may sleep on retry
    wf = load_workflow(workflow_id)
    if not wf:
        raise KeyError(f"workflow_not_found:{workflow_id}")
    if wf["state"] == "CANCELLED":
        return wf
    if wf["state"] == "COMPLETED":
        return wf

    if wf["state"] in ("RECEIVED", "FAILED", "RETRYING", "DEAD_LETTER"):
        wf = enqueue(workflow_id)

    if wf["state"] == "QUEUED":
        _set_state(wf, "RUNNING")
        wf["started_at"] = wf.get("started_at") or now_iso()
        save_workflow(wf)

    executed = 0
    stage = wf.get("current_stage") or STAGES[0]

    while stage:
        if max_stages is not None and executed >= max_stages:
            break

        # Idempotency: skip completed stages
        if stage_already_completed(wf, stage) or IDEMPOTENCY_CHECKS.get(stage, lambda _w: False)(wf):
            bucket = wf["stages"].setdefault(stage, {})
            if bucket.get("status") != "COMPLETED":
                bucket.update(
                    {
                        "status": "COMPLETED",
                        "finished_at": now_iso(),
                        "skipped_idempotent": True,
                    }
                )
                _emit("stage.skipped.v1", {"workflow_id": workflow_id, "stage": stage})
            nxt = next_stage(stage)
            wf["current_stage"] = nxt
            save_workflow(wf)
            stage = nxt
            continue

        bucket = wf["stages"].setdefault(stage, {"attempts": 0})
        bucket["status"] = "RUNNING"
        bucket["started_at"] = now_iso()
        bucket["attempts"] = int(bucket.get("attempts") or 0) + 1
        wf["current_stage"] = stage
        save_workflow(wf)
        _emit("stage.started.v1", {"workflow_id": workflow_id, "stage": stage, "attempt": bucket["attempts"]})

        fn = fns.get(stage)
        if fn is None:
            return _fail(wf, stage, "NO_STAGE_FN", f"no executor for {stage}", transient=False)

        t0 = time.time()
        try:
            result = fn(wf)
            duration_ms = int((time.time() - t0) * 1000)
            bucket["status"] = "COMPLETED"
            bucket["finished_at"] = now_iso()
            bucket["duration_ms"] = duration_ms
            bucket["result_summary"] = {k: result.get(k) for k in result if k not in ("draft", "validated_pack", "result")}
            # stash artifacts for downstream stages
            arts = wf.setdefault("artifacts", {})
            if result.get("draft") is not None:
                arts["draft"] = result["draft"]
            if result.get("draft_id"):
                arts["draft_id"] = result["draft_id"]
            if result.get("validation_id"):
                arts["validation_id"] = result["validation_id"]
            if result.get("validated_pack") is not None:
                arts["validated_pack"] = result["validated_pack"]
            if result.get("publish_result") is not None:
                arts["publish_result"] = result["publish_result"]
            if result.get("raw_acked"):
                arts["raw_acked"] = True
            save_workflow(wf)
            _emit(
                "stage.completed.v1",
                {"workflow_id": workflow_id, "stage": stage, "duration_ms": duration_ms},
            )
            executed += 1
            stage = next_stage(stage)
            wf["current_stage"] = stage
            save_workflow(wf)
        except StageError as exc:
            return _handle_stage_failure(
                wf, stage, exc.code, exc.detail, transient=exc.transient, sleeper=sleeper, stage_fns=fns
            )
        except Exception as exc:  # noqa: BLE001
            return _handle_stage_failure(
                wf, stage, "EXCEPTION", str(exc)[:300], transient=True, sleeper=sleeper, stage_fns=fns
            )

    wf = load_workflow(workflow_id) or wf
    if wf.get("current_stage") is None and all(
        (wf.get("stages") or {}).get(s, {}).get("status") == "COMPLETED" for s in STAGES
    ):
        try:
            _set_state(wf, "COMPLETED")
        except IllegalTransition:
            wf["state"] = "COMPLETED"
        wf["finished_at"] = now_iso()
        wf["failure_reason"] = None
        save_workflow(wf)
        _emit("workflow.completed.v1", {"workflow_id": workflow_id, "ticker": wf.get("ticker")})
    return wf


def _handle_stage_failure(
    wf: dict[str, Any],
    stage: str,
    code: str,
    detail: str,
    *,
    transient: bool,
    sleeper: Callable[[float], None],
    stage_fns: dict[str, StageFn] | None = None,
) -> dict[str, Any]:
    bucket = wf["stages"].setdefault(stage, {})
    bucket["status"] = "FAILED"
    bucket["finished_at"] = now_iso()
    bucket["error"] = {"code": code, "detail": detail, "transient": transient}
    wf["failure_reason"] = f"{stage}:{code}:{detail}"
    _emit(
        "stage.failed.v1",
        {"workflow_id": wf["workflow_id"], "stage": stage, "code": code, "detail": detail},
    )

    retries = int(wf.get("retries") or 0)
    if transient and should_retry(retries, error_code=code, detail=detail):
        wf["retries"] = retries + 1
        wf["last_retry_at"] = now_iso()
        delay = backoff_seconds(retries)
        try:
            _set_state(wf, "RETRYING")
        except IllegalTransition:
            wf["state"] = "RETRYING"
        save_workflow(wf)
        _emit(
            "workflow.retrying.v1",
            {"workflow_id": wf["workflow_id"], "retries": wf["retries"], "backoff_seconds": delay},
        )
        sleeper(delay)
        # reset stage to pending for retry
        bucket["status"] = "PENDING"
        try:
            _set_state(wf, "QUEUED")
        except IllegalTransition:
            wf["state"] = "QUEUED"
        save_workflow(wf)
        return run_workflow(str(wf["workflow_id"]), stage_fns=stage_fns, sleep_fn=sleeper)

    # Retries exhausted or permanent failure → FAILED then Dead Letter Queue
    return _dead_letter(wf, stage, code, detail, transient=transient)


def _fail(wf: dict[str, Any], stage: str, code: str, detail: str, *, transient: bool) -> dict[str, Any]:
    try:
        _set_state(wf, "FAILED")
    except IllegalTransition:
        wf["state"] = "FAILED"
    wf["finished_at"] = now_iso()
    wf["failure_reason"] = f"{stage}:{code}:{detail}"
    save_workflow(wf)
    _emit(
        "workflow.failed.v1",
        {
            "workflow_id": wf["workflow_id"],
            "stage": stage,
            "code": code,
            "detail": detail,
            "transient": transient,
        },
    )
    return wf


def _dead_letter(
    wf: dict[str, Any],
    stage: str,
    code: str,
    detail: str,
    *,
    transient: bool,
) -> dict[str, Any]:
    """Move exhausted/permanent failures into DEAD_LETTER for operator review."""
    _fail(wf, stage, code, detail, transient=transient)
    wf = load_workflow(str(wf["workflow_id"])) or wf
    try:
        _set_state(wf, "DEAD_LETTER")
    except IllegalTransition:
        wf["state"] = "DEAD_LETTER"
    wf["dead_letter"] = {
        "stage": stage,
        "error_code": code,
        "error_detail": detail,
        "transient": transient,
        "retries": int(wf.get("retries") or 0),
        "last_retry_at": wf.get("last_retry_at"),
        "dead_lettered_at": now_iso(),
        "manual_replay": True,
    }
    wf["finished_at"] = now_iso()
    save_workflow(wf)
    _emit(
        "workflow.dead_letter.v1",
        {
            "workflow_id": wf["workflow_id"],
            "ticker": wf.get("ticker"),
            "company_id": wf.get("company_id"),
            "stage": stage,
            "code": code,
            "detail": detail,
            "retries": wf.get("retries"),
            "last_retry_at": wf.get("last_retry_at"),
        },
    )
    return wf


def retry_workflow(workflow_id: str, **kwargs: Any) -> dict[str, Any]:
    wf = load_workflow(workflow_id)
    if not wf:
        raise KeyError(f"workflow_not_found:{workflow_id}")
    if wf["state"] == "CANCELLED":
        return wf
    # clear failure on current stage
    stage = wf.get("current_stage") or STAGES[0]
    bucket = wf["stages"].setdefault(stage, {})
    if bucket.get("status") == "FAILED":
        bucket["status"] = "PENDING"
        bucket["error"] = None
    wf["failure_reason"] = None
    wf["finished_at"] = None
    wf["retries"] = 0  # operator-initiated retry resets backoff budget
    wf.pop("dead_letter", None)
    try:
        if wf["state"] == "DEAD_LETTER":
            _set_state(wf, "RETRYING")
        else:
            _set_state(wf, "RETRYING")
    except IllegalTransition:
        wf["state"] = "RETRYING"
    save_workflow(wf)
    return run_workflow(workflow_id, **kwargs)


def replay_workflow(workflow_id: str, *, from_stage: str | None = None, **kwargs: Any) -> dict[str, Any]:
    """Replay from a stage (default: first). Safely re-runs; idempotent skips apply."""
    wf = load_workflow(workflow_id)
    if not wf:
        raise KeyError(f"workflow_not_found:{workflow_id}")
    start = from_stage or STAGES[0]
    if start not in STAGES:
        raise ValueError(f"unknown_stage:{start}")
    # Reset stage statuses from start onward + clear downstream artifacts
    reset = False
    clear_keys = set()
    for s in STAGES:
        if s == start:
            reset = True
        if reset:
            wf["stages"][s] = {"status": "PENDING", "attempts": 0, "started_at": None, "finished_at": None}
            if s == "RAW_EVIDENCE_STORED":
                clear_keys.update({"raw_acked"})
            if s == "PARSE":
                clear_keys.update({"draft", "draft_id"})
            if s == "VALIDATE":
                clear_keys.update({"validation_id", "validated_pack"})
            if s == "WAREHOUSE_PUBLISH":
                clear_keys.update({"publish_result"})
    arts = dict(wf.get("artifacts") or {})
    for k in clear_keys:
        arts.pop(k, None)
    wf["artifacts"] = arts
    wf["current_stage"] = start
    wf["failure_reason"] = None
    wf["finished_at"] = None
    wf["retries"] = 0
    wf.pop("dead_letter", None)
    wf["state"] = "RECEIVED"
    wf["history"] = list(wf.get("history") or []) + [{"state": "RECEIVED", "at": now_iso(), "replay": True}]
    save_workflow(wf)
    return run_workflow(workflow_id, **kwargs)


def cancel_workflow(workflow_id: str) -> dict[str, Any]:
    wf = load_workflow(workflow_id)
    if not wf:
        raise KeyError(f"workflow_not_found:{workflow_id}")
    if wf["state"] in ("COMPLETED", "CANCELLED"):
        return wf
    try:
        _set_state(wf, "CANCELLED")
    except IllegalTransition:
        wf["state"] = "CANCELLED"
    wf["finished_at"] = now_iso()
    save_workflow(wf)
    _emit("workflow.cancelled.v1", {"workflow_id": workflow_id})
    return wf
