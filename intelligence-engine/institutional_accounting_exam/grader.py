"""Weighted rubric grader — Accounting correctness 20%, Statement linkage
20%, Interpretation 25%, Causal reasoning 20%, Honesty about uncertainty
10%, Hallucination penalty −15% (of max).

Every dimension is computed from properties the exam items themselves
report (booleans and keypoint-coverage ratios) — the grader does not
re-interpret free text; it aggregates what each ``ExamAnswer`` already
verified against the actual engine output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from institutional_accounting_exam.schema import RELEASE_GATE, RUBRIC_WEIGHTS, ExamAnswer, ExamItem


@dataclass
class ItemResult:
    item: ExamItem
    answer: ExamAnswer
    accounting_score: float  # None represented as -1 => excluded from aggregate
    linkage_score: float
    interpretation_score: float
    causal_score: float
    uncertainty_score: float  # -1 if N/A
    hallucinated: bool


def _ratio(checks: dict[str, bool]) -> float:
    if not checks:
        return -1.0
    return sum(1 for v in checks.values() if v) / len(checks)


def _keypoint_ratio(answer: ExamAnswer) -> float:
    if not answer.interpretation_keypoints_expected:
        return -1.0
    return len(answer.interpretation_keypoints_matched) / len(answer.interpretation_keypoints_expected)


def grade_item(item: ExamItem) -> ItemResult:
    answer = item.run()
    return ItemResult(
        item=item,
        answer=answer,
        accounting_score=_ratio(answer.accounting_checks),
        linkage_score=_ratio(answer.linkage_checks),
        interpretation_score=_keypoint_ratio(answer),
        causal_score=1.0 if answer.causal_reasoning_present else 0.0,
        uncertainty_score=(1.0 if answer.admits_uncertainty_correctly else 0.0) if answer.admits_uncertainty_correctly is not None else -1.0,
        hallucinated=answer.hallucination_detected,
    )


def _avg_excluding_na(values: list[float]) -> float:
    applicable = [v for v in values if v >= 0]
    return sum(applicable) / len(applicable) if applicable else 1.0


@dataclass
class ExamReport:
    item_results: list[ItemResult]
    dimension_scores: dict[str, float]
    overall_score: float
    release_gate: dict[str, Any]
    passed: bool


def grade_exam(items: list[ExamItem]) -> ExamReport:
    results = [grade_item(i) for i in items]

    accounting_dim = _avg_excluding_na([r.accounting_score for r in results])
    linkage_dim = _avg_excluding_na([r.linkage_score for r in results])
    interpretation_dim = _avg_excluding_na([r.interpretation_score for r in results])
    causal_dim = sum(r.causal_score for r in results) / len(results) if results else 0.0
    uncertainty_dim = _avg_excluding_na([r.uncertainty_score for r in results])
    hallucination_rate = sum(1 for r in results if r.hallucinated) / len(results) if results else 0.0

    dimension_scores = {
        "accounting_correctness": round(accounting_dim, 4),
        "statement_linkage": round(linkage_dim, 4),
        "interpretation": round(interpretation_dim, 4),
        "causal_reasoning": round(causal_dim, 4),
        "honesty_about_uncertainty": round(uncertainty_dim, 4),
        "hallucination_rate": round(hallucination_rate, 4),
    }

    overall = (
        accounting_dim * RUBRIC_WEIGHTS["accounting_correctness"]
        + linkage_dim * RUBRIC_WEIGHTS["statement_linkage"]
        + interpretation_dim * RUBRIC_WEIGHTS["interpretation"]
        + causal_dim * RUBRIC_WEIGHTS["causal_reasoning"]
        + uncertainty_dim * RUBRIC_WEIGHTS["honesty_about_uncertainty"]
        + hallucination_rate * RUBRIC_WEIGHTS["hallucination_penalty"]  # weight is already negative
    )
    overall = max(0.0, round(overall, 4))

    # Release gate — Section A items are the "journal accuracy" proof;
    # every item's linkage_checks (where applicable) must be 100% for
    # "statement linkage accuracy".
    section_a_results = [r for r in results if r.item.section == "A"]
    journal_accuracy = _avg_excluding_na([r.accounting_score for r in section_a_results]) if section_a_results else 1.0
    linkage_accuracy = _avg_excluding_na([r.linkage_score for r in results])

    gate = {
        "min_overall_score_met": overall >= RELEASE_GATE["min_overall_score"],
        "min_journal_accuracy_met": journal_accuracy >= RELEASE_GATE["min_journal_accuracy"],
        "min_statement_linkage_accuracy_met": linkage_accuracy >= RELEASE_GATE["min_statement_linkage_accuracy"],
        "zero_hallucinations_met": hallucination_rate <= RELEASE_GATE["max_hallucination_rate"],
        "uncertainty_admission_met": uncertainty_dim >= 1.0,
        "journal_accuracy": round(journal_accuracy, 4),
        "statement_linkage_accuracy": round(linkage_accuracy, 4),
        "overall_score": overall,
        "hallucination_rate": hallucination_rate,
    }
    passed = all(
        gate[k] for k in (
            "min_overall_score_met", "min_journal_accuracy_met", "min_statement_linkage_accuracy_met",
            "zero_hallucinations_met", "uncertainty_admission_met",
        )
    )

    return ExamReport(
        item_results=results, dimension_scores=dimension_scores, overall_score=overall,
        release_gate=gate, passed=passed,
    )
