"""Institutional Intelligence snapshot — HTTP never fans out dashboards."""

from __future__ import annotations

import inspect
from pathlib import Path

from mission_control import institutional_intelligence_snapshot as ii
from mission_control.production import institutional_intelligence, reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_warming_when_missing():
    body = institutional_intelligence()
    assert body["status"] == "warming"
    assert body.get("_warming") is True
    assert body.get("boards", {}).get("health") is None


def test_production_never_gathers_inline():
    from mission_control import production

    source = inspect.getsource(production.institutional_intelligence)
    assert "soft_gather_boards" not in source
    assert "read_institutional_intelligence" in source


def test_http_route_is_snapshot_reader():
    from app.api import routes

    source = inspect.getsource(routes.mission_control_institutional_intelligence)
    body = source.split('"""', 2)[-1]
    assert "soft_gather_boards" not in body
    assert "return institutional_intelligence()" in source


def test_build_persist_then_read():
    built = ii.build_and_persist_institutional_intelligence(trigger="test")
    assert built["ok"] is True
    body = institutional_intelligence()
    assert body.get("_warming") is not True
    boards = body.get("boards") or {}
    assert boards.get("health") is not None
    assert boards.get("institutional_knowledge") is not None
    assert body["summary"]["boards_ok"] >= 1


def test_path_under_mission_control_root():
    path = ii.institutional_intelligence_path()
    assert path.name == "institutional_intelligence.json"
    assert "mission_control" in str(path)


def test_frontend_no_longer_fans_out():
    root = Path(__file__).resolve().parents[2]
    jsx = root / "src/pages/admin/InstitutionalIntelligence.jsx"
    text = jsx.read_text(encoding="utf-8")
    assert "getInstitutionalIntelligenceSnapshot" in text
    assert "getKnowledgeFactoryDailyHealth" not in text
    assert "getUniverseIntelligenceDashboard" not in text
    assert "Promise.all([" not in text
    assert "90_000" in text
    # Intentional write-side prime/run remains.
    assert "runUniverseIntelligence" in text
