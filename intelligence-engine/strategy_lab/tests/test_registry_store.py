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


def test_latest_evidence_keeps_newest_receipt_per_gate(monkeypatch):
    monkeypatch.setattr(registry_store, "_credentials", lambda: ("https://example.supabase.co", "key"))
    rows = [
        {"strategy_key": "momentum", "gate_key": "backtest", "status": "PASSED", "recorded_at": "2026-08-14T02:00:00Z", "metrics": {"detail": {"sharpe": 1.1}}},
        {"strategy_key": "momentum", "gate_key": "backtest", "status": "MISSING", "recorded_at": "2026-08-14T01:00:00Z", "metrics": {}},
        {"strategy_key": "momentum", "gate_key": "transaction_costs", "status": "PASSED", "recorded_at": "2026-08-14T02:00:00Z", "metrics": {"detail": {"bps": 25}}},
    ]
    monkeypatch.setattr(registry_store, "_rest", lambda *args, **kwargs: rows)
    registry_store._EVIDENCE_CACHE.update({"at": 0.0, "rows": {}})

    evidence = registry_store.load_latest_evidence(force=True)["momentum"]

    assert evidence["backtest"]["status"] == "PASSED"
    assert evidence["backtest"]["detail"]["sharpe"] == 1.1
    assert evidence["transaction_costs"]["status"] == "PASSED"


def test_latest_evidence_ignores_newer_missing_refresh(monkeypatch):
    monkeypatch.setattr(registry_store, "_credentials", lambda: ("https://example.supabase.co", "key"))
    rows = [
        {"strategy_key": "momentum", "gate_key": "risk", "status": "MISSING", "recorded_at": "2026-08-15T00:00:00Z"},
        {"strategy_key": "momentum", "gate_key": "risk", "status": "FAILED", "recorded_at": "2026-08-14T00:00:00Z", "metrics": {"detail": "drawdown"}},
    ]
    monkeypatch.setattr(registry_store, "_rest", lambda *args, **kwargs: rows)
    registry_store._EVIDENCE_CACHE.update({"at": 0.0, "rows": {}})

    evidence = registry_store.load_latest_evidence(force=True)["momentum"]

    assert evidence["risk"]["status"] == "FAILED"


def test_latest_evidence_filters_missing_before_server_limit(monkeypatch):
    monkeypatch.setattr(registry_store, "_credentials", lambda: ("https://example.supabase.co", "key"))
    queries = []
    monkeypatch.setattr(registry_store, "_rest", lambda *args, **kwargs: queries.append(kwargs.get("query")) or [])
    registry_store._EVIDENCE_CACHE.update({"at": 0.0, "rows": {}})

    registry_store.load_latest_evidence(force=True)

    assert "status=neq.MISSING" in queries[0]
    assert queries[0].index("status=neq.MISSING") < queries[0].index("limit=1000")


def test_persist_decisions_does_not_append_missing_evidence(monkeypatch):
    calls = []
    monkeypatch.setattr(registry_store, "_credentials", lambda: ("https://example.supabase.co", "key"))
    monkeypatch.setattr(registry_store, "_rest", lambda method, table, **kwargs: calls.append((table, kwargs.get("body"))))
    registry_store._LAST_WRITE.update({"at": 0.0, "result": {"ok": False}})
    strategy = {
        "strategy_id": "momentum",
        "name": "Momentum",
        "version": "v1",
        "validation_registry": {
            "evidence": {
                "implementation": {"status": "PASSED", "source": "calculator"},
                "risk": {"status": "MISSING"},
            }
        },
    }

    result = registry_store.persist_decisions([strategy], force=True)

    evidence_write = next(body for table, body in calls if table == "strategy_validation_evidence")
    assert result["evidence_rows"] == 1
    assert [row["gate_key"] for row in evidence_write] == ["implementation"]
