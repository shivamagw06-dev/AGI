"""Ask orchestration stage timing / partial flush (no engine call)."""

from __future__ import annotations

import time

from app.ui.ask_orchestration_trace import (
    STAGE_THRESHOLDS_MS,
    StageTimer,
    format_execution_trace,
    gateway_timeout_orchestration,
)


def test_stage_timer_checkpoints_and_thresholds():
    timer = StageTimer(ask_trace_id="ASK-TEST-001")
    assert timer.last_completed_stage == "http_ingress"
    timer.set_context(entity={"name": "META", "confidence": 0.99})
    timer.mark("entity_resolution")
    timer.mark("ikl")
    # Force a slow reasoning mark
    timer._marks["_last"] = timer._t0 - 31.0  # noqa: SLF001 — test hook (>30s warn)
    timer.mark("reasoning")
    assert any(w.get("kind") == "reasoning_slow" for w in timer.warnings)
    assert any(w.get("stage") == "reasoning" for w in timer.warnings)
    snap = timer.partial_snapshot(completed=False, timeout=True)
    assert snap["ask_trace_id"] == "ASK-TEST-001"
    assert snap["timeout"] is True
    assert snap["last_completed_stage"] == "reasoning"
    assert "ikl_ms" in snap["latency"]
    assert STAGE_THRESHOLDS_MS["reasoning"] == 20_000


def test_execution_trace_format():
    orch = gateway_timeout_orchestration(
        ask_trace_id="ASK-TEST-TO",
        elapsed_ms=120_100,
        timeout_ms=120_000,
        question="How has Meta evolved?",
        detail="timeout",
    )
    text = format_execution_trace(orch)
    assert "Ask Trace ID: ASK-TEST-TO" in text
    assert "Completed: false" in text
    assert "Last completed stage: http_ingress" in text
    assert "Timeout: true" in text
    assert "120.1s" in text


def test_partial_store_roundtrip():
    from app.ui.ask_observability_store import get_partial_trace, record_partial_trace

    record_partial_trace(
        {
            "ask_trace_id": "ASK-PARTIAL-1",
            "last_completed_stage": "retrieval",
            "elapsed_ms": 1500,
            "completed": False,
            "entity": {"name": "RELIANCE"},
            "funnel": {"retrieved": 4, "ranked": 0, "passed": 0, "referenced": 0},
        }
    )
    got = get_partial_trace("ASK-PARTIAL-1")
    assert got is not None
    assert got["last_completed_stage"] == "retrieval"
    assert got["entity"]["name"] == "RELIANCE"
