"""Grade Validation Suite answers against institutional pass criteria."""

from __future__ import annotations

from typing import Any

from academy.validation_suite.schema import LEVELS, CriterionResult, ExamItem, ExamResult


def grade(exam: ExamItem, reasoned: dict[str, Any]) -> ExamResult:
    answer = reasoned.get("answer") or ""
    structure = reasoned.get("structure") or {}
    text = f"{answer}\n{structure}".lower()

    criteria: list[CriterionResult] = []

    if exam.level == 1:
        criteria = _grade_l1(exam, structure, text)
    elif exam.level == 2:
        criteria = _grade_l2(exam, structure, text)
    elif exam.level == 3:
        criteria = _grade_l3(exam, structure, text)
    elif exam.level == 4:
        criteria = _grade_l4(exam, structure, text)
    elif exam.level == 5:
        criteria = _grade_l5(exam, structure, text)
    elif exam.level == 6:
        criteria = _grade_l6(exam, structure, text)
    elif exam.level == 7:
        criteria = _grade_l7(exam, structure, text)
    elif exam.level == 8:
        criteria = _grade_l8(exam, structure, text)

    # Global: no book quotation style
    criteria.append(
        CriterionResult(
            name="Does not quote books / PDFs",
            passed=not any(
                bad in text
                for bad in ("according to the book", "on page ", "chapter 1", ".pdf", "verbatim")
            ),
            detail="Institutional language only",
        )
    )

    # Must-include tokens (soft: require majority)
    if exam.must_include:
        hits = sum(1 for m in exam.must_include if m.lower() in text)
        need = max(1, int(round(len(exam.must_include) * 0.7)))
        criteria.append(
            CriterionResult(
                name="Required institutional vocabulary",
                passed=hits >= need,
                detail=f"{hits}/{len(exam.must_include)} tokens present (need ≥{need})",
            )
        )

    for bad in exam.must_not_include:
        if bad.lower() in text:
            criteria.append(
                CriterionResult(name=f"Forbidden: {bad}", passed=False, detail="found in answer")
            )

    passed_n = sum(1 for c in criteria if c.passed)
    score = passed_n / max(1, len(criteria))
    passed = all(c.passed for c in criteria)

    return ExamResult(
        exam_id=exam.exam_id,
        level=exam.level,
        level_name=LEVELS.get(exam.level, "unknown"),
        question=exam.question,
        passed=passed,
        score=round(score, 3),
        answer=answer,
        structure=structure,
        criteria=criteria,
        provenance=reasoned.get("provenance") or {},
    )


def _has(structure: dict[str, Any], *keys: str) -> bool:
    for k in keys:
        v = structure.get(k)
        if v:
            return True
    return False


def _grade_l1(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    return [
        CriterionResult(
            "Defines the concept correctly",
            bool(structure.get("definition")) and len(str(structure.get("definition"))) > 40,
        ),
        CriterionResult(
            "Explains why it matters",
            bool(structure.get("why_it_matters")) and len(str(structure.get("why_it_matters"))) > 20,
        ),
        CriterionResult(
            "Describes when to apply it",
            bool(structure.get("when_to_apply")),
        ),
        CriterionResult(
            "Describes when not to apply it",
            bool(structure.get("when_not_to_apply")),
        ),
    ]


def _grade_l2(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    sections = structure.get("sections") or []
    applied = len(sections) >= 3
    if (exam.framework or "").lower() == "porter":
        forces = { (s.get("force") or "") for s in sections }
        applied = len(forces & {"rivalry", "buyer_power", "supplier_power", "substitutes", "entrants"}) >= 5
    return [
        CriterionResult("Applies the framework correctly", applied, f"{len(sections)} sections"),
        CriterionResult(
            "Uses company-specific evidence",
            bool(structure.get("company_specific_evidence")) and bool(structure.get("company")),
        ),
        CriterionResult(
            "Produces a conclusion",
            bool(structure.get("conclusion")) and len(str(structure.get("conclusion"))) > 20,
        ),
        CriterionResult(
            "Does not merely define the framework",
            "definition only" not in text and bool(structure.get("company")),
        ),
    ]


def _grade_l3(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    authors = [a.lower() for a in (structure.get("authors_used") or [])]
    wanted = [a.lower() for a in exam.authors]
    multi = sum(1 for a in wanted if a in authors or a in text) >= min(3, max(2, len(wanted)))
    return [
        CriterionResult(
            "Integrates multiple authors naturally",
            multi,
            f"authors_used={authors}",
        ),
        CriterionResult(
            "Does not answer from only one book",
            not structure.get("single_book_only", True) and multi,
        ),
        CriterionResult(
            "Produces a unified institutional view",
            bool(structure.get("unified_institutional_view")),
        ),
    ]


def _grade_l4(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    sims = structure.get("similarities")
    diffs = structure.get("differences") or []
    lessons = structure.get("lessons") or []
    return [
        CriterionResult("Identifies the right analogue", bool(structure.get("analogue"))),
        CriterionResult(
            "Explains similarities and differences",
            bool(sims) and len(diffs) >= 1,
        ),
        CriterionResult("Draws transferable lessons", len([x for x in lessons if x]) >= 1),
    ]


def _grade_l5(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    ex = structure.get("exceptions") or []
    return [
        CriterionResult("Identifies exceptions", len(ex) >= 3, f"{len(ex)} exceptions"),
        CriterionResult(
            "Does not treat concepts as universally true",
            bool(structure.get("not_universal")) or "not universally" in text or "only if" in text or "misleading" in text,
        ),
    ]


def _grade_l6(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    domain = structure.get("domain_guard") or exam.analyst
    points = structure.get("points") or []
    out = [
        CriterionResult(
            f"Stays in {domain} domain",
            (structure.get("analyst") or "") == exam.analyst or domain == exam.analyst,
        ),
        CriterionResult("Uses company evidence / reasoned points", len(points) >= 2 or bool(structure.get("conclusion"))),
        CriterionResult("Reaches a reasoned view", bool(structure.get("conclusion"))),
    ]
    if exam.analyst == "valuation":
        out.append(
            CriterionResult(
                "No cheap/expensive slogan alone",
                not (("cheap" in text or "expensive" in text) and "assumption" not in text and "expectation" not in text),
            )
        )
    return out


def _grade_l7(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    metrics = structure.get("metrics") or {}
    return [
        CriterionResult(
            "References prior review memory",
            bool(structure.get("previous_opinion")) and bool(structure.get("updated_opinion")),
        ),
        CriterionResult(
            "Tracks key operating metrics",
            all(
                metrics.get(k) or structure.get(k)
                for k in ("loan_growth", "deposit_mix", "nim", "capital")
            ),
        ),
        CriterionResult(
            "States previous and updated opinion",
            "previous" in text and "updated" in text,
        ),
    ]


def _grade_l8(exam: ExamItem, structure: dict[str, Any], text: str) -> list[CriterionResult]:
    chain = structure.get("chain") or []
    stages = [c.get("stage", "").lower() for c in chain]
    needed = ["business", "financials", "valuation", "risks", "committee"]
    has_chain = all(any(n in s for s in stages) for n in needed)
    justified = all(c.get("justification") for c in chain) if chain else False
    bare = structure.get("bare_yes_no")
    # Fail if answer is only yes/no
    stripped = text.strip()
    only_yes_no = stripped in {"yes", "no", "yes.", "no."} or (
        len(stripped) < 40 and ("yes" in stripped or "no" in stripped) and "business" not in stripped
    )
    return [
        CriterionResult(
            "Builds Business → Financials → Valuation → Risks → Committee chain",
            has_chain,
            f"stages={stages}",
        ),
        CriterionResult(
            "Does not answer with bare yes/no",
            bare is False and not only_yes_no,
        ),
        CriterionResult("Every major statement is justified", justified and bool(structure.get("conclusion"))),
    ]
