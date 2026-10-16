"""The options-lab collector that runs inside the API server.

These lock in the two things that made the lab collect nothing for weeks: the
loop has to actually be started by something, and it has to be observable when
it is not.
"""

from __future__ import annotations

import datetime as dt
import pathlib

import pytest

from options_lab import automation
from options_lab.upstox_live import IST, LiveConfig


def _config(tmp_path: pathlib.Path) -> LiveConfig:
    return LiveConfig(
        database_path=tmp_path / "ol.sqlite3",
        report_directory=tmp_path / "reports",
    )


def _freeze(monkeypatch, ist_text: str) -> None:
    """Pin automation's clock to a wall time in IST."""
    naive = dt.datetime.strptime(ist_text, "%Y-%m-%d %H:%M")
    moment = naive.replace(tzinfo=IST).astimezone(dt.timezone.utc)

    class Frozen(dt.datetime):
        @classmethod
        def now(cls, tz=None):
            return moment.astimezone(tz) if tz else moment

    monkeypatch.setattr(automation, "datetime", Frozen)


@pytest.fixture
def collected(monkeypatch):
    """Count collections without calling Upstox."""
    calls: list[bool] = []
    monkeypatch.setattr(
        automation, "collect_command", lambda config, force: calls.append(force) or 0
    )
    return calls


# 2026-08-24 is a Monday; the NSE session is 09:15-15:30 IST.
@pytest.mark.parametrize(
    "moment,should_collect",
    [
        ("2026-08-24 08:00", False),  # before the open
        ("2026-08-24 09:20", True),  # in session
        ("2026-08-24 15:29", True),  # a minute before the close
        ("2026-08-24 16:00", False),  # after the close
        ("2026-08-23 11:00", False),  # Sunday
    ],
)
def test_collects_only_during_the_session(
    tmp_path, monkeypatch, collected, moment, should_collect
):
    _freeze(monkeypatch, moment)
    automation.worker_tick(_config(tmp_path), automation.WorkerState())
    assert bool(collected) is should_collect


def test_one_collection_per_fifteen_minute_bucket(tmp_path, monkeypatch, collected):
    state = automation.WorkerState()
    config = _config(tmp_path)
    for moment in ("2026-08-24 09:20", "2026-08-24 09:25", "2026-08-24 09:29"):
        _freeze(monkeypatch, moment)
        automation.worker_tick(config, state)
    assert len(collected) == 1, "same bucket must not collect twice"

    _freeze(monkeypatch, "2026-08-24 09:31")
    automation.worker_tick(config, state)
    assert len(collected) == 2, "a new bucket must collect"


def test_a_failed_collection_is_counted_not_raised(tmp_path, monkeypatch):
    monkeypatch.setattr(automation, "collect_command", lambda config, force: 2)
    _freeze(monkeypatch, "2026-08-24 09:20")
    state = automation.WorkerState()
    automation.worker_tick(_config(tmp_path), state)
    assert state.failures == 1
    assert state.collections == 0
    assert state.last_event["kind"] == "collection_failed"


def test_embedded_stays_off_unless_the_flag_is_set(monkeypatch, tmp_path):
    from options_lab import embedded

    monkeypatch.delenv("OPTIONS_LAB_LIVE_VALIDATION", raising=False)
    monkeypatch.setattr(embedded, "_thread", None)
    embedded.start()
    status = embedded.status()
    assert status["enabled"] is False
    assert status["running"] is False
    # The reason has to be reported: a silent no-op is what hid this before.
    assert status["disabled_reason"]


def test_embedded_runs_the_shared_tick(monkeypatch, tmp_path):
    """The embedded loop must not be a second copy of the worker logic."""
    from options_lab import embedded

    monkeypatch.setenv("OPTIONS_LAB_LIVE_VALIDATION", "true")
    monkeypatch.setenv("OPTIONS_LAB_DB_PATH", str(tmp_path / "ol.sqlite3"))
    monkeypatch.setenv("OPTIONS_LAB_REPORT_DIR", str(tmp_path / "reports"))

    seen: list[int] = []
    monkeypatch.setattr(
        embedded, "worker_tick", lambda config, state: seen.append(1) or None
    )
    monkeypatch.setattr(embedded, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(embedded, "_thread", None)

    embedded.start()
    try:
        deadline = dt.datetime.now() + dt.timedelta(seconds=3)
        while not seen and dt.datetime.now() < deadline:
            pass
        assert seen, "the collector thread never ran a tick"
        assert embedded.status()["running"] is True
    finally:
        embedded.stop(timeout=3)
    assert embedded.status()["running"] is False, "must stop on shutdown"


def test_embedded_installs_no_signal_handler():
    """run_worker owns SIGTERM/SIGINT. Inside the API server that would take
    over the engine's own shutdown, so the embedded path must not do it."""
    import ast

    source = pathlib.Path(
        pathlib.Path(__file__).parent.parent / "options_lab" / "embedded.py"
    ).read_text()
    tree = ast.parse(source)
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Import) and node.names[0].name == "signal"
    ]
    assert not [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "signal"
    ]
