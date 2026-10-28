"""Financial Concepts — production facade.

Soft-wire only: a standalone deterministic knowledge engine. Ask
integration happens exclusively through app/ui/financial_router.py
(Module 11) and app/ui/coverage_policy.py (Module 12) calling into this
facade — this package makes no changes to retrieval or entity resolution
itself.
"""

from __future__ import annotations

from typing import Any, Optional

from financial_concepts.concepts import (
    ALL_CONCEPTS,
    all_concept_keys,
    concept_count,
    concept_count_by_module,
    concepts_by_module,
    get_concept,
    validate_related_concepts,
)
from financial_concepts.exam import CONCEPT_EXAM, grade_answer, list_exam_questions, run_item
from financial_concepts.lookup import explain as _explain
from financial_concepts.lookup import search as _search
from financial_concepts.relationships import graph_summary, isolated_concepts, neighbors, shortest_path
from financial_concepts.schema import FC_VERSION, FREEZE_LOCKS, MODULES, PROGRAMME


def health() -> dict[str, Any]:
    dangling = validate_related_concepts()
    return {
        "status": "ok" if not dangling else "degraded",
        "programme": PROGRAMME,
        "fc_version": FC_VERSION,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/financial-concepts",
        "modules": list(MODULES),
        "concept_count": concept_count(),
        "concept_count_by_module": concept_count_by_module(),
        "exam_question_count": len(CONCEPT_EXAM),
        "graph": graph_summary(),
        "dangling_relationship_refs": dangling,
        "fabricated": False,
    }


def dashboard() -> dict[str, Any]:
    return {
        "fc_version": FC_VERSION,
        "concept_count": concept_count(),
        "concept_count_by_module": concept_count_by_module(),
        "exam_question_count": len(CONCEPT_EXAM),
        "graph": graph_summary(),
        "fabricated": False,
    }


def list_concepts(module: Optional[str] = None) -> dict[str, Any]:
    concepts = concepts_by_module(module) if module else ALL_CONCEPTS
    return {
        "n": len(concepts),
        "module": module,
        "concepts": sorted(concepts.keys()),
        "fabricated": False,
    }


def explain(topic: str) -> dict[str, Any]:
    return _explain(topic)


def search(query: str, limit: int = 5) -> dict[str, Any]:
    results = _search(query, limit=limit)
    return {"query": query, "n": len(results), "results": results, "fabricated": False}


def concept_card(key: str) -> dict[str, Any]:
    card = get_concept(key)
    if not card:
        return {"found": False, "key": key}
    return {"found": True, **card.to_dict()}


def related(key: str) -> dict[str, Any]:
    if key not in ALL_CONCEPTS:
        return {"found": False, "key": key}
    return {"found": True, "key": key, "related": neighbors(key)}


def path(start: str, end: str) -> dict[str, Any]:
    result = shortest_path(start, end)
    return {"start": start, "end": end, "path": result, "found": result is not None}


def graph() -> dict[str, Any]:
    return {**graph_summary(), "isolated_concepts": isolated_concepts(), "fabricated": False}


def exam_questions(section: Optional[str] = None) -> dict[str, Any]:
    return list_exam_questions(section)


def exam_run_item(item_id: str) -> dict[str, Any]:
    return run_item(item_id)


def exam_grade(item_id: str, candidate_answer: str) -> dict[str, Any]:
    return grade_answer(item_id, candidate_answer)


def soft_slice_for_ask_agi(question: str, *_args: Any, **_kwargs: Any) -> dict[str, Any]:
    """Non-invasive Ask soft-wire, matching the financial_foundations /
    financial_statement_intelligence pattern — surfaces a concept
    explanation when the question matches Phase 2.6 vocabulary."""

    result = _explain(question)
    if not result.get("found"):
        return {"enabled": False}
    return {"enabled": True, "financial_concepts": result}
