"""Snapshot writes must be coalesced, not run once per ingest.

save_store() rebuilds the entire KIP store as a single JSON string before
writing. It used to be called after every successful ingest, so each new
document re-serialised every document already stored. With the live store at
roughly 2,000 documents and 37,000 chunks, the process spent its time
serialising and the uvicorn event loop was starved.

That is how the engine failed on 2026-08-19: /v1/health timed out for hours
while the same process kept writing snapshots to disk, so the container was
alive and doing work but answering no HTTP. Disk usage was flat at ~34/50 GB
throughout, ruling out exhaustion.
"""

from __future__ import annotations

import threading
import time
from types import SimpleNamespace

import pytest

from app.kip.service import KipService


class _Recorder:
    """Stands in for kip_persist, counting full-store writes."""

    def __init__(self):
        self.saves = 0
        self.concurrent = 0
        self._active = 0
        self._lock = threading.Lock()

    def save_store(self, _store):
        with self._lock:
            self._active += 1
            if self._active > 1:
                self.concurrent += 1
        time.sleep(0.01)  # stand-in for a large synchronous serialisation
        with self._lock:
            self._active -= 1
        self.saves += 1
        return {"ok": True}

    def load_store(self, _store):
        return {"loaded": False}


@pytest.fixture
def svc(monkeypatch):
    from app.kip import service as service_mod

    rec = _Recorder()
    monkeypatch.setattr(service_mod, "kip_persist", rec)
    s = KipService(load_snapshot=False)
    s.flags = SimpleNamespace(kip=True, kip_prediction_tracking=False, kip_graph=False)
    return s, rec


def test_first_ingest_still_writes(svc):
    """A cold store must persist immediately — nothing to coalesce yet."""
    s, rec = svc
    s._post_ingest(object())
    assert rec.saves == 1


def test_subsequent_ingests_are_coalesced(svc):
    """The regression: 50 ingests must not mean 50 full-store writes."""
    s, rec = svc
    for _ in range(50):
        s._post_ingest(object())
    # One initial write, then at most one more per max_pending batch.
    assert rec.saves <= 1 + (50 // s._save_max_pending)
    assert rec.saves < 50


def test_pending_threshold_forces_a_write(svc):
    """Coalescing must not defer indefinitely under sustained ingest."""
    s, rec = svc
    s._post_ingest(object())          # initial write
    before = rec.saves
    for _ in range(s._save_max_pending):
        s._post_ingest(object())
    assert rec.saves > before


def test_time_interval_forces_a_write(svc):
    s, rec = svc
    s._post_ingest(object())
    before = rec.saves
    s._last_save_at = time.monotonic() - (s._save_min_interval + 1)
    s._post_ingest(object())
    assert rec.saves == before + 1


def test_concurrent_ingests_never_serialise_twice(svc):
    """Two threads must not both serialise the store: that doubles peak memory."""
    s, rec = svc
    s._post_ingest(object())
    s._last_save_at = 0.0  # make every caller consider itself due

    threads = [threading.Thread(target=s._post_ingest, args=(object(),)) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert rec.concurrent == 0


def test_explicit_save_always_writes(svc):
    """The manual endpoint and shutdown path must never be debounced away."""
    s, rec = svc
    s._post_ingest(object())
    before = rec.saves
    s.save_snapshot()
    assert rec.saves == before + 1


def test_ingest_failure_never_propagates(svc, monkeypatch):
    """A failed snapshot must not fail the ingest that triggered it."""
    s, rec = svc

    def boom(_store):
        raise OSError("disk full")

    monkeypatch.setattr(rec, "save_store", boom)
    s._post_ingest(object())  # must not raise
