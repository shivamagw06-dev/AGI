"""Institutional Accounting Exam — production facade."""

from __future__ import annotations

from typing import Any

from institutional_accounting_exam.all_items import ALL_EXAM_ITEMS, items_by_section
from institutional_accounting_exam.grader import grade_exam
from institutional_accounting_exam.schema import EXAM_VERSION, PASSING_SCORE, PROGRAMME, RELEASE_GATE, RUBRIC_WEIGHTS


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "exam_version": EXAM_VERSION,
        "total_items": len(ALL_EXAM_ITEMS),
        "sections": sorted({i.section for i in ALL_EXAM_ITEMS}),
        "passing_score": PASSING_SCORE,
        "rubric_weights": RUBRIC_WEIGHTS,
        "release_gate": RELEASE_GATE,
        "api_prefix": "/v1/institutional-accounting-exam",
        "fabricated": False,
    }


def list_items(section: str | None = None) -> dict[str, Any]:
    items = items_by_section(section) if section else ALL_EXAM_ITEMS
    return {
        "n": len(items),
        "items": [{"id": i.id, "section": i.section, "number": i.number, "prompt": i.prompt} for i in items],
        "fabricated": False,
    }


def run_full_exam() -> dict[str, Any]:
    report = grade_exam(ALL_EXAM_ITEMS)
    return {
        "exam_version": EXAM_VERSION,
        "total_items": len(ALL_EXAM_ITEMS),
        "dimension_scores": report.dimension_scores,
        "overall_score": report.overall_score,
        "passing_score": PASSING_SCORE,
        "release_gate": report.release_gate,
        "passed": report.passed,
        "items": [
            {
                "id": r.item.id, "section": r.item.section, "prompt": r.item.prompt,
                "answer": r.answer.answer_text, "accounting_score": r.accounting_score,
                "linkage_score": r.linkage_score, "interpretation_score": r.interpretation_score,
                "causal_reasoning_present": bool(r.causal_score), "hallucination_detected": r.hallucinated,
            }
            for r in report.item_results
        ],
    }


def run_item(item_id: str) -> dict[str, Any]:
    from institutional_accounting_exam.grader import grade_item

    item = next((i for i in ALL_EXAM_ITEMS if i.id == item_id), None)
    if not item:
        return {"found": False, "item_id": item_id}
    result = grade_item(item)
    return {
        "found": True,
        "id": item.id,
        "section": item.section,
        "prompt": item.prompt,
        "answer": result.answer.answer_text,
        "evidence": result.answer.evidence,
        "accounting_score": result.accounting_score,
        "linkage_score": result.linkage_score,
        "interpretation_score": result.interpretation_score,
        "causal_reasoning_present": bool(result.causal_score),
        "hallucination_detected": result.hallucinated,
    }
