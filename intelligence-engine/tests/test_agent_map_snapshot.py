"""Agent Map snapshot architecture — HTTP never probes; worker persists."""

from __future__ import annotations

import inspect

from mission_control import agent_map_snapshot as am
from mission_control.production import agent_map, reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_agent_map_warming_when_missing():
    body = agent_map()
    assert body["status"] == "warming"
    assert body.get("_warming") is True
    assert body.get("agents") == []


def test_production_never_calls_build_inline():
    from mission_control import production

    source = inspect.getsource(production.agent_map)
    assert "build_agent_map" not in source
    assert "read_agent_map" in source


def test_http_route_is_snapshot_reader():
    from app.api import routes

    source = inspect.getsource(routes.mission_control_agent_map)
    body = source.split('"""', 2)[-1]
    assert "build_agent_map(" not in body
    assert "return agent_map()" in source


def test_build_persist_then_read():
    built = am.build_and_persist_agent_map(trigger="test")
    assert built["ok"] is True
    body = agent_map()
    assert body.get("_warming") is not True
    assert body.get("status") == "ready" or body.get("enabled") is True
    assert len(body.get("agents") or []) >= 1
    assert body["summary"]["headline"]


def test_failed_meta_keeps_previous():
    am.build_and_persist_agent_map(trigger="seed")
    with am._LOCK:  # noqa: SLF001
        am._META["last_failure_at"] = "2026-01-01T00:00:00Z"
        am._META["last_error"] = "boom"
    again = agent_map()
    assert again.get("_warming") is not True
    assert len(again.get("agents") or []) >= 1


def test_path_under_mission_control_root():
    path = am.agent_map_path()
    assert path.name == "agent_map.json"
    assert path.parent.name == "mission_control" or "mission_control" in str(path)
