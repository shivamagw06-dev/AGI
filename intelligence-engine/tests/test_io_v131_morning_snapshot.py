"""AGI V1.3.1 — Morning Snapshot Performance & Operations tests."""

from __future__ import annotations

import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from investment_office.v13_schema import DATA_CLASSES, IO_V13_VERSION, IO_V13_PLATFORM
from investment_office.morning_snapshot import (
    enqueue_refresh,
    get_snapshot,
    live_system_health,
    put_snapshot,
    reset_for_tests,
    snapshot_meta,
)
from investment_office.production import morning_overview, refresh_morning_office, system_health_v13


def _seed_snapshot(**overrides):
    base = {
        "ok": True,
        "version": IO_V13_VERSION,
        "workstream_id": "IO-V1.3",
        "product": "Investment Office",
        "platform": IO_V13_PLATFORM,
        "admin_only": True,
        "policy": {"buy_sell": False, "issues_recommendations": False, "monitoring_only": True},
        "top_summary": {"research_queue": 3, "market_mood": "Neutral"},
        "header": {"greeting": "Good Morning", "title": "Investment Office"},
        "executive_brief": {"narrative": "Seeded"},
        "priorities": [],
        "overnight_activity": [],
        "research_queue": {"count": 3, "stages": {}, "items": []},
        "opportunities": [],
        "market_summary": {},
        "macro": {},
        "calendar": {},
        "portfolio_monitor": {},
        "sector_monitor": [],
        "metrics": {},
        "analyst_workspace": {},
        "investment_calendar": {},
        "ai_summary": {"text": "Seeded"},
        "generated_at": "2026-07-30T00:00:00Z",
        "actions": ["refresh_morning_office"],
        "links": {"knowledge_operations": "/admin/knowledge-operations"},
    }
    base.update(overrides)
    return put_snapshot(base, trigger="test")


def setup_function():
    reset_for_tests()


def test_v131_identity_and_data_classes():
    assert IO_V13_VERSION.startswith("io-v1.3.1")
    assert IO_V13_PLATFORM == "AGI V1.3.1"
    assert "morning_brief" in DATA_CLASSES
    assert DATA_CLASSES["morning_brief"]["delivery"] == "precomputed_snapshot"


def test_overview_hot_path_reads_snapshot_not_live_rebuild():
    _seed_snapshot()
    t0 = time.time()
    overview = morning_overview()
    elapsed = time.time() - t0
    assert overview["ok"] is True
    assert overview.get("cache", {}).get("source") == "morning_snapshot"
    assert overview["top_summary"]["research_queue"] == 3
    assert elapsed < 1.0  # hot path must not run ICF/IEP/CGL


def test_overview_miss_returns_placeholder_and_queues():
    reset_for_tests()
    overview = morning_overview()
    assert overview["ok"] is True
    assert overview.get("building") is True
    assert overview.get("delivery", {}).get("mode") == "building_placeholder"


def test_snapshot_persist_roundtrip_and_async_refresh_contract():
    meta = _seed_snapshot()
    assert meta.get("persisted_at")
    assert snapshot_meta()["exists"] is True
    assert get_snapshot()["top_summary"]["research_queue"] == 3

    # Contract only — do not start a real background rebuild in unit tests.
    # enqueue_refresh is exercised with wait=False after patching the worker.
    import investment_office.morning_snapshot as ms

    calls = {"n": 0}

    def _noop_worker_build(**kwargs):
        calls["n"] += 1
        return {"ok": True, "trigger": kwargs.get("trigger"), "meta": snapshot_meta()}

    original = ms.build_and_persist_morning_snapshot
    ms.build_and_persist_morning_snapshot = _noop_worker_build  # type: ignore
    try:
        queued = enqueue_refresh(trigger="test_refresh", wait=False)
        assert queued["ok"] is True
        assert queued["status"] in {"queued", "already_running", "running", "completed"}
        assert "job_id" in queued
        t0 = time.time()
        refreshed = refresh_morning_office(wait=False)
        assert time.time() - t0 < 2.0
        assert refreshed["ok"] is True
        time.sleep(0.15)
        assert calls["n"] >= 1
    finally:
        ms.build_and_persist_morning_snapshot = original  # type: ignore


def test_live_system_health_is_lightweight():
    t0 = time.time()
    health = system_health_v13()
    elapsed = time.time() - t0
    assert health["ok"] is True
    assert health["class"] == "live_status"
    assert "snapshot" in health
    assert elapsed < 2.0
    live = live_system_health()
    assert live["ok"] is True
