from __future__ import annotations

from macro_intelligence_engine.snapshot import read, save


def test_snapshot_is_read_only_on_request(tmp_path, monkeypatch):
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path))
    assert read("Global")["status"] == "AWAITING_SNAPSHOT"
    published = save({"ok": True, "generated_at": "2026-08-07T00:00:00+00:00", "modules": {}}, country="India")
    assert published["ok"] is True
    snapshot = read("Global")
    assert snapshot["ok"] is True
    assert snapshot["fallback"] is True
    assert snapshot["pack"]["modules"] == {}
