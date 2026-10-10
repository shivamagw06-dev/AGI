"""Mission Control Agent Map — inventory + status probes."""

from __future__ import annotations

from mission_control.agent_map import AGENT_MAP_VERSION, GROUP_LABELS, build_agent_map
from mission_control.production import agent_map, health


def test_agent_map_payload_shape():
    body = build_agent_map()
    assert body["enabled"] is True
    assert body["read_only"] is True
    assert body["version"] == AGENT_MAP_VERSION
    assert body["summary"]["total"] >= 30
    assert isinstance(body["agents"], list)
    assert isinstance(body["groups"], list)
    assert body["groups"]
    ids = {a["id"] for a in body["agents"]}
    assert "cio" in ids
    assert "faa" in ids
    assert "macro_economist" in ids
    assert "iaf_business" in ids
    for a in body["agents"]:
        assert a["status"] in {"working", "soft", "off", "orphan", "degraded", "unknown"}
        assert a["responsibility"]
        assert isinstance(a["sources"], list)
        assert a["group"] in GROUP_LABELS


def test_production_facade_and_health_link():
    from mission_control.agent_map_snapshot import build_and_persist_agent_map

    # HTTP facade is snapshot-backed — seed then read.
    build_and_persist_agent_map(trigger="test_seed")
    body = agent_map()
    assert body["summary"]["headline"]
    assert body.get("_warming") is not True
    h = health()
    assert "agent-map" in str(h.get("agent_map") or "")
