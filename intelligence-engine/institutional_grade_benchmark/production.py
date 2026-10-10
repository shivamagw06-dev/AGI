"""IB-01 production façades — Benchmark Center + scoring APIs."""

from __future__ import annotations

from typing import Any, Optional

from institutional_grade_benchmark.dashboards import benchmark_center_board
from institutional_grade_benchmark.diagnostics import build_diagnostics
from institutional_grade_benchmark.flags import flags_dict, harness_mode, is_enabled
from institutional_grade_benchmark import runner, store
from institutional_grade_benchmark.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    AGIB_GENERAL_AVAILABILITY,
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    BENCHMARK_ENGINE_VERSION,
    GUIDING_PRINCIPLE,
    IB_PRODUCT,
    IB_ROLE,
    IB_SPEC,
    IB_VERSION,
    IB_WORKSTREAM_ID,
    PASS_THRESHOLD,
    TOTAL_POINTS,
)

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def reset_for_tests() -> None:
    runner.reset_for_tests()


def health() -> dict[str, Any]:
    last = runner.last_report() or {}
    board = (
        benchmark_center_board(last)
        if last
        else {"benchmark_center": True, "institutional_grade": False}
    )
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": IB_WORKSTREAM_ID,
        "product": IB_PRODUCT,
        "version": IB_VERSION,
        "role": IB_ROLE,
        "llm": False,
        "is_competitive_intelligence_test": True,
        "is_software_acceptance": False,
        "distinct_from_pat": True,
        "distinct_from_ibs": True,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "agib_platform_version": AGIB_PLATFORM_VERSION,
        "agib_general_availability": AGIB_GENERAL_AVAILABILITY,
        "benchmark_engine_version": BENCHMARK_ENGINE_VERSION,
        "guiding_principle": GUIDING_PRINCIPLE,
        "total_points": TOTAL_POINTS,
        "pass_threshold": PASS_THRESHOLD,
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "harness": harness_mode(),
        "spec": IB_SPEC,
        "brand": "AGI",
        "programme": "Institutional Benchmark",
        "phase": "competitive_validation",
        "as_of": now_iso(),
        **board,
    }


def soft_slice_mission_control() -> dict[str, Any]:
    last = runner.last_report()
    if not is_enabled():
        return {
            "status": "disabled",
            "workstream_id": IB_WORKSTREAM_ID,
            "benchmark_center": False,
        }
    if last is None:
        board = {
            "benchmark_center": True,
            "institutional_grade": False,
            "overall_result": "NOT RUN",
            "total_score": None,
            "total_max": TOTAL_POINTS,
            "pass_threshold": PASS_THRESHOLD,
            "mission": (
                "Can AGIB produce institutional-grade research comparable to "
                "Bloomberg, Capital IQ, FactSet, AlphaSense, and sell-side?"
            ),
            "distinct_from_pat": (
                "PAT proves the software works. IB-01 proves the investment "
                "intelligence is competitive."
            ),
        }
    else:
        board = benchmark_center_board(last)
    return {
        "status": "institutional_grade" if board.get("institutional_grade") else "ok",
        "workstream_id": IB_WORKSTREAM_ID,
        "product": IB_PRODUCT,
        "version": IB_VERSION,
        "llm": False,
        **board,
    }


def run(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    mode = str(body.get("mode") or ("harness" if harness_mode() else "live"))
    report = runner.run_all(mode=mode)
    return {"ok": True, "workstream_id": IB_WORKSTREAM_ID, **report}


def report_api() -> dict[str, Any]:
    last = runner.last_report()
    if last is None:
        last = runner.run_all()
    return {"ok": True, "workstream_id": IB_WORKSTREAM_ID, **last}


def section_api(section: str, payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    mode = str(body.get("mode") or ("harness" if harness_mode() else "live"))
    return runner.run_section(section, mode=mode)


def blind_vote_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    return store.record_blind_vote(
        analyst_id=str(body.get("analyst_id") or "anonymous"),
        preferred_label=str(body.get("preferred_label") or body.get("preferred") or ""),
        ranking=body.get("ranking") if isinstance(body.get("ranking"), list) else None,
        comment=str(body.get("comment") or ""),
    )


def productivity_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    return store.record_productivity(
        group=str(body.get("group") or ""),
        completion_time_min=float(body.get("completion_time_min") or 0),
        confidence=float(body.get("confidence") or 0),
        quality=float(body.get("quality") or 0),
        n_analysts=int(body.get("n_analysts") or 1),
    )


def manual_score_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    store.set_manual_section_score(
        str(body.get("section") or ""),
        float(body.get("score") or 0),
        float(body.get("max") or 0),
    )
    return {"ok": True, "manual": store.manual_section_scores()}


def diagnostics_api() -> dict[str, Any]:
    return {"ok": True, **build_diagnostics()}


def reliance_productivity_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Productivity case: investment note on RELIANCE with measured metrics."""
    body = dict(payload or {})
    generate = body.get("generate_draft")
    if isinstance(generate, str):
        generate = generate.strip().lower() not in {"0", "false", "no", "off"}
    if generate is None:
        generate = True
    from institutional_grade_benchmark.cases.reliance_productivity import (
        run_reliance_productivity_case,
    )
    from institutional_grade_benchmark.publication_gates import evaluate_reliance_note_as_reviewed

    out = run_reliance_productivity_case(generate_draft=bool(generate))
    gates = evaluate_reliance_note_as_reviewed()
    out["pm_review"] = {
        "overall": gates.get("pm_overall_score"),
        "verdict": gates.get("pm_verdict"),
        "publication_allowed": gates.get("publication_allowed"),
        "blocking_failures": gates.get("blocking_failures"),
        "gates_passed": gates.get("gates_passed"),
        "gates_total": gates.get("gates_total"),
        "doc": "docs/research_notes/RELIANCE_PM_REVIEW.md",
    }
    out["publication_gates"] = gates
    return {"ok": bool(out.get("ok")), "workstream_id": IB_WORKSTREAM_ID, **out}


def publication_gates_api(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Evaluate a research-note payload (or Reliance ground truth) against PM gates."""
    from institutional_grade_benchmark.publication_gates import (
        evaluate_publication_readiness,
        evaluate_reliance_note_as_reviewed,
    )

    body = dict(payload or {})
    if body.get("case") == "reliance" or body.get("use_reliance_ground_truth"):
        out = evaluate_reliance_note_as_reviewed()
    else:
        note = body.get("note") if isinstance(body.get("note"), dict) else body
        out = evaluate_publication_readiness(note)
    return {"ok": True, "workstream_id": IB_WORKSTREAM_ID, **out}
