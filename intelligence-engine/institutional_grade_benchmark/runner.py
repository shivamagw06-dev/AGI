"""IB-01 master runner — sections A–H → 1000-point scorecard."""

from __future__ import annotations

from typing import Any, Optional

from institutional_grade_benchmark.dashboards import benchmark_center_board
from institutional_grade_benchmark.flags import harness_mode, is_enabled
from institutional_grade_benchmark.report import build_benchmark_report
from institutional_grade_benchmark.schema import IB_WORKSTREAM_ID, PASS_THRESHOLD, SECTIONS, TOTAL_POINTS
from institutional_grade_benchmark.sections import SECTION_SCORERS

_LAST: dict[str, Any] | None = None


def reset_for_tests() -> None:
    global _LAST
    from institutional_grade_benchmark import store

    store.reset_for_tests()
    _LAST = None


def last_report() -> dict[str, Any] | None:
    return dict(_LAST) if _LAST else None


def run_all(*, mode: Optional[str] = None) -> dict[str, Any]:
    global _LAST
    if not is_enabled():
        out = {
            "ok": False,
            "enabled": False,
            "workstream_id": IB_WORKSTREAM_ID,
            "institutional_grade": False,
            "total_score": 0,
            "overall_result": "DISABLED",
        }
        _LAST = out
        return out

    run_mode = mode or ("harness" if harness_mode() else "live")
    sections: list[dict[str, Any]] = []
    for _code, key, _title, _max in SECTIONS:
        scorer = SECTION_SCORERS[key]
        sections.append(scorer(mode=run_mode))

    report = build_benchmark_report(sections, mode=run_mode)
    report["ok"] = True
    report["enabled"] = True
    report["total_points"] = TOTAL_POINTS
    report["pass_threshold"] = PASS_THRESHOLD
    report["board"] = benchmark_center_board(report)
    _LAST = report
    return report


def run_section(section_key: str, *, mode: Optional[str] = None) -> dict[str, Any]:
    run_mode = mode or ("harness" if harness_mode() else "live")
    scorer = SECTION_SCORERS.get(section_key)
    if not scorer:
        return {"ok": False, "error": f"unknown section: {section_key}"}
    return {"ok": True, "section": scorer(mode=run_mode)}
