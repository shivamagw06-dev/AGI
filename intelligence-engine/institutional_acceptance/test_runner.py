"""PAT-01 master test runner — all 15 phases."""

from __future__ import annotations

from typing import Any, Optional

from institutional_acceptance.dashboards import acceptance_center_board
from institutional_acceptance.failure import run_failure_injection
from institutional_acceptance.flags import harness_mode, is_enabled
from institutional_acceptance.reports import build_certification_report
from institutional_acceptance.scenarios import PHASE_RUNNERS
from institutional_acceptance.schema import PAT_WORKSTREAM_ID, PHASES, SUCCESS_CRITERIA
from institutional_acceptance.stress import run_stress
from institutional_acceptance.workflow.analyst import run_end_to_end_workflow
from institutional_acceptance.workflow.stability import run_long_running_stability

_LAST_REPORT: dict[str, Any] | None = None
_LAST_CASES: list[dict[str, Any]] = []


def reset_for_tests() -> None:
    global _LAST_REPORT, _LAST_CASES
    _LAST_REPORT = None
    _LAST_CASES = []


def last_report() -> dict[str, Any] | None:
    return dict(_LAST_REPORT) if _LAST_REPORT else None


def last_cases() -> list[dict[str, Any]]:
    return list(_LAST_CASES)


def run_phase(phase_key: str, *, mode: str = "harness") -> list[dict[str, Any]]:
    if phase_key in PHASE_RUNNERS:
        return list(PHASE_RUNNERS[phase_key](mode=mode))
    if phase_key == "failure_injection":
        return list(run_failure_injection(mode=mode))
    if phase_key == "end_to_end_workflow":
        return list(run_end_to_end_workflow(mode=mode))
    if phase_key == "long_running_stability":
        return list(run_long_running_stability(mode=mode))
    if phase_key == "performance":
        # scenarios + stress execution
        base = list(PHASE_RUNNERS["performance"](mode=mode))
        base.extend(run_stress(mode=mode))
        return base
    return []


def run_all(*, mode: Optional[str] = None, include_stress: bool = True) -> dict[str, Any]:
    """Execute full Production Acceptance suite."""
    global _LAST_REPORT, _LAST_CASES
    if not is_enabled():
        report = {
            "ok": False,
            "enabled": False,
            "workstream_id": PAT_WORKSTREAM_ID,
            "certified": False,
            "overall_result": "DISABLED",
            "total": 0,
            "passed": 0,
            "failed": 0,
        }
        _LAST_REPORT = report
        _LAST_CASES = []
        return report

    run_mode = mode or ("harness" if harness_mode() else "live")
    cases: list[dict[str, Any]] = []

    for _code, key, _title in PHASES:
        if key == "performance":
            cases.extend(PHASE_RUNNERS["performance"](mode=run_mode))
            if include_stress:
                cases.extend(run_stress(mode=run_mode))
            continue
        if key == "failure_injection":
            cases.extend(run_failure_injection(mode=run_mode))
            continue
        if key == "end_to_end_workflow":
            cases.extend(run_end_to_end_workflow(mode=run_mode))
            continue
        if key == "long_running_stability":
            cases.extend(run_long_running_stability(mode=run_mode))
            continue
        runner = PHASE_RUNNERS.get(key)
        if runner:
            cases.extend(runner(mode=run_mode))

    report = build_certification_report(cases)
    report["ok"] = bool(report.get("certified"))
    report["enabled"] = True
    report["mode"] = run_mode
    report["min_test_cases"] = SUCCESS_CRITERIA["min_test_cases"]
    report["board"] = acceptance_center_board(report)
    _LAST_CASES = cases
    _LAST_REPORT = report
    return report


def summarize() -> dict[str, Any]:
    if _LAST_REPORT:
        return dict(_LAST_REPORT)
    return run_all()
