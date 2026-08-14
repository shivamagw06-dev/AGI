import json

from strategy_lab import registry_store


def test_persist_decisions_upserts_registry_and_appends_evidence(monkeypatch):
    calls = []
    monkeypatch.setattr(registry_store, "_credentials", lambda: ("https://example.supabase.co", "key"))
    monkeypatch.setattr(registry_store, "_rest", lambda method, table, **kwargs: calls.append((method, table, kwargs)))
    registry_store._LAST_WRITE.update({"at": 0.0, "result": {"ok": False}})
    strategy = {
        "strategy_id": "momentum",
        "name": "Momentum",
        "version": "v1",
        "validation_registry": {
            "requested_lifecycle": "OPERATIONAL",
            "supported_lifecycle": "OPERATIONAL",
            "lifecycle": "OPERATIONAL",
            "health": "HEALTHY",
            "execution": "BLOCKED",
            "registry_version": "v2",
            "evidence": {"implementation": {"status": "PASSED", "source": "test"}},
        },
    }

    result = registry_store.persist_decisions([strategy], force=True)

    assert result == {"ok": True, "status": "PERSISTED", "decisions": 1, "evidence_rows": 1}
    assert [call[1] for call in calls] == ["strategy_validation_registry", "strategy_validation_evidence"]
    evidence = calls[1][2]["body"][0]
    assert evidence["status"] == "PASSED"
    assert evidence["receipt_id"] == evidence["evidence_hash"]
    assert len(evidence["receipt_id"]) == 64


def test_persistence_failure_is_fail_soft(monkeypatch):
    monkeypatch.setattr(registry_store, "_credentials", lambda: ("https://example.supabase.co", "key"))
    monkeypatch.setattr(registry_store, "_rest", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("offline")))
    registry_store._LAST_WRITE.update({"at": 0.0, "result": {"ok": False}})

    result = registry_store.persist_decisions([{
        "strategy_id": "momentum", "name": "Momentum", "version": "v1",
        "validation_registry": {"evidence": {}},
    }], force=True)

    assert result["ok"] is False
    assert result["status"] == "PERSISTENCE_FAILED"
    assert "offline" in result["error"]

