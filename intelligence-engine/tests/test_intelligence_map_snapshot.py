"""Intelligence Map snapshot — HTTP never fans out probes; worker persists."""

from __future__ import annotations

import inspect

from mission_control import intelligence_map_snapshot as im
from mission_control.production import intelligence_map, reset_for_tests


def setup_function() -> None:
    reset_for_tests()


def test_warming_when_missing():
    body = intelligence_map()
    assert body["status"] == "warming"
    assert body.get("_warming") is True
    assert body.get("probes") == {}


def test_production_never_probes_inline():
    from mission_control import production

    source = inspect.getsource(production.intelligence_map)
    assert "soft_probe_catalog" not in source
    assert "read_intelligence_map" in source


def test_http_route_is_snapshot_reader():
    from app.api import routes

    source = inspect.getsource(routes.mission_control_intelligence_map)
    body = source.split('"""', 2)[-1]
    assert "soft_probe_catalog" not in body
    assert "return intelligence_map()" in source


def test_catalog_routes_loaded():
    layers = im.load_catalog_layers()
    assert len(layers) >= 50
    assert any(r["id"] == "FIL" for r in layers)
    assert any(r["route"].endswith("/health") for r in layers)


def test_build_persist_then_read():
    built = im.build_and_persist_intelligence_map(trigger="test")
    assert built["ok"] is True
    body = intelligence_map()
    assert body.get("_warming") is not True
    assert isinstance(body.get("probes"), dict)
    assert body["summary"]["total"] >= 1
    assert "mission_control_summary" in body


def test_path_under_mission_control_root():
    path = im.intelligence_map_path()
    assert path.name == "intelligence_map.json"
    assert "mission_control" in str(path)


def test_frontend_no_longer_fans_out():
    from pathlib import Path

    # intelligence-engine/tests -> repo root
    root = Path(__file__).resolve().parents[2]
    jsx = root / "src/pages/admin/IntelligenceMap.jsx"
    text = jsx.read_text(encoding="utf-8")
    assert "import { getIntelligenceMapSnapshot }" in text or "getIntelligenceMapSnapshot" in text
    assert "probeIntelligencePath," not in text
    assert "Promise.all(" not in text
    assert "getMissionControlDashboard" not in text
    assert "30_000" not in text
    assert "90_000" in text
