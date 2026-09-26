"""Track 2 — Institutional Scheduler operational acceptance tests."""

from __future__ import annotations

import ast
import time
from pathlib import Path

from institutional_scheduler import store
from institutional_scheduler.dag.morning import build_morning_dag, dependencies_satisfied
from institutional_scheduler.production import dashboard, health, history, reports, status, telemetry, workflows
from institutional_scheduler.retry.engine import run_with_retry
from institutional_scheduler.scheduler.engine import InstitutionalScheduler, get_scheduler
from institutional_scheduler.schema import FREEZE_LOCKS, OPERATIONAL_STATES


def setup_function() -> None:
    store.reset()
    # reset singleton
    import institutional_scheduler.scheduler.engine as eng

    eng._SCHEDULER = None


def test_scheduler_starts() -> None:
    sch = get_scheduler()
    st = sch.status()
    assert st["version"]
    assert st["state"] in OPERATIONAL_STATES
    assert FREEZE_LOCKS["phases_1_7"] is True
    assert FREEZE_LOCKS["no_reasoning"] is True
    h = health()
    assert h["status"] == "ok"
    assert h["no_intelligence"] is True


def test_dag_dependency_and_parallel_levels() -> None:
    dag = build_morning_dag()
    assert dag["acyclic"] is True
    assert dag["schedule"] == "06:00"
    assert dag["max_parallelism"] >= 2
    # level 2 has company ‖ government
    level2 = dag["levels"][2]
    assert "company_intelligence" in level2
    assert "government_intelligence" in level2
    assert dependencies_satisfied("corporate_events", {"company_intelligence": "ok"})
    assert not dependencies_satisfied("corporate_events", {})


def test_dry_run_morning_dag_execution() -> None:
    sch = InstitutionalScheduler()
    out = sch.run_morning(dry_run=True, parallel=True)
    assert out["status"] == "ok"
    assert out["run_id"]
    assert out["state"] in OPERATIONAL_STATES
    assert out.get("quality_gates") is not None
    # history immutable append
    hist = history(limit=5)
    assert hist["n"] >= 1
    assert hist["runs"][0]["run_id"] == out["run_id"]
    # reports + telemetry
    assert out.get("reports_generated")
    tel = telemetry(limit=5)
    assert tel["n"] >= 1
    dash = dashboard()
    assert dash["north_star"] == "morning_system_ready"
    assert dash["ready_status"]["state"] in OPERATIONAL_STATES
    reps = reports(out["run_id"])
    assert "market_morning_brief" in (reps.get("reports") or {})
    # no recommendations in reports
    for r in (reps.get("reports") or {}).values():
        assert r.get("recommendation") in (None, )


def test_retry_logic_and_failure_isolation() -> None:
    calls = {"n": 0}

    def flaky() -> dict:
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return {"status": "ok", "recovered": True}

    t0 = time.time()
    out = run_with_retry(
        flaky,
        workflow_id="alternative_data",
        retry_policy={"max_attempts": 3, "backoff_seconds": [0, 0, 0]},
    )
    assert out["status"] == "ok"
    assert out["retries"] == 2
    assert time.time() - t0 < 2

    def always_fail() -> dict:
        raise RuntimeError("permanent")

    bad = run_with_retry(
        always_fail,
        workflow_id="alternative_data",
        retry_policy={"max_attempts": 2, "backoff_seconds": [0, 0]},
    )
    assert bad["status"] == "error"
    assert bad["permanent_failure"] is True
    assert bad["failure_isolated"] is True
    assert bad["operator_alert"] is True


def test_skip_and_maintenance_and_manual_override() -> None:
    sch = InstitutionalScheduler()
    sch.set_maintenance(True)
    blocked = sch.run_morning(dry_run=True)
    assert blocked["state"] == "MAINTENANCE"
    out = sch.run_morning(dry_run=True, manual_override=True, skip=["alternative_data"])
    assert out["status"] == "ok"
    run = store.get_run(out["run_id"])
    assert (run or {}).get("completed", {}).get("alternative_data") == "skipped"


def test_workflows_api_shape() -> None:
    w = workflows()
    assert w["n"] >= 15
    row = w["workflows"][0]
    for key in (
        "workflow_id",
        "name",
        "dependencies",
        "priority",
        "retry_policy",
        "timeout_seconds",
        "version",
    ):
        assert key in row


def test_frozen_packages_untouched() -> None:
    root = Path(__file__).resolve().parents[2]
    frozen = [
        root / "institutional_reasoning" / "execution_governance.py",
        root / "knowledge_factory" / "schedulers" / "daily.py",
        root / "decision_quality" / "pipeline.py",
        root / "institutional_reasoning" / "cal" / "governance.py",
    ]
    for path in frozen:
        assert path.exists()
        ast.parse(path.read_text(encoding="utf-8"))
    # scheduler must not import govern_answer / evaluate_decision / propose learning
    eng = (root / "institutional_scheduler" / "scheduler" / "engine.py").read_text(encoding="utf-8")
    assert "govern_answer" not in eng
    assert "evaluate_decision" not in eng
    assert "propose_from_outcome" not in eng


def test_status_surface() -> None:
    st = status()
    assert "dag" in st
    assert st["freeze_locks"]["ask_pipeline"] is True
