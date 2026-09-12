"""Score ACS exam answers into 0–100 institutional scores."""

from __future__ import annotations

from typing import Any

from academy.certification.grading.scale import band_for, is_pass
from academy.certification.schema import ExamScore, ExamSpec


def score_exam(exam: ExamSpec, reasoned: dict[str, Any]) -> ExamScore:
    answer = (reasoned.get("answer") or "").lower()
    structure = reasoned.get("structure") or {}
    blob = f"{answer}\n{structure}".lower()

    checks: list[tuple[str, bool]] = []

    # Structural richness
    checks.append(("has_conclusion", bool(structure.get("conclusion") or "conclusion" in blob)))
    checks.append(("answer_length", len(answer) >= 120))
    checks.append(("no_book_quote", not any(x in blob for x in ("on page ", "chapter 1", ".pdf", "according to the book"))))

    # Must-include vocabulary (70% threshold)
    must = exam.must_include or []
    if must:
        hits = sum(1 for m in must if m.lower() in blob)
        need = max(1, int(round(len(must) * 0.7)))
        checks.append(("vocabulary", hits >= need))
    else:
        checks.append(("vocabulary", True))

    # Level-specific
    lvl = exam.level
    if lvl == 1:
        checks += [
            ("definition", "definition" in blob or bool(structure.get("definition"))),
            ("why", "why" in blob or bool(structure.get("why_it_matters"))),
            ("when_use", "when to" in blob or bool(structure.get("when_to_apply"))),
            ("when_not", "when not" in blob or bool(structure.get("when_not_to_apply"))),
        ]
    elif lvl == 2:
        checks += [
            ("evidence", "evidence" in blob or bool(structure.get("company_specific_evidence"))),
            ("framework", bool(exam.framework) and (exam.framework.lower() in blob or bool(structure.get("sections")))),
            ("company", bool(exam.company) and (exam.company.split()[0].lower() in blob or bool(structure.get("company")))),
        ]
    elif lvl == 3:
        authors = ["damodaran", "graham", "fisher", "klarman", "fridson"]
        checks.append(("multi_author", sum(1 for a in authors if a in blob) >= 3))
        checks.append(("unified", "institutional" in blob or bool(structure.get("unified_institutional_view"))))
    elif lvl == 4:
        checks += [
            ("analogue", "analogue" in blob or "resemble" in blob or bool(structure.get("analogue"))),
            ("similar", "similar" in blob),
            ("differ", "differ" in blob),
            ("lesson", "lesson" in blob),
        ]
    elif lvl == 5:
        checks += [
            ("exceptions", "exception" in blob or "misleading" in blob or bool(structure.get("exceptions"))),
            ("not_universal", "not" in blob and ("always" in blob or "universal" in blob or "only" in blob or bool(structure.get("not_universal")))),
        ]
    elif lvl == 6:
        checks.append(("analyst_domain", exam.analyst in blob or bool(structure.get("analyst"))))
        checks.append(("points", len(structure.get("points") or []) >= 2 or blob.count("-") >= 2))
    elif lvl == 7:
        checks += [
            ("previous", "previous" in blob),
            ("updated", "updated" in blob or "current" in blob),
            ("changed", "changed" in blob or "trajectory" in blob),
        ]
    elif lvl == 8:
        for stage in ("business", "financial", "valuation", "risk", "committee"):
            checks.append((f"stage_{stage}", stage in blob))
        checks.append(("not_bare_yes_no", not blob.strip() in {"yes", "no", "yes.", "no."}))
    elif lvl == 9:
        checks.append(("case_recognized", bool(structure.get("case_profile") or structure.get("lessons"))))
    elif lvl == 10:
        checks.append(("pattern", bool(structure.get("pattern") or "pattern" in blob)))
    elif lvl == 11:
        checks.append(("portfolio_lens", any(k in blob for k in ("diversif", "correlation", "concentration", "drawdown", "factor"))))
    elif lvl == 12:
        checks.append(("accuracy_track", any(k in blob for k in ("correct", "wrong", "lesson", "outcome", "accuracy"))))
    elif lvl in (13, 14):
        checks.append(("coherence", "coherent" in blob or "without changing" in blob or bool(structure.get("coherence"))))
        checks.append(("pipeline", any(k in blob for k in ("committee", "analyst", "report", "cio"))))
    elif lvl == 15:
        checks.append(("degrade", any(k in blob for k in ("degrade", "low confidence", "incomplete", "missing", "conflict"))))
    elif lvl == 16:
        checks.append(("benchmark_company", bool(exam.company) and exam.company.split()[0].lower() in blob))
    elif lvl == 17:
        checks.append(("coverage", any(k in blob for k in ("coverage", "confidence", "framework", "case", "decision"))))
    elif lvl == 18:
        checks.append(("iq_rollup", "overall" in blob or bool(structure.get("overall_iq"))))

    passed_n = sum(1 for _, ok in checks if ok)
    total = max(1, len(checks))
    score = round(100.0 * passed_n / total, 2)
    band = band_for(score)
    return ExamScore(
        exam_id=exam.exam_id,
        level=exam.level,
        analyst=exam.analyst,
        score=score,
        passed=is_pass(score, floor=70.0),  # per-exam developing floor; suite uses 80 overall
        band=band["label"],
        answer=reasoned.get("answer") or "",
        criteria_passed=passed_n,
        criteria_total=total,
        details={"checks": [{"name": n, "passed": ok} for n, ok in checks], "letter": band["letter"]},
    )
