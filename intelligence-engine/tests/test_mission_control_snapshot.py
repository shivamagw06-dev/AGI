"""Mission Control snapshot architecture — HTTP never builds; worker persists."""

from __future__ import annotations

import ast
import inspect

from mission_control import snapshot as mc_snapshot
from mission_control.production import dashboard, health, quality_gates, rebuild, reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_dashboard_warming_when_no_snapshot():
    body = dashboard()
    assert body["status"] == "warming"
    assert body.get("_warming") is True
    assert body.get("snapshot") is None
    assert body["executive_status"]["agi_status"] == "Warming"


def test_dashboard_never_calls_build_inline():
    """dashboard() source must not invoke build_mission_control."""
    from mission_control import production

    source = inspect.getsource(production.dashboard)
    assert "build_mission_control" not in source
    assert "read_dashboard" in source


def test_http_route_is_snapshot_reader():
    from app.api import routes

    source = inspect.getsource(routes.mission_control_dashboard)
    assert "to_thread" not in source
    assert "return dashboard()" in source
    # Docstring may mention the forbidden call; body must not invoke it.
    body = source.split('"""', 2)[-1]
    assert "build_mission_control(" not in body
    assert "from mission_control.aggregate" not in body


def test_build_persist_then_read():
    built = mc_snapshot.build_and_persist_snapshot(trigger="test")
    assert built["ok"] is True
    body = dashboard()
    assert body.get("status") == "ready" or body.get("enabled") is True
    assert body.get("_warming") is not True
    assert body["executive_status"]["agi_status"]
    assert len(body["platform_status"]) >= 10


def test_failed_rebuild_keeps_previous_snapshot():
    mc_snapshot.build_and_persist_snapshot(trigger="seed")
    first = dashboard()
    assert first.get("enabled") is True

    # Simulate failure meta without wiping disk
    with mc_snapshot._LOCK:  # noqa: SLF001
        mc_snapshot._META["last_failure_at"] = "2026-01-01T00:00:00Z"
        mc_snapshot._META["last_error"] = "boom"

    again = dashboard()
    assert again.get("enabled") is True
    assert again.get("_warming") is not True


def test_enqueue_single_flight():
    a = rebuild(trigger="a", wait=True)
    assert a["ok"] is True
    assert a["status"] in {"completed", "failed"}
    # With idle job, a fresh queue should be accepted (single-flight only while running).
    b = rebuild(trigger="b", wait=True)
    assert b["ok"] is True


def test_health_includes_snapshot_meta():
    h = health()
    assert "snapshot" in h
    assert "worker" in h
    assert h["delivery"] == "snapshot"


def test_quality_gates_warming():
    qg = quality_gates()
    assert qg["status"] == "warming"
    assert qg["passed"] is False


def test_atomic_write_helpers_used():
    source = inspect.getsource(mc_snapshot._write_json)
    assert "atomic_write_json" in source or "replace" in source


def test_production_dashboard_ast_no_aggregate_import():
    from mission_control import production

    tree = ast.parse(inspect.getsource(production.dashboard))
    calls = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert "build_mission_control" not in calls
