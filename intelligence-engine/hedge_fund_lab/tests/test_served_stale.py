"""Heavy caches answer from what they have and refresh behind the answer.

A cache that rebuilds on whichever request arrives after it expires makes that
client pay for the whole scan while everyone else queues behind the lock.
`sector_ratio_history` is 139,639 rows and that turnover measured 39 seconds in
production.
"""

from __future__ import annotations

import threading
import time

import pytest

from hedge_fund_lab.scanner import _served_stale


@pytest.fixture
def cache():
    return {"at": 0.0, "rows": None, "building": False}


class TestServingStale:
    def test_an_expired_value_is_returned_without_waiting(self, cache):
        cache.update({"rows": "old", "at": time.time() - 10_000})
        started = time.time()
        out = _served_stale(cache, threading.Lock(), 60,
                            lambda: (time.sleep(3), "new")[1], "t")
        assert out == "old"
        assert time.time() - started < 0.5, "the caller must not pay for the rebuild"

    def test_the_refresh_lands_behind_the_answer(self, cache):
        cache.update({"rows": "old", "at": time.time() - 10_000})
        _served_stale(cache, threading.Lock(), 60, lambda: "new", "t")
        for _ in range(50):
            if cache["rows"] == "new":
                break
            time.sleep(0.05)
        assert cache["rows"] == "new"

    def test_a_fresh_value_starts_no_rebuild(self, cache):
        cache.update({"rows": "current", "at": time.time()})
        calls = []
        assert _served_stale(cache, threading.Lock(), 60,
                             lambda: calls.append(1) or "x", "t") == "current"
        time.sleep(0.2)
        assert calls == []

    def test_an_empty_cache_builds_once_and_waits(self, cache):
        """Nothing to serve, so this is the one case that blocks."""
        assert _served_stale(cache, threading.Lock(), 60, lambda: "built", "t") == "built"


class TestFailureBehaviour:
    def test_a_failed_refresh_keeps_the_previous_value(self, cache):
        cache.update({"rows": "good", "at": time.time() - 10_000})
        _served_stale(cache, threading.Lock(), 60,
                      lambda: (_ for _ in ()).throw(RuntimeError("warehouse down")), "t")
        time.sleep(0.3)
        assert cache["rows"] == "good", "a failed refresh must not empty a working cache"
        assert cache["building"] is False, "and must not wedge the refresh flag"

    def test_an_empty_rebuild_does_not_replace_a_good_value(self, cache):
        cache.update({"rows": "good", "at": time.time() - 10_000})
        _served_stale(cache, threading.Lock(), 60, lambda: {}, "t")
        time.sleep(0.3)
        assert cache["rows"] == "good"

    def test_only_one_refresh_runs_at_a_time(self, cache):
        cache.update({"rows": "old", "at": time.time() - 10_000})
        calls = []

        def slow():
            calls.append(1)
            time.sleep(0.4)
            return "new"

        lock = threading.Lock()
        for _ in range(5):
            _served_stale(cache, lock, 60, slow, "t")
        time.sleep(0.8)
        assert len(calls) == 1, "five page opens must not cause five scans"
