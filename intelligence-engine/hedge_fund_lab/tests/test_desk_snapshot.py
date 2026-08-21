"""Serving the desk without making the client wait for the build.

Measured on 21 August: 200 seconds on the first request after a restart, 12 to
25 every time the cache turned over, and a timeout whenever a backfill slice ran
at the same time. The client's wait was the rebuild's duration.
"""

from __future__ import annotations

import threading
import time

import pytest

from hedge_fund_lab import desk_snapshot as ds


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    ds.reset()
    yield
    ds.reset()


def _rows(n=3, tag="a"):
    return [{"symbol": f"S{i}", "tag": tag} for i in range(n)]


class TestServingWithoutWaiting:
    def test_a_stale_snapshot_is_returned_immediately(self, monkeypatch):
        """The whole point: an old answer now beats a current one in 20 seconds."""
        ds.rebuild(lambda: _rows(tag="old"))
        ds._STATE["built_at"] = time.time() - (ds.REFRESH_AFTER_SEC + 60)

        started = time.time()
        out = ds.current(lambda: (time.sleep(5), _rows(tag="new"))[1])
        assert time.time() - started < 1.0, "the request must not wait for the build"
        assert out[0]["tag"] == "old"

    def test_a_refresh_is_triggered_behind_the_request(self, monkeypatch):
        ds.rebuild(lambda: _rows(tag="old"))
        ds._STATE["built_at"] = time.time() - (ds.REFRESH_AFTER_SEC + 60)
        ds.current(lambda: _rows(tag="new"))
        for _ in range(50):
            if (ds._STATE.get("rows") or [{}])[0].get("tag") == "new":
                break
            time.sleep(0.05)
        assert ds._STATE["rows"][0]["tag"] == "new"

    def test_a_fresh_snapshot_triggers_no_build(self):
        ds.rebuild(lambda: _rows(tag="fresh"))
        calls = []
        ds.current(lambda: calls.append(1) or _rows())
        time.sleep(0.2)
        assert calls == [], "a fresh snapshot must not cause work"

    def test_with_nothing_at_all_it_builds_once(self):
        """The only case that blocks. There is no stale answer to give and an
        empty desk is not an answer either."""
        assert ds.current(lambda: _rows(tag="first"))[0]["tag"] == "first"


class TestFailureNeverCostsTheGoodOne:
    def test_a_failed_build_keeps_the_previous_snapshot(self):
        ds.rebuild(lambda: _rows(tag="good"))
        out = ds.rebuild(lambda: (_ for _ in ()).throw(RuntimeError("warehouse down")))
        assert out["ok"] is False
        assert out["kept_previous"] is True
        assert ds._STATE["rows"][0]["tag"] == "good"

    def test_an_empty_build_is_a_failure_not_a_universe_of_nothing(self):
        ds.rebuild(lambda: _rows(tag="good"))
        out = ds.rebuild(lambda: [])
        assert out["ok"] is False
        assert ds._STATE["rows"][0]["tag"] == "good"

    def test_repeated_failures_show_as_degraded(self):
        ds.rebuild(lambda: _rows())
        for _ in range(2):
            ds.rebuild(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert ds.freshness() == ds.DEGRADED

    def test_a_failing_builder_is_not_retried_on_every_request(self):
        """A broken warehouse should not be hammered by every page open."""
        ds.rebuild(lambda: _rows())
        ds.rebuild(lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert ds.should_refresh() is False


class TestSurvivingRestart:
    def test_a_snapshot_is_persisted_and_read_back(self):
        ds.rebuild(lambda: _rows(tag="persisted"))
        assert ds.snapshot_path().exists()
        ds.reset()
        assert ds.prime() is True
        assert ds._STATE["rows"][0]["tag"] == "persisted"

    def test_a_fresh_process_serves_the_previous_build_without_building(self):
        ds.rebuild(lambda: _rows(tag="yesterday"))
        ds.reset()
        calls = []
        out = ds.current(lambda: calls.append(1) or _rows(tag="new"))
        assert out[0]["tag"] == "yesterday"
        assert calls == [], "a restart must not rebuild before answering"

    def test_a_half_written_file_is_not_adopted(self):
        ds.rebuild(lambda: _rows())
        ds.snapshot_path().write_text("{\"version\": 2, \"rows\": [", encoding="utf-8")
        ds.reset()
        assert ds.prime() is False

    def test_an_older_format_is_ignored_rather_than_misread(self):
        ds.rebuild(lambda: _rows())
        import json
        payload = json.loads(ds.snapshot_path().read_text())
        payload["version"] = 1
        ds.snapshot_path().write_text(json.dumps(payload), encoding="utf-8")
        ds.reset()
        assert ds.prime() is False


class TestConcurrency:
    def test_two_builds_do_not_run_at_once(self):
        """Two identical scans of the same tables help nobody and compete for
        the same database lock."""
        started = threading.Event()
        release = threading.Event()

        def slow():
            started.set()
            release.wait(2)
            return _rows(tag="slow")

        t = threading.Thread(target=lambda: ds.rebuild(slow), daemon=True)
        t.start()
        started.wait(2)
        out = ds.rebuild(lambda: _rows(tag="second"))
        release.set()
        t.join(3)
        assert out == {"ok": False, "skipped": "already_building"}


class TestReporting:
    def test_status_says_how_old_and_how_healthy(self):
        ds.rebuild(lambda: _rows(5))
        st = ds.status()
        assert st["rows"] == 5
        assert st["freshness"] == ds.FRESH
        assert st["age_seconds"] is not None
        assert st["build_seconds"] is not None
        assert st["persisted"] is True

    def test_an_empty_state_is_reported_as_empty(self):
        assert ds.status()["freshness"] == ds.EMPTY


class TestDutyCycle:
    """The refresh interval must stay clear of how long a build takes.

    The first production build was 210 seconds against a 300 second interval,
    which would have left the engine building two thirds of every cycle - the
    same continuous background load that took the site down that morning,
    arriving by a different route.
    """

    def test_the_interval_leaves_room_for_a_slow_build(self):
        assert ds.REFRESH_AFTER_SEC >= 900, "a 210s build needs far more than 300s"

    def test_a_slow_build_is_flagged_even_when_it_succeeds(self, monkeypatch):
        monkeypatch.setattr(ds, "SLOW_BUILD_SEC", 0.0)
        out = ds.rebuild(lambda: _rows())
        assert out["ok"] is True and out["slow"] is True
        assert ds.status()["slow_build"] is True

    def test_the_interval_is_configurable(self):
        assert ds.status()["refresh_after_seconds"] == ds.REFRESH_AFTER_SEC
