"""Multi-course catalog — additive aggregation without redesigning Academy APIs."""

from __future__ import annotations

from typing import Any

from academy import accounting
from academy import corporate_finance
from academy.accounting import causal_models as acc_causal
from academy.accounting import mental_models as acc_mental
from academy.accounting import teaching as acc_teaching
from academy.accounting.curriculum import CONCEPT_CHAPTER_MAP as ACC_CHAPTER_MAP
from academy.accounting.curriculum import course_manifest as accounting_manifest
from academy.accounting.earnings_quality import score_earnings_quality
from academy.accounting.knowledge_objects import all_knowledge_objects as accounting_objects
from academy.accounting.red_flags import list_red_flags, score_red_flags
from academy.causal_models import all_causal_models as economics_causal
from academy.corporate_finance import causal_models as acf_causal
from academy.corporate_finance import mental_models as acf_mental
from academy.corporate_finance import teaching as acf_teaching
from academy.corporate_finance.curriculum import CONCEPT_CHAPTER_MAP as ACF_CHAPTER_MAP
from academy.corporate_finance.curriculum import course_manifest as acf_manifest
from academy.corporate_finance.knowledge_objects import all_knowledge_objects as acf_objects
from academy.curriculum import CONCEPT_CHAPTER_MAP as ECO_CHAPTER_MAP
from academy.curriculum import course_manifest as economics_manifest
from academy.knowledge_objects import all_knowledge_objects as economics_objects
from academy.mental_models import all_mental_models as economics_mental
from academy.schema import ACADEMY_VERSION, COURSE_ID, KnowledgeObject
from academy.teaching import EXAMS as ECO_EXAMS
from academy.teaching import answer_question as eco_answer
from academy.teaching import run_exam_suite as eco_exams
from academy.teaching import teach as eco_teach

_ACC_ALIASES = {
    accounting.COURSE_ID,
    "accounting",
    "minimalist_accounting",
    "damodaran_accounting",
}
_ACF_ALIASES = {
    corporate_finance.COURSE_ID,
    "acf",
    "corporate_finance",
    "applied_corporate_finance",
    "damodaran_acf",
}
# bare "damodaran" kept for accounting backward-compat (existing tests/API clients)
_ACC_ALIASES.add("damodaran")


def list_courses() -> list[dict[str, Any]]:
    return [economics_manifest(), accounting_manifest(), acf_manifest()]


def course_manifest(course_id: str | None = None) -> dict[str, Any]:
    if not course_id or course_id in (COURSE_ID, "economics", "mankiw"):
        return economics_manifest()
    if course_id in _ACC_ALIASES:
        return accounting_manifest()
    if course_id in _ACF_ALIASES:
        return acf_manifest()
    raise KeyError(f"Unknown course: {course_id}")


def _book_knowledge_objects() -> list[KnowledgeObject]:
    """Soft-include Academy Books concepts as KnowledgeObjects (fill curriculum)."""
    try:
        from academy.books.flags import is_books_enabled
        from academy.books.ingest import ensure_seeded
        from academy.books.store import get_books_store
        from academy.schema import SourceRef
    except Exception:
        return []
    if not is_books_enabled():
        return []
    ensure_seeded()
    out: list[KnowledgeObject] = []
    for c in get_books_store().concepts.values():
        out.append(
            KnowledgeObject(
                concept=c.title,
                concept_id=c.concept_id,
                definition=c.definition,
                purpose=c.explanation or c.definition,
                first_principles=[c.explanation] if c.explanation else [c.definition],
                examples=list(c.examples)[:4],
                confidence=c.confidence,
                sources=[
                    SourceRef(
                        book=c.source_book_id or "academy_books",
                        chapter_title=c.source_chapter,
                    )
                ],
                course_id="academy_books",
                tags=["course:books", f"academy:{c.academy}", "source:books"],
            )
        )
    return out


def all_knowledge_objects(course_id: str | None = None) -> list[KnowledgeObject]:
    eco = economics_objects()
    for k in eco:
        if not k.course_id:
            k.course_id = COURSE_ID
        if "course:economics" not in k.tags:
            k.tags = list(k.tags) + ["course:economics"]
    acc = accounting_objects()
    acf = acf_objects()
    # Books are a parallel structured-learning layer. Soft-included only when
    # explicitly requested so curriculum QC / completion gates stay unchanged.
    # FAPI still merges Academy Books via academy.books.production.package_for_query.
    if course_id in {"academy_books", "books", "book"}:
        return _book_knowledge_objects()
    if course_id in (None, "", "all"):
        return eco + acc + acf
    if course_id in (COURSE_ID, "economics", "mankiw"):
        return eco
    if course_id in _ACC_ALIASES:
        return acc
    if course_id in _ACF_ALIASES:
        return acf
    raise KeyError(f"Unknown course: {course_id}")


def knowledge_by_id() -> dict[str, KnowledgeObject]:
    return {k.concept_id: k for k in all_knowledge_objects()}


def list_concept_ids(course_id: str | None = None) -> list[str]:
    return [k.concept_id for k in all_knowledge_objects(course_id)]


def concept_chapter_map() -> dict[str, int]:
    out = dict(ECO_CHAPTER_MAP)
    out.update(ACC_CHAPTER_MAP)
    out.update(ACF_CHAPTER_MAP)
    return out


def all_causal_models():
    return economics_causal() + acc_causal.all_causal_models() + acf_causal.all_causal_models()


def all_mental_models():
    return economics_mental() + acc_mental.all_mental_models() + acf_mental.all_mental_models()


def all_exams() -> list[dict[str, Any]]:
    eco = [{**e, "course": COURSE_ID} for e in ECO_EXAMS]
    acc = [{**e, "course": accounting.COURSE_ID} for e in acc_teaching.EXAMS]
    acf = [{**e, "course": corporate_finance.COURSE_ID} for e in acf_teaching.EXAMS]
    return eco + acc + acf


def answer_question(question_id: str) -> dict[str, Any]:
    try:
        return eco_answer(question_id)
    except KeyError:
        try:
            return acc_teaching.answer_question(question_id)
        except KeyError:
            return acf_teaching.answer_question(question_id)


def run_exam_suite(course_id: str | None = None) -> dict[str, Any]:
    if course_id in _ACC_ALIASES:
        return acc_teaching.run_exam_suite()
    if course_id in _ACF_ALIASES:
        return acf_teaching.run_exam_suite()
    if course_id in (COURSE_ID, "economics", "mankiw"):
        return eco_exams()
    eco = eco_exams()
    acc = acc_teaching.run_exam_suite()
    acf = acf_teaching.run_exam_suite()
    return {
        "total": eco["total"] + acc["total"] + acf["total"],
        "passed": eco["passed"] + acc["passed"] + acf["passed"],
        "failed": eco["failed"] + acc["failed"] + acf["failed"],
        "complete": eco["complete"] and acc["complete"] and acf["complete"],
        "by_course": {
            COURSE_ID: eco,
            accounting.COURSE_ID: acc,
            corporate_finance.COURSE_ID: acf,
        },
    }


def teach(concept_id: str) -> dict[str, Any]:
    kb = knowledge_by_id()
    if concept_id not in kb:
        raise KeyError(concept_id)
    cid = kb[concept_id].course_id
    tags = kb[concept_id].tags
    if cid == accounting.COURSE_ID or "course:accounting" in tags:
        return acc_teaching.teach(concept_id)
    if cid == corporate_finance.COURSE_ID or "course:corporate_finance" in tags:
        return acf_teaching.teach(concept_id)
    return eco_teach(concept_id)


def accounting_toolkit() -> dict[str, Any]:
    return {
        "course": accounting_manifest(),
        "red_flags": list_red_flags(),
        "earnings_quality_methodology": score_earnings_quality({}),
        "version": ACADEMY_VERSION,
    }


def corporate_finance_toolkit() -> dict[str, Any]:
    return {
        "course": acf_manifest(),
        "foundations": ["investment_principle", "financing_principle", "dividend_principle"],
        "core_spread": "roic_wacc_spread",
        "decision_questions": [
            "Is management allocating capital efficiently?",
            "Is ROIC above WACC?",
            "Is leverage appropriate?",
            "Is the buyback value accretive?",
            "Is the acquisition likely to create value?",
            "Should excess cash be returned or reinvested?",
        ],
        "version": ACADEMY_VERSION,
    }
