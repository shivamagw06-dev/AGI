"""PRP-01 — Performance & Scale tests."""

from __future__ import annotations

import time

import pytest

from institutional_performance.cache import get, reset_for_tests as reset_cache, set, stats
from institutional_performance.flags import flags_dict, is_enabled
from institutional_performance.graph_incremental import apply_incremental_update
from institutional_performance.job_queue import get_queue, reset_queue_for_tests
from institutional_performance.metrics import latency_snapshot, record_latency, reset_metrics_for_tests
from institutional_performance.parallel import run_parallel
from institutional_performance.production import (
    enqueue_job,
    get_job,
    health,
    metrics_api,
    parallel_demo,
    reset_for_tests,
    soft_slice_mission_control,
)
from institutional_performance.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    PRP_WORKSTREAM_ID,
)


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
    assert ADDS_INTELLIGENCE_ENGINES is False
    assert ARCHITECTURE_FROZEN is True
    assert is_enabled() is True
    assert flags_dict()["adds_intelligence_engines"] is False


def test_cache_hit_miss_and_namespaces():
    assert get("query", "q1") is None
    set("query", "q1", value={"answer": 42}, ttl=60)
    assert get("query", "q1") == {"answer": 42}
    set("workspace", "HDFCBANK", "overview", value={"ok": True}, ttl=30)
    assert get("workspace", "HDFCBANK", "overview")["ok"] is True
    s = stats()
    assert s["hits"] >= 1
    assert s["sets"] >= 2
    assert "query" in s["namespaces"]


def test_metrics_p95_and_slow():
    reset_metrics_for_tests()
    for i in range(20):
        record_latency("ask", 0.05 + i * 0.01)
    record_latency("ask", 3.5)  # slow
    snap = latency_snapshot()
    assert snap["sample_count"] >= 21
    assert snap["overall_p95_seconds"] is not None
    assert snap["slow_query_count"] >= 1


def test_parallel_faster_than_serial_wall():
    def _slow(n):
        def _fn():
            time.sleep(0.05)
            return n

        return _fn

    t0 = time.perf_counter()
    out = run_parallel({f"t{i}": _slow(i) for i in range(4)})
    elapsed = time.perf_counter() - t0
    assert len(out) == 4
    # Parallel should finish well under 4 * 0.05 if workers available
    assert elapsed < 0.18
    demo = parallel_demo({"tasks": ["a", "b"], "sleep": 0.01})
    assert demo["ok"] is True


def test_job_queue_cache_warmup_and_status():
    reset_queue_for_tests()
    res = enqueue_job(
        {
            "kind": "cache_warmup",
            "payload": {"namespace": "object", "key": "k1", "value": {"v": 1}},
        }
    )
    assert res["ok"] is True
    job_id = res["job"]["job_id"]
    # Wait for completion
    deadline = time.time() + 3
    final = None
    while time.time() < deadline:
        final = get_job(job_id)
        if final.get("job", {}).get("status") in {"completed", "failed"}:
            break
        time.sleep(0.05)
    assert final is not None
    assert final["job"]["status"] == "completed"
    assert get("object", "k1") == {"v": 1}


def test_graph_incremental_invalidates():
    set("graph", "neighbourhood:TCS", value={"entity_id": "TCS"}, ttl=120)
    assert get("graph", "neighbourhood:TCS") is not None
    out = apply_incremental_update({"entity_ids": ["TCS"], "reason": "test"})
    assert out["mode"] == "incremental"
    assert out["graph_sor"].startswith("KG-01")
    assert "keys_invalidated" in out


def test_soft_slice_performance_center():
    board = soft_slice_mission_control()
    assert board["performance_center"] is True
    assert board["workstream_id"] == PRP_WORKSTREAM_ID
    assert "cache_hit_rate" in board
    assert "queue_depth" in board
    assert "targets" in board
    m = metrics_api()
    assert m["ok"] is True


def test_ask_query_cache_soft_hook():
    from institutional_orchestrator.production import ask, reset_for_tests as reset_uag

    reset_uag()
    reset_cache()
    q = {"question": "What is the decision on HDFCBANK?", "portfolio_id": "agi-core-equity"}
    first = ask(q)
    assert first.get("ok") is True or first.get("rejected") is True
    # Only assert cache path when ask succeeded
    if first.get("ok"):
        second = ask(q)
        assert second.get("cached") is True
        assert second.get("cache_layer") == "PRP-01"
        bypass = ask({**q, "bypass_cache": True})
        assert bypass.get("cached") is not True


def test_workspace_cache_soft_hook():
    from institutional_workspace.production import get_company_workspace, reset_for_tests as reset_rw

    reset_rw()
    reset_cache()
    a = get_company_workspace("INFY", focus="overview")
    if a.get("ok"):
        b = get_company_workspace("INFY", focus="overview")
        assert b.get("cached") is True
        assert b.get("cache_layer") == "PRP-01"


def test_async_publication_enqueue():
    from institutional_publishing.production import generate, reset_for_tests as reset_pub

    reset_pub()
    reset_queue_for_tests()
    res = generate(
        {
            "async": True,
            "type": "morning_brief",
            "portfolio_id": "agi-core-equity",
        }
    )
    assert res.get("async") is True
    assert res.get("job_id") or (res.get("job") or {}).get("job_id")
    job_id = res.get("job_id") or res["job"]["job_id"]
    deadline = time.time() + 5
    while time.time() < deadline:
        st = get_job(job_id)
        if st.get("job", {}).get("status") in {"completed", "failed"}:
            break
        time.sleep(0.05)
    st = get_job(job_id)
    assert st["job"]["status"] in {"completed", "failed"}


def test_queue_stats_depth():
    q = get_queue()
    s = q.stats()
    assert "queue_depth" in s
    assert "active_workers" in s
    assert "publication_generate" in s["registered_kinds"]
