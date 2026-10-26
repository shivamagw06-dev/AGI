"""Boot restoration must not allocate a second copy of the research store."""

from app.kip import persist
from app.kip.service import KipService


def test_startup_reuses_restored_store_but_explicit_reload_refreshes(monkeypatch):
    calls = []

    def restore(store):
        calls.append(store)
        return {"ok": True, "loaded": True, "documents": 37}

    monkeypatch.setattr(persist, "load_store", restore)
    service = KipService()
    original_store = service.store
    assert service.ensure_snapshot_loaded()["documents"] == 37
    assert service.ensure_snapshot_loaded()["loaded"]
    assert calls == [original_store]
    service.reload_snapshot()
    assert calls == [original_store, original_store]


def test_startup_retries_a_missing_or_failed_initial_snapshot(monkeypatch):
    results = iter([
        {"ok": False, "loaded": False, "error": "temporary read failure"},
        {"ok": True, "loaded": True, "documents": 12},
    ])
    monkeypatch.setattr(persist, "load_store", lambda store: next(results))
    service = KipService()
    assert service.ensure_snapshot_loaded()["documents"] == 12
    assert service.ensure_snapshot_loaded()["loaded"]


def test_deferred_constructor_load_is_restored_at_startup(monkeypatch):
    calls = []
    monkeypatch.setattr(persist, "load_store", lambda store: calls.append(store) or {
        "ok": True, "loaded": True,
    })
    service = KipService(load_snapshot=False)
    assert calls == []
    assert service.ensure_snapshot_loaded()["loaded"]
    assert calls == [service.store]
