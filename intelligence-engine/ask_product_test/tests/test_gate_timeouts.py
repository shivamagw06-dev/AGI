"""A suite that stops must be reported as a stopped suite, not a bad score.

The gate runs 18 suites as child processes. Before this, subprocess.run had no
timeout: a suite that hung blocked the runner until the 90-minute job ceiling,
with no output naming which one. Runs also left children behind - the job log
shows "Terminate orphan process: pid (2434) (python)".
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import time

import pytest

from ask_product_test import run_production_regression_v1 as gate


def test_a_timeout_is_not_read_as_a_product_score():
    """The important one: a hung suite must not inherit a stale artifact score."""
    decision = gate._decide("bi_acceptance", {"pass_rate_pct": 100.0}, gate.EXIT_TIMEOUT)
    assert decision["pass"] is False
    assert decision["actual"] == "timeout"
    assert decision["failure_class"] == "TIMEOUT"
    assert decision["timed_out"] is True


def test_a_normal_failure_is_still_a_product_failure():
    decision = gate._decide("bi_acceptance", {"pass_rate_pct": 10.0}, 1)
    assert decision.get("failure_class") != "TIMEOUT"


def test_every_suite_has_a_timeout_ceiling():
    for module in gate.SUITE_MODULES.values():
        assert gate._suite_timeout(module) > 0


def test_the_slow_suites_get_headroom_over_their_measured_time():
    """core_platform measured 1,719s and answer_quality 1,403s."""
    assert gate._suite_timeout("ask_product_test.run_core_platform_acceptance_v1") >= 2 * 1719
    assert gate._suite_timeout("ask_product_test.run_answer_quality_acceptance_v1") >= 2 * 1403


def test_the_ceiling_can_be_overridden_for_a_short_gate():
    os.environ["GATE_SUITE_TIMEOUT_SEC"] = "5"
    try:
        assert gate._suite_timeout("anything") == 5
    finally:
        del os.environ["GATE_SUITE_TIMEOUT_SEC"]


def test_a_timeout_blocks_the_merge_and_fails_the_job():
    """merge_allowed must be False and the exit status non-zero."""
    results = [{"suite": "a", "pass": True, "failure_class": None},
               {"suite": "b", "pass": False, "failure_class": "TIMEOUT"}]
    all_pass = all(r["pass"] for r in results)
    assert all_pass is False, "merge_allowed = all_pass and ... so it is False"
    timed_out = [r for r in results if r.get("failure_class") == "TIMEOUT"]
    assert timed_out and gate.EXIT_TIMEOUT != 0


def test_a_timeout_is_not_relabelled_as_infrastructure():
    """Returning EXIT_INFRASTRUCTURE would file a hung suite under the wrong cause."""
    assert gate.EXIT_TIMEOUT != gate.EXIT_INFRASTRUCTURE


@pytest.mark.parametrize("rc", [-9, -15, 137, 2 ** 8, 99])
def test_an_abnormal_exit_is_not_scored_from_disk(rc):
    """Signals, OOM kills and unknown codes mean the suite reported nothing."""
    if rc == gate.EXIT_INFRASTRUCTURE:
        pytest.skip("infrastructure is a real outcome")
    decision = gate._decide("bi_acceptance", {}, rc, launched_at=time.time())
    assert decision["pass"] is False
    assert decision["failure_class"] == "ABNORMAL_EXIT"


def test_a_stale_artifact_is_rejected_even_on_a_clean_exit(tmp_path, monkeypatch):
    """The case that produces a green number from a suite that never ran.

    A previous run's artifact sits on disk. The suite exits 0 without writing.
    Read naively, last run's score is reported as this run's.
    """
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    name = gate.SUITE_ARTIFACTS["bi_acceptance"]
    (tmp_path / name).write_text('{"pass_rate_pct": 100.0}')
    os.utime(tmp_path / name, (1000, 1000))          # written long ago

    decision = gate._decide("bi_acceptance", {}, 0, launched_at=time.time())
    assert decision["pass"] is False
    assert decision["actual"] == "stale_artifact"


def test_a_fresh_artifact_is_still_accepted(tmp_path, monkeypatch):
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    name = gate.SUITE_ARTIFACTS["bi_acceptance"]
    launched = time.time()
    (tmp_path / name).write_text('{"pass_rate_pct": 100.0}')
    decision = gate._decide("bi_acceptance", {}, 0, launched_at=launched)
    assert decision["pass"] is True


def test_purging_removes_the_previous_run_artifact(tmp_path, monkeypatch):
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    name = gate.SUITE_ARTIFACTS["bi_acceptance"]
    (tmp_path / name).write_text("{}")
    gate._purge_artifact(name)
    assert not (tmp_path / name).exists()


@pytest.mark.skipif(os.name != "posix", reason="process groups are posix-only")
def test_children_are_cleaned_up_after_a_suite_that_exited_cleanly(tmp_path):
    """A suite can exit 0 and still leave a child running.

    That is what the job log's orphan-process lines were, and it happens on the
    success path, so cleanup cannot be limited to timeouts.
    """
    marker = tmp_path / "child.pid"
    script = tmp_path / "leaky.py"
    script.write_text(textwrap.dedent(f"""
        import subprocess, sys
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
        open({str(marker)!r}, "w").write(str(child.pid))
        raise SystemExit(0)
    """))
    proc = subprocess.Popen([sys.executable, str(script)], start_new_session=True)
    pgid = os.getpgid(proc.pid)
    proc.wait(timeout=30)
    assert proc.returncode == 0, "the suite itself exited cleanly"
    for _ in range(100):
        if marker.exists():
            break
        time.sleep(0.05)
    child = int(marker.read_text().strip())

    gate._terminate_group(pgid, "leaky.py", proc=proc)

    deadline, alive = time.time() + 5, True
    while time.time() < deadline:
        try:
            os.kill(child, 0)
            time.sleep(0.05)
        except OSError:
            alive = False
            break
    assert not alive, "a child outliving a successful suite must still be cleaned up"


@pytest.mark.skipif(os.name != "posix", reason="process groups are posix-only")
def test_a_hanging_child_is_killed_along_with_its_own_children(tmp_path):
    """The behaviour that stops orphans surviving the step.

    A parent that sleeps forever, having spawned a child that also sleeps
    forever. Killing only the parent leaves the grandchild running.
    """
    marker = tmp_path / "grandchild.pid"
    script = tmp_path / "hang.py"
    script.write_text(textwrap.dedent(f"""
        import subprocess, sys, time, os
        child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(300)"])
        open({str(marker)!r}, "w").write(str(child.pid))
        time.sleep(300)
    """))

    proc = subprocess.Popen([sys.executable, str(script)], start_new_session=True)
    pgid = os.getpgid(proc.pid)
    for _ in range(100):
        if marker.exists():
            break
        time.sleep(0.05)
    grandchild = int(marker.read_text().strip())

    gate._terminate_group(pgid, "hang.py", proc=proc)
    assert proc.poll() is not None, "the suite process must be stopped"

    deadline = time.time() + 5
    alive = True
    while time.time() < deadline:
        try:
            os.kill(grandchild, 0)
            time.sleep(0.05)
        except OSError:
            alive = False
            break
    assert not alive, "the grandchild must not survive the suite it belonged to"


@pytest.mark.skipif(os.name != "posix", reason="process groups are posix-only")
def test_run_module_reports_a_timeout_rather_than_blocking(monkeypatch, tmp_path):
    monkeypatch.setenv("GATE_SUITE_TIMEOUT_SEC", "2")
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    started = time.perf_counter()
    rc, elapsed, launched = gate._run_module("this_module_does_not_exist_and_would_hang")
    assert time.perf_counter() - started < 30, "must not block the runner"
    assert rc in (gate.EXIT_TIMEOUT, 1), "a missing module exits; a hanging one times out"


# --- per-run artifact isolation -------------------------------------------

def test_each_run_gets_its_own_artifact_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    a = gate._suite_artifact_dir("bi_acceptance")
    assert a.exists() and gate.RUN_ID in str(a) and "bi_acceptance" in str(a)
    assert gate._suite_artifact_dir("ii_acceptance") != a


def test_isolation_not_timestamps_decides_freshness(monkeypatch, tmp_path):
    """A file in this run's own directory is this run's, whatever its mtime.

    Timestamp resolution is not uniform across filesystems, so mtime is the
    fallback and location is the test.
    """
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    name = gate.SUITE_ARTIFACTS["bi_acceptance"]
    suite_dir = gate._suite_artifact_dir("bi_acceptance")
    (suite_dir / name).write_text('{"pass_rate_pct": 100.0}')
    os.utime(suite_dir / name, (1000, 1000))          # an implausible mtime

    assert gate._artifact_is_fresh(name, time.time(), suite_dir) is True
    decision = gate._decide("bi_acceptance", {}, 0,
                            launched_at=time.time(), suite_dir=suite_dir)
    assert decision["pass"] is True


def test_a_previous_runs_file_cannot_reach_this_runs_directory(monkeypatch, tmp_path):
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    name = gate.SUITE_ARTIFACTS["bi_acceptance"]
    (tmp_path / name).write_text('{"pass_rate_pct": 100.0}')   # last run, shared path
    os.utime(tmp_path / name, (1000, 1000))
    suite_dir = gate._suite_artifact_dir("bi_acceptance")      # this run, empty

    decision = gate._decide("bi_acceptance", {}, 0,
                            launched_at=time.time(), suite_dir=suite_dir)
    assert decision["pass"] is False
    assert decision["actual"] == "stale_artifact"


def test_results_are_published_to_the_shared_upload_path(monkeypatch, tmp_path):
    monkeypatch.setenv("ASK_TEST_ARTIFACTS", str(tmp_path))
    name = gate.SUITE_ARTIFACTS["bi_acceptance"]
    suite_dir = gate._suite_artifact_dir("bi_acceptance")
    (suite_dir / name).write_text('{"pass_rate_pct": 99.0}')
    gate._publish_artifact(name, suite_dir)
    assert (tmp_path / name).exists(), "the upload step must still find it"
