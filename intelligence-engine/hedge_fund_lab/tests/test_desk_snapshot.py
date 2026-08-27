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


NAME = "test_artifact"


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    ds.reset()
    ds.register(NAME, lambda: _rows(), refresh_after=ds.REFRESH_AFTER_SEC)
    yield
    ds.reset()


def _rows(n=3, tag="a"):
    return [{"symbol": f"S{i}", "tag": tag} for i in range(n)]


class TestServingWithoutWaiting:
    def test_a_stale_snapshot_is_returned_immediately(self, monkeypatch):
        """The whole point: an old answer now beats a current one in 20 seconds."""
        ds.rebuild(NAME, lambda: _rows(tag="old"))
        ds._state(NAME)["built_at"] = time.time() - (ds.REFRESH_AFTER_SEC + 60)

        started = time.time()
        out = ds.current(NAME, lambda: (time.sleep(5), _rows(tag="new"))[1])
        assert time.time() - started < 1.0, "the request must not wait for the build"
        assert out[0]["tag"] == "old"

    def test_a_refresh_is_triggered_behind_the_request(self, monkeypatch):
        ds.rebuild(NAME, lambda: _rows(tag="old"))
        ds._state(NAME)["built_at"] = time.time() - (ds.REFRESH_AFTER_SEC + 60)
        ds.current(NAME, lambda: _rows(tag="new"))
        for _ in range(50):
            if (ds._state(NAME).get("payload") or [{}])[0].get("tag") == "new":
                break
            time.sleep(0.05)
        assert ds._state(NAME)["payload"][0]["tag"] == "new"

    def test_a_fresh_snapshot_triggers_no_build(self):
        ds.rebuild(NAME, lambda: _rows(tag="fresh"))
        calls = []
        ds.current(NAME, lambda: calls.append(1) or _rows())
        time.sleep(0.2)
        assert calls == [], "a fresh snapshot must not cause work"

    def test_with_nothing_at_all_it_builds_once(self):
        """The only case that blocks. There is no stale answer to give and an
        empty desk is not an answer either."""
        assert ds.current(NAME, lambda: _rows(tag="first"))[0]["tag"] == "first"


class TestFailureNeverCostsTheGoodOne:
    def test_a_failed_build_keeps_the_previous_snapshot(self):
        ds.rebuild(NAME, lambda: _rows(tag="good"))
        out = ds.rebuild(NAME, lambda: (_ for _ in ()).throw(RuntimeError("warehouse down")))
        assert out["ok"] is False
        assert out["kept_previous"] is True
        assert ds._state(NAME)["payload"][0]["tag"] == "good"

    def test_an_empty_build_is_a_failure_not_a_universe_of_nothing(self):
        ds.rebuild(NAME, lambda: _rows(tag="good"))
        out = ds.rebuild(NAME, lambda: [])
        assert out["ok"] is False
        assert ds._state(NAME)["payload"][0]["tag"] == "good"

    def test_repeated_failures_show_as_degraded(self):
        ds.rebuild(NAME, lambda: _rows())
        for _ in range(2):
            ds.rebuild(NAME, lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert ds.freshness(NAME) == ds.DEGRADED

    def test_a_failing_builder_is_not_retried_on_every_request(self):
        """A broken warehouse should not be hammered by every page open."""
        ds.rebuild(NAME, lambda: _rows())
        ds.rebuild(NAME, lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        assert ds.should_refresh(NAME) is False


class TestSurvivingRestart:
    def test_a_snapshot_is_persisted_and_read_back(self):
        ds.rebuild(NAME, lambda: _rows(tag="persisted"))
        assert ds.snapshot_path(NAME).exists()
        ds.reset()
        assert ds.prime(NAME) is True
        assert ds._state(NAME)["payload"][0]["tag"] == "persisted"

    def test_a_fresh_process_serves_the_previous_build_without_building(self):
        ds.rebuild(NAME, lambda: _rows(tag="yesterday"))
        ds.reset()
        calls = []
        out = ds.current(NAME, lambda: calls.append(1) or _rows(tag="new"))
        assert out[0]["tag"] == "yesterday"
        assert calls == [], "a restart must not rebuild before answering"

    def test_a_half_written_file_is_not_adopted(self):
        ds.rebuild(NAME, lambda: _rows())
        ds.snapshot_path(NAME).write_text("{\"version\": 2, \"rows\": [", encoding="utf-8")
        ds.reset()
        assert ds.prime(NAME) is False

    def test_an_older_format_is_ignored_rather_than_misread(self):
        ds.rebuild(NAME, lambda: _rows())
        import json
        payload = json.loads(ds.snapshot_path(NAME).read_text())
        payload["version"] = 1
        ds.snapshot_path(NAME).write_text(json.dumps(payload), encoding="utf-8")
        ds.reset()
        assert ds.prime(NAME) is False


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

        t = threading.Thread(target=lambda: ds.rebuild(NAME, slow), daemon=True)
        t.start()
        started.wait(2)
        out = ds.rebuild(NAME, lambda: _rows(tag="second"))
        release.set()
        t.join(3)
        assert out == {"ok": False, "skipped": "already_building"}


class TestReporting:
    def test_status_says_how_old_and_how_healthy(self):
        ds.rebuild(NAME, lambda: _rows(5))
        st = ds.status(NAME)
        assert st["size"] == 5
        assert st["freshness"] == ds.FRESH
        assert st["age_seconds"] is not None
        assert st["build_seconds"] is not None
        assert st["persisted"] is True

    def test_an_empty_state_is_reported_as_empty(self):
        assert ds.status(NAME)["freshness"] == ds.EMPTY


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
        out = ds.rebuild(NAME, lambda: _rows())
        assert out["ok"] is True and out["slow"] is True
        assert ds.status(NAME)["slow_build"] is True

    def test_the_interval_is_configurable(self):
        assert ds.status(NAME)["refresh_after_seconds"] == ds.REFRESH_AFTER_SEC


class TestStartupPriming:
    """What makes a deploy cheap: the process comes up already able to answer.

    Without this the first client after a restart paid for a 206 second universe
    build and a 28 second ratio-history scan, because a fresh process has nothing
    cached and nothing to serve stale.
    """

    def test_priming_adopts_every_registered_artifact(self):
        ds.register("a1", lambda: {"x": 1})
        ds.register("a2", lambda: {"y": 2})
        ds.rebuild("a1")
        ds.rebuild("a2")
        ds.reset()
        out = ds.prime_all()
        assert out["primed"]["a1"] is True
        assert out["primed"]["a2"] is True

    def test_a_primed_artifact_is_served_without_building(self):
        ds.register("a3", lambda: {"built": "first"})
        ds.rebuild("a3")
        ds.reset()
        ds.prime_all()
        calls = []
        out = ds.current("a3", lambda: calls.append(1) or {"built": "second"})
        assert out == {"built": "first"}
        assert calls == [], "a primed process must answer before it rebuilds"

    def test_artifacts_keep_their_own_staleness_budget(self):
        """How old something may be is a question about the data, not about how
        long it takes to build."""
        ds.register("slowish", lambda: {"a": 1}, refresh_after=60.0)
        ds.register("stable", lambda: {"b": 2}, refresh_after=21600.0)
        assert ds.refresh_after("slowish") == 60.0
        assert ds.refresh_after("stable") == 21600.0

    def test_one_artifact_failing_does_not_stop_the_others(self):
        ds.register("good", lambda: {"ok": 1})
        ds.register("bad", lambda: (_ for _ in ()).throw(RuntimeError("boom")))
        out = ds.refresh_stale()
        assert out["artifacts"]["good"]["ok"] is True
        assert out["artifacts"]["bad"]["ok"] is False

    def test_status_covers_every_artifact(self):
        ds.register("z1", lambda: {"a": 1})
        names = {a["name"] for a in ds.status_all()}
        assert "z1" in names and NAME in names
