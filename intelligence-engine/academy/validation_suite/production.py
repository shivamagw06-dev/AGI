"""Academy Validation Suite production facade — demonstrate knowledge, not ingest status."""

from __future__ import annotations

from typing import Any

from academy.validation_suite.catalog import all_exams, exam_by_id, exams_for_level
from academy.validation_suite.grader import grade
from academy.validation_suite.memory import reset_memory
from academy.validation_suite.reasoner import reason
from academy.validation_suite.schema import AVS_VERSION, LEVELS


def is_enabled() -> bool:
    try:
        from app.core.config import get_settings

        s = get_settings()
        return bool(getattr(s, "academy", True)) and bool(
            getattr(s, "academy_validation_suite", True)
        )
    except Exception:
        return True


def list_exams(*, level: int | None = None) -> dict[str, Any]:
    items = exams_for_level(level) if level else all_exams()
    return {
        "enabled": is_enabled(),
        "version": AVS_VERSION,
        "count": len(items),
        "exams": [e.to_dict() for e in items],
        "levels": LEVELS,
    }


def run_exam(exam_id: str) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "exam_id": exam_id}
    exam = exam_by_id(exam_id)
    if exam is None:
        return {"ok": False, "reason": "unknown_exam", "exam_id": exam_id}
    reasoned = reason(exam)
    result = grade(exam, reasoned)
    out = result.to_dict()
    out["ok"] = True
    out["enabled"] = True
    out["knowledge_refs"] = reasoned.get("knowledge_refs") or {}
    return out


def run_level(level: int) -> dict[str, Any]:
    if not is_enabled():
        return {"enabled": False, "level": level}
    results = []
    for exam in exams_for_level(level):
        reasoned = reason(exam)
        results.append(grade(exam, reasoned).to_dict())
    passed = sum(1 for r in results if r.get("passed"))
    return {
        "enabled": True,
        "version": AVS_VERSION,
        "level": level,
        "level_name": LEVELS.get(level),
        "passed": passed,
        "total": len(results),
        "pass_rate": round(passed / max(1, len(results)), 3),
        "results": results,
        "level_passed": passed == len(results) and len(results) > 0,
    }


def run_suite(*, levels: list[int] | None = None) -> dict[str, Any]:
    """Run the full Academy Validation Suite (or selected levels)."""
    if not is_enabled():
        return {"enabled": False, "version": AVS_VERSION}
    selected = levels or list(LEVELS.keys())
    by_level = {}
    all_results = []
    for lvl in selected:
        block = run_level(int(lvl))
        by_level[str(lvl)] = {
            "level_name": block.get("level_name"),
            "passed": block.get("passed"),
            "total": block.get("total"),
            "pass_rate": block.get("pass_rate"),
            "level_passed": block.get("level_passed"),
        }
        all_results.extend(block.get("results") or [])

    total = len(all_results)
    passed = sum(1 for r in all_results if r.get("passed"))
    failed = [r["exam_id"] for r in all_results if not r.get("passed")]
    return {
        "enabled": True,
        "programme": "AGI_ACADEMY_VALIDATION_SUITE",
        "version": AVS_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "question": "Can the intelligence demonstrate institutional knowledge?",
        "not": "Did it ingest the book?",
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / max(1, total), 3),
        "suite_passed": passed == total and total > 0,
        "by_level": by_level,
        "failed_exam_ids": failed,
        "results": all_results,
        "retrieval_policy": {
            "demonstrate": [
                "concept_recall",
                "framework_application",
                "cross_book_synthesis",
                "case_transfer",
                "counter_examples",
                "analyst_exams",
                "memory",
                "decision_chain",
            ],
            "never": ["book_quotation", "pdf_retrieval", "chapter_dump"],
        },
    }


def dashboard() -> dict[str, Any]:
    summary = run_suite()
    return {
        "programme": "AGI_ACADEMY_VALIDATION_SUITE",
        "version": AVS_VERSION,
        "enabled": is_enabled(),
        "architecture_status": "v1.0.1 LOCKED",
        "suite_passed": summary.get("suite_passed"),
        "pass_rate": summary.get("pass_rate"),
        "passed": summary.get("passed"),
        "total": summary.get("total"),
        "by_level": summary.get("by_level"),
        "failed_exam_ids": summary.get("failed_exam_ids"),
        "exam_count": len(all_exams()),
        "levels": LEVELS,
        "no_redesign": [
            "engine",
            "cid",
            "company_analysis",
            "financial_analyst",
            "valuation_analyst",
            "investment_committee",
            "cio",
            "irw",
            "provider",
            "ui",
        ],
    }


def quality_gates() -> dict[str, Any]:
    suite = run_suite()
    checks = {
        "suite_enabled": is_enabled(),
        "has_all_eight_levels": set(suite.get("by_level") or {}) >= {str(i) for i in range(1, 9)},
        "level1_concept_recall": bool((suite.get("by_level") or {}).get("1", {}).get("level_passed")),
        "level2_framework_application": bool(
            (suite.get("by_level") or {}).get("2", {}).get("level_passed")
        ),
        "level3_cross_book_synthesis": bool(
            (suite.get("by_level") or {}).get("3", {}).get("level_passed")
        ),
        "level4_case_transfer": bool((suite.get("by_level") or {}).get("4", {}).get("level_passed")),
        "level5_counter_examples": bool(
            (suite.get("by_level") or {}).get("5", {}).get("level_passed")
        ),
        "level6_analyst_exams": bool((suite.get("by_level") or {}).get("6", {}).get("level_passed")),
        "level7_memory": bool((suite.get("by_level") or {}).get("7", {}).get("level_passed")),
        "level8_decision": bool((suite.get("by_level") or {}).get("8", {}).get("level_passed")),
        "suite_passed": bool(suite.get("suite_passed")),
        "no_pdf_provenance": all(
            not (r.get("provenance") or {}).get("pdf_used") for r in suite.get("results") or []
        ),
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "version": AVS_VERSION,
        "failed_exam_ids": suite.get("failed_exam_ids") or [],
        "pass_rate": suite.get("pass_rate"),
    }


def reset_for_tests() -> None:
    reset_memory()
