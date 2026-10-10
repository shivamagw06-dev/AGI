from __future__ import annotations

from types import SimpleNamespace

from valuation_engine import snapshot_store


def test_web_role_runs_snapshot_in_disposable_process(monkeypatch):
    monkeypatch.setenv("AGI_ROLE", "web")
    monkeypatch.setenv("VALUATION_PACK_PROCESS_ISOLATION", "true")
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        payload = {"ok": True, "symbol": "RELIANCE", "window": "5Y"}
        return SimpleNamespace(
            returncode=0,
            stdout=snapshot_store._RESULT_PREFIX + snapshot_store.json.dumps(payload) + "\n",
            stderr="",
        )

    monkeypatch.setattr(snapshot_store.subprocess, "run", fake_run)

    result = snapshot_store.compute_and_persist("reliance", window="5Y", peer_limit=12)

    assert result == {"ok": True, "symbol": "RELIANCE", "window": "5Y"}
    assert seen["command"][1:4] == [
        "-m",
        "valuation_engine.snapshot_store",
        "--compute",
    ]
    assert seen["command"][-3:] == ["RELIANCE", "5Y", "12"]
    assert seen["kwargs"]["timeout"] == 150.0
    assert seen["kwargs"]["check"] is False


def test_worker_role_keeps_inline_calculation(monkeypatch):
    monkeypatch.setenv("AGI_ROLE", "gather_worker")
    monkeypatch.setenv("VALUATION_PACK_PROCESS_ISOLATION", "true")
    monkeypatch.setattr(
        snapshot_store,
        "_compute_and_persist_inline",
        lambda symbol, **kwargs: {
            "ok": True,
            "symbol": symbol,
            "window": kwargs["window"],
            "mode": "inline",
        },
    )
    monkeypatch.setattr(
        snapshot_store.subprocess,
        "run",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("must not spawn")),
    )

    result = snapshot_store.compute_and_persist("TCS", window="3Y", peer_limit=4)

    assert result["mode"] == "inline"
    assert result["symbol"] == "TCS"
    assert result["window"] == "3Y"
