"""CGL health surfaces gather sidecar heartbeat when HTTP gather is off."""

from __future__ import annotations

from continuous_gather_learn import persist as cgl_persist
from continuous_gather_learn.production import health


def test_heartbeat_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("CONTINUOUS_GATHER_LEARN", "false")
    monkeypatch.setenv("AGI_ROLE", "gather_worker")
    monkeypatch.setenv("FAA_LIVE_FETCH", "true")

    written = cgl_persist.write_gather_heartbeat({"phase": "ready"})
    assert written["role"] == "gather_worker"
    assert written["FAA_LIVE_FETCH"] == "true"

    hb = cgl_persist.read_gather_heartbeat(max_age_sec=120)
    assert hb["fresh"] is True
    assert hb["present"] is True

    h = health()
    assert h["enabled"] is False
    assert h["effective_gather"] is True
    assert h["status"] == "ok_via_sidecar"
    assert h["gather_sidecar"]["fresh"] is True


def test_faa_flags_prefer_env(monkeypatch):
    monkeypatch.setenv("FAA_LIVE_FETCH", "true")
    from app.faa.flags import FaaFlags

    flags = FaaFlags.from_settings()
    assert flags.faa_live_fetch is True
