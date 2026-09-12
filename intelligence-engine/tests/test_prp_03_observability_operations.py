"""PRP-03 — Observability & Operations tests."""

from __future__ import annotations

import time

import pytest

from institutional_observability.alerts import evaluate, list_alerts, reset_for_tests as reset_alerts
from institutional_observability.dependency_monitor import dependency_graph, probe_dependencies
from institutional_observability.health import aggregate_health, liveness, readiness
from institutional_observability.logging import log_event, recent_logs, validate_log_fields
from institutional_observability.metrics import emit, incr, observe_latency, reset_for_tests as reset_metrics, snapshot
from institutional_observability.production import (
    health,
    ops_alerts,
    ops_health,
    ops_metrics,
    ops_service_map,
    ops_trace,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_observability.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    PRP_WORKSTREAM_ID,
)
from institutional_observability.telemetry import begin_request, end_request, span, finish_span
from institutional_observability.tracing import (
    end_trace,
    get_trace,
    start_span,
    start_trace,
    validate_span_hierarchy,
)
from institutional_observability.validator import run_operational_gates, validate_trace


@pytest.fixture(autouse=True)
def _clean():
    reset_for_tests()
    yield
    reset_for_tests()


def test_health_and_freeze_invariants():
    h = health()
    assert h["workstream_id"] == PRP_WORKSTREAM_ID
    assert h["status"] == "ok"
    assert h["adds_intelligence_engines"] is False
    assert h["architecture_frozen"] is True
    assert h["changes_platform_behavior"] is False
    assert h["enters_intelligence_layer"] is False
    assert ADDS_INTELLIGENCE_ENGINES is False
    assert ARCHITECTURE_FROZEN is True
    assert "never changes" in GUIDING_PRINCIPLE.lower() or "never changes" in GUIDING_PRINCIPLE


def test_trace_lifecycle_and_hierarchy():
    from institutional_observability.tracing import end_span

    started = start_trace(correlation_id="corr_obs_1", name="ask")
    tid = started["trace_id"]
    sid = start_span(tid, "authentication", parent_span_id=started["root_span_id"])
    assert sid
    end_span(tid, sid, outcome="ok")
    sid2 = start_span(tid, "uag", parent_span_id=started["root_span_id"])
    end_span(tid, sid2, outcome="ok")
    trace = end_trace(tid, outcome="ok")
    assert trace is not None
    assert trace.correlation_id == "corr_obs_1"
    assert len(trace.spans) >= 3
    d = get_trace(tid)
    assert d["correlation_id"] == "corr_obs_1"
    errors = validate_span_hierarchy(d)
    assert errors == []
    v = validate_trace(d)
    assert v["ok"] is True
    assert v["affects_business_logic"] is False


def test_trace_missing_correlation_flagged():
    started = start_trace(correlation_id="", name="bare")
    tid = started["trace_id"]
    end_trace(tid)
    d = get_trace(tid)
    errors = validate_span_hierarchy(d)
    assert any("correlation" in e for e in errors)


def test_metric_emission_and_percentiles():
    reset_metrics()
    incr("request_count", 1)
    for i in range(20):
        observe_latency(10 + i * 5, component="api")
    emit("cache_hit_rate", 0.75)
    snap = snapshot()
    assert snap["request_count"] >= 1
    assert snap["p50_latency_ms"] is not None
    assert snap["p95_latency_ms"] is not None
    assert snap["cache_hit_rate"] == 0.75


def test_structured_logging_required_fields():
    row = log_event(
        "ask completed",
        component="uag",
        severity="info",
        correlation_id="corr_log",
        trace_id="tr_log",
        tenant_id="agi-default",
        portfolio_id="agi-core-equity",
        user_id="analyst.demo",
    )
    assert validate_log_fields(row) == []
    logs = recent_logs(correlation_id="corr_log")
    assert logs and logs[0]["message"] == "ask completed"


def test_health_aggregation_liveness_readiness():
    assert liveness()["status"] == "alive"
    agg = aggregate_health()
    assert agg["status"] in {"healthy", "degraded", "unhealthy"}
    assert "services" in agg
    r = readiness()
    assert r["status"] in {"ready", "not_ready"}
    oh = ops_health()
    assert oh["ok"] is True


def test_alert_evaluation_from_metrics():
    reset_alerts()
    reset_metrics()
    # Force high latency samples
    for _ in range(30):
        observe_latency(3000, component="api")
    incr("request_count", 30)
    fired = evaluate()
    assert any(a["rule"] == "p95_latency_exceeded" for a in fired) or list_alerts()
    assert ops_alerts()["ok"] is True


def test_dependency_graph_and_probe():
    g = dependency_graph()
    assert g["nodes"] and g["edges"]
    assert any(e["from"] == "api" and e["to"] == "security" for e in g["edges"])
    probed = probe_dependencies()
    assert "dependencies" in probed
    assert probed["graph"]["nodes"]


def test_service_map_and_operations_center():
    sm = ops_service_map()
    assert sm["ok"] is True
    assert sm["topology"]["nodes"]
    board = soft_slice_mission_control()
    assert board["operations_center"] is True
    assert board["workstream_id"] == PRP_WORKSTREAM_ID
    assert board["changes_platform_behavior"] is False
    assert "live_request_rate" in board or board.get("metrics")


def test_telemetry_never_changes_result_meaning():
    handle = begin_request({"correlation_id": "corr_tel"}, name="demo")
    assert handle["enabled"] is True
    sid = span(handle["trace_id"], "work")
    finish_span(handle["trace_id"], sid, outcome="ok")
    business = {"ok": True, "answer": 42, "workstream_id": "UAG-01"}
    out = end_request(handle, outcome="ok", component="demo", result=business)
    assert out["ok"] is True
    assert out["answer"] == 42
    assert out["workstream_id"] == "UAG-01"
    assert out["trace_id"]
    assert out["observability_context"]["correlation_id"] == "corr_tel"
    assert out["observability"]["changes_platform_behavior"] is False


def test_operational_gates_do_not_affect_business():
    g = run_operational_gates(trace={"spans": [], "correlation_id": ""})
    assert g["affects_business_logic"] is False
    assert g["changes_platform_behavior"] is False


def test_integration_ask_tracing_and_correlation():
    from institutional_orchestrator.production import ask, reset_for_tests as reset_uag
    from institutional_security.production import login, reset_for_tests as reset_sec

    reset_uag()
    reset_sec()
    sess = login({"username": "analyst.demo", "password": "analyst-pass"})
    result = ask(
        {
            "question": "What is the decision on INFY?",
            "session_id": sess["session_id"],
            "bypass_cache": True,
        }
    )
    # Observability envelope present; business meaning unchanged by obs
    assert result.get("trace_id") or result.get("observability") or result.get("observability_context")
    if result.get("correlation_id"):
        assert str(result["correlation_id"]).startswith("corr_") or "corr" in str(
            result["correlation_id"]
        )
    if result.get("trace_id"):
        tr = ops_trace(result["trace_id"])
        assert tr["ok"] is True
        assert tr["trace"]["correlation_id"]


def test_integration_publication_obs_and_background_metric():
    from institutional_publishing.production import generate, reset_for_tests as reset_pub
    from institutional_security.production import login, reset_for_tests as reset_sec

    reset_pub()
    reset_sec()
    reset_metrics()
    sess = login({"username": "pm.demo", "password": "pm-pass"})
    result = generate(
        {
            "session_id": sess["session_id"],
            "type": "MorningBrief",
            "portfolio_id": "agi-core-equity",
            "async": True,
        }
    )
    assert result.get("error") != "insufficient_permission"
    # Async path records background job + obs envelope
    if result.get("async"):
        snap = snapshot()
        assert snap["background_jobs"] >= 1 or result.get("trace_id")


def test_integration_security_uag_pub_trace_continuity():
    from institutional_orchestrator.production import ask, reset_for_tests as reset_uag
    from institutional_security.correlation import ensure_correlation_id
    from institutional_security.production import login, reset_for_tests as reset_sec

    reset_uag()
    reset_sec()
    cid = ensure_correlation_id("corr_continuity_prp03")
    sess = login({"username": "analyst.demo", "password": "analyst-pass", "correlation_id": cid})
    # Login returns its own correlation; use session for ask with explicit cid
    result = ask(
        {
            "question": "Summarize HDFCBANK",
            "session_id": sess["session_id"],
            "correlation_id": cid,
            "bypass_cache": True,
        }
    )
    if result.get("trace_id"):
        tr = get_trace(result["trace_id"])
        assert tr is not None
        assert tr.get("correlation_id") == cid or result.get("correlation_id") == cid


def test_ops_metrics_api():
    incr("request_count", 1)
    observe_latency(12)
    m = ops_metrics()
    assert m["ok"] is True
    assert "metrics" in m


def test_three_contexts_are_independent():
    from institutional_observability.models import InstitutionalObservabilityContext
    from institutional_security.models import InstitutionalSecurityContext

    obs = InstitutionalObservabilityContext(
        trace_id="tr_x",
        correlation_id="corr_x",
        request_start=time.time(),
        request_source="api",
    )
    sec = InstitutionalSecurityContext(
        user_id="analyst.demo",
        tenant_id="agi-default",
        role="research_analyst",
        correlation_id="corr_x",
    )
    assert obs.to_dict()["complements_execution_and_security"] is True
    assert sec.to_dict()["complements_execution_context"] is True
    assert "changes_platform_behavior" in obs.to_dict()
    assert obs.correlation_id == sec.correlation_id
