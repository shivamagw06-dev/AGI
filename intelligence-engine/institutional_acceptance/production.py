"""PAT-01 production façades — Acceptance Center + runner APIs."""

from __future__ import annotations

from typing import Any, Optional

from institutional_acceptance.dashboards import acceptance_center_board
from institutional_acceptance.diagnostics import build_diagnostics
from institutional_acceptance.flags import flags_dict, harness_mode, is_enabled
from institutional_acceptance.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_GENERAL_AVAILABILITY,
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    ACCEPTANCE_ENGINE_VERSION,
    GUIDING_PRINCIPLE,
    PAT_PRODUCT,
    PAT_ROLE,
    PAT_SPEC,
    PAT_VERSION,
    PAT_WORKSTREAM_ID,
    SUCCESS_CRITERIA,
)
from institutional_acceptance import test_runner

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    test_runner.reset_for_tests()


def health() -> dict[str, Any]:
    last = test_runner.last_report() or {}
    board = acceptance_center_board(last) if last else {"acceptance_center": True, "certified": False}
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": PAT_WORKSTREAM_ID,
        "product": PAT_PRODUCT,
        "version": PAT_VERSION,
        "role": PAT_ROLE,
        "llm": False,
        "is_production_acceptance": True,
        "is_feature_expansion": False,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "agib_general_availability": AGIB_GENERAL_AVAILABILITY,
        "acceptance_engine_version": ACCEPTANCE_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "success_criteria": dict(SUCCESS_CRITERIA),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "harness": harness_mode(),
        "spec": PAT_SPEC,
        "brand": "AGI",
        "programme": "Production Acceptance",
        "phase": "pre_user_onboarding",
        "as_of": now_iso(),
        "closed_beta_next": (
            "After PAT: closed beta with 5–10 experienced finance professionals"
        ),
        **board,
    }


def soft_slice_mission_control() -> dict[str, Any]:
    last = test_runner.last_report()
    if not is_enabled():
        return {
            "status": "disabled",
            "workstream_id": PAT_WORKSTREAM_ID,
            "acceptance_center": False,
        }
    if last is None:
        # Cheap board without full run
        board = {
            "acceptance_center": True,
            "certified": False,
            "overall_result": "NOT RUN",
            "total_cases": None,
            "passed": None,
            "failed": None,
            "closed_beta_recommendation": (
                "After PAT passes: closed beta with 5–10 experienced finance professionals."
            ),
        }
    else:
        board = acceptance_center_board(last)
    return {
        "status": "certified" if board.get("certified") else "ok",
        "workstream_id": PAT_WORKSTREAM_ID,
        "product": PAT_PRODUCT,
        "version": PAT_VERSION,
        "llm": False,
        **board,
    }


def run(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    mode = str(body.get("mode") or ("harness" if harness_mode() else "live"))
    include_stress = bool(body.get("include_stress", True))
    report = test_runner.run_all(mode=mode, include_stress=include_stress)
    return {
        "ok": bool(report.get("certified")),
        "workstream_id": PAT_WORKSTREAM_ID,
        **report,
    }


def report_api() -> dict[str, Any]:
    last = test_runner.last_report()
    if last is None:
        last = test_runner.run_all()
    return {"ok": bool(last.get("certified")), "workstream_id": PAT_WORKSTREAM_ID, **last}


def cases_api(limit: int = 500) -> dict[str, Any]:
    cases = test_runner.last_cases()
    if not cases:
        test_runner.run_all()
        cases = test_runner.last_cases()
    lim = max(1, min(int(limit or 500), 2000))
    return {
        "ok": True,
        "workstream_id": PAT_WORKSTREAM_ID,
        "total": len(cases),
        "cases": cases[:lim],
    }


def phase_api(phase: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    mode = str(body.get("mode") or ("harness" if harness_mode() else "live"))
    cases = test_runner.run_phase(str(phase or ""), mode=mode)
    failed = sum(1 for c in cases if c.get("status") == "FAIL")
    return {
        "ok": failed == 0 and bool(cases),
        "workstream_id": PAT_WORKSTREAM_ID,
        "phase": phase,
        "total": len(cases),
        "failed": failed,
        "cases": cases,
    }


def diagnostics_api() -> dict[str, Any]:
    return {"ok": True, **build_diagnostics()}
