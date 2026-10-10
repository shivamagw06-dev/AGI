"""Stage measurement, tested on the shapes that made the last two guesses wrong.

Two explanations for the 7.6 GB engine have already failed, both inferred from
what was running rather than from what was allocating. These assert that the
instrument actually catches the thing an inference misses: a stage that returns
to its starting RSS having briefly held two copies.
"""

from __future__ import annotations

import json
import os
import tempfile

import pytest

os.environ.setdefault("INSTITUTIONAL_WAREHOUSE_ROOT", tempfile.mkdtemp(prefix="ms_"))

from observability import memory_stages as ms  # noqa: E402


@pytest.fixture(autouse=True)
def fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path))
    yield


def test_rss_reports_something_sane():
    rss = ms.rss_bytes()
    assert rss is not None and rss > 1_000_000, "a live process is bigger than a megabyte"


def test_a_transient_double_allocation_is_caught_by_peak_not_by_delta():
    """The defect an ends-only measurement cannot see.

    The desk holds the previous artifact live for the whole rebuild and releases
    it on adopt. Before and after are then nearly equal while the middle is
    twice the size, which is what an 8 GB ceiling actually meets.
    """
    with ms.stage("transient") as detail:
        blob = [bytearray(1024 * 1024) for _ in range(200)]
        detail["rows"] = len(blob)
        del blob

    row = ms.read_stages()["stages"][-1]
    assert row["rss_peak_over_before_mb"] > 100, "the peak must show the held copy"
    assert row["rss_peak_mb"] >= row["rss_after_mb"]
    assert row["rows"] == 200


def test_a_stage_records_duration_threads_and_its_own_facts():
    with ms.stage("counted", companies="60") as detail:
        detail["rows"] = 1234
    row = ms.read_stages()["stages"][-1]
    assert row["stage"] == "counted"
    assert row["companies"] == "60"
    assert row["rows"] == 1234
    assert row["duration_s"] >= 0
    assert row["threads_before"] >= 1
    assert row["pid"] == os.getpid()


def test_a_failing_stage_is_recorded_and_the_error_still_raises():
    """A job that dies is the one you most need the measurement for."""
    with pytest.raises(ValueError):
        with ms.stage("explodes"):
            raise ValueError("boom")
    row = ms.read_stages()["stages"][-1]
    assert row["stage"] == "explodes"
    assert "ValueError" in row["error"]


def test_heartbeats_say_where_execution_reached():
    ms.heartbeat("backfill_entered")
    ms.heartbeat("backfill_boot_slice_start", companies="60")
    rows = ms.read_stages()["stages"]
    names = [r["stage"] for r in rows if r.get("kind") == "heartbeat"]
    assert names == ["backfill_entered", "backfill_boot_slice_start"]
    assert rows[-1]["companies"] == "60"
    assert rows[-1]["rss_mb"] > 0


def test_reading_never_starts_work_and_never_raises_on_a_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("INSTITUTIONAL_WAREHOUSE_ROOT", str(tmp_path / "nothing-here"))
    out = ms.read_stages()
    assert out["ok"] is True
    assert out["records"] == 0
    assert out["stages"] == []


def test_records_survive_being_written_by_another_process():
    """The sidecar measures; uvicorn reports. They share only the disk."""
    ms.heartbeat("written_by_the_sidecar")
    path = ms._path()
    assert os.path.exists(path)
    with open(path) as handle:
        assert json.loads(handle.readlines()[-1])["stage"] == "written_by_the_sidecar"


def test_the_worst_stage_is_surfaced_without_reading_every_row():
    with ms.stage("small"):
        pass
    with ms.stage("large"):
        blob = [bytearray(1024 * 1024) for _ in range(150)]
        del blob
    worst = ms.read_stages()["largest_peak_stage"]
    assert worst["stage"] == "large"


def test_the_file_stays_bounded():
    for i in range(1200):
        ms.heartbeat(f"tick{i}", padding="x" * 400)
    assert os.path.getsize(ms._path()) < 1_000_000
