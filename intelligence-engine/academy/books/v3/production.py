"""Academy Books V3 production facade — soft layer on V2, no engine redesign."""

from __future__ import annotations

from typing import Any

from academy.books.v3.graph_v3 import graph_preview
from academy.books.v3.retrieval import institutional_ask, knowledge_for_analyst
from academy.books.v3.schema import BOOKS_V3_VERSION
from academy.books.v3.store import ensure_v3_seeded, get_v3_store, reset_v3_store


def is_v3_enabled() -> bool:
    try:
        from academy.books.flags import flag_books_v3

        return flag_books_v3()
    except Exception:
        return True


def bootstrap() -> dict[str, Any]:
    return ensure_v3_seeded()


def dashboard() -> dict[str, Any]:
    snap = ensure_v3_seeded()
    store = get_v3_store()
    return {
        "programme": "AGI_ACADEMY_BOOKS_V3",
        "books_v3_version": BOOKS_V3_VERSION,
        "architecture_status": "v1.0.1 LOCKED",
        "enabled": is_v3_enabled(),
        "mode": "institutional_knowledge_transformation",
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
        "snapshot": snap,
        "knowledge_graph": graph_preview(store),
        "analyst_bases": sorted(store.analyst_bases.keys()),
        "sectors": [s.name for s in store.sectors.values()],
        "institutional_topics": [o.topic for o in store.institutional_objects.values()],
        "copyright": {
            "verbatim_storage": False,
            "searchable_pdf_index": False,
            "policy": "institutional_objects_only",
            "retrieve": ["knowledge", "reasoning", "frameworks", "lessons", "cases", "decision_rules"],
            "never_retrieve": ["chapters", "paragraphs", "pdfs"],
        },
    }


def package_for_query(
    query: str,
    *,
    ticker: str | None = None,
    analyst: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Soft institutional package for Ask AGI / analysts — never PDF/chapter dumps."""
    if not is_v3_enabled():
        return {"enabled": False, "books_v3_version": BOOKS_V3_VERSION}
    result = institutional_ask(query, analyst=analyst, ticker=ticker, limit=limit)
    # Compact soft-wire slice for existing consumers
    return {
        "enabled": True,
        "books_v3_version": BOOKS_V3_VERSION,
        "mode": "institutional_knowledge",
        "primary": result.get("primary"),
        "institutional_objects": result.get("institutional_objects") or [],
        "concepts": result.get("concepts") or [],
        "frameworks": result.get("frameworks") or [],
        "formulas": result.get("formulas") or [],
        "cases": result.get("cases") or [],
        "decision_rules": result.get("decision_rules") or [],
        "reasoning_chains": result.get("reasoning_chains") or [],
        "decision_trees": result.get("decision_trees") or [],
        "mental_models": result.get("mental_models") or [],
        "patterns": result.get("patterns") or [],
        "checklists": result.get("checklists") or [],
        "author_comparison": result.get("author_comparison") or [],
        "failure_patterns": result.get("failure_patterns") or [],
        "lessons": result.get("lessons") or [],
        "examples": result.get("examples") or [],
        "counter_examples": result.get("counter_examples") or [],
        "analyst_knowledge_base": result.get("analyst_knowledge_base"),
        "answer_hints": _hints_from_result(result),
        "provenance": result.get("provenance") or {},
        "retrieval_policy": result.get("retrieval_policy") or {},
    }


def _hints_from_result(result: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    primary = result.get("primary") or {}
    obj = primary.get("object") if isinstance(primary, dict) else None
    if isinstance(obj, dict):
        if obj.get("unified_definition"):
            hints.append(obj["unified_definition"])
        elif obj.get("synthesis"):
            hints.append(str(obj["synthesis"])[:400])
        elif obj.get("definition"):
            hints.append(obj["definition"])
    for lesson in (result.get("lessons") or [])[:3]:
        hints.append(lesson)
    for rule in (result.get("decision_rules") or [])[:2]:
        if isinstance(rule, dict) and rule.get("then_action"):
            cond = " AND ".join(rule.get("if_conditions") or [])
            hints.append(f"If {cond} → {rule['then_action']}")
    return hints[:6]


def analyst_base(analyst: str, *, question: str = "") -> dict[str, Any]:
    if not is_v3_enabled():
        return {"enabled": False}
    return knowledge_for_analyst(analyst, question=question)


def quality_gates() -> dict[str, Any]:
    snap = ensure_v3_seeded()
    store = get_v3_store()
    # ROIC synthesis success criterion
    roic_ask = institutional_ask("How should I interpret high ROIC?", analyst="valuation")
    primary = roic_ask.get("primary") or {}
    primary_obj = primary.get("object") if isinstance(primary, dict) else {}
    authors = set()
    if isinstance(primary_obj, dict):
        authors = set(primary_obj.get("source_authors") or [])
    for a in roic_ask.get("author_comparison") or []:
        for p in a.get("perspectives") or []:
            if p.get("author"):
                authors.add(p["author"])

    checks = {
        "v3_seeded": bool(snap.get("seeded")),
        "concepts_present": snap.get("concepts", 0) >= 6,
        "frameworks_present": snap.get("frameworks", 0) >= 8,
        "formulas_present": snap.get("formulas", 0) >= 4,
        "cases_present": snap.get("cases", 0) >= 3,
        "mental_models_present": snap.get("mental_models", 0) >= 10,
        "decision_trees_present": snap.get("decision_trees", 0) >= 2,
        "checklists_present": snap.get("checklists", 0) >= 6,
        "patterns_present": snap.get("patterns", 0) >= 8,
        "sectors_present": snap.get("sectors", 0) >= 10,
        "institutional_objects_present": snap.get("institutional_objects", 0) >= 2,
        "graph_built": snap.get("edges", 0) >= 20,
        "analyst_bases_present": snap.get("analyst_bases", 0) >= 6,
        "roic_returns_synthesis_not_paragraph": (
            (primary.get("type") == "institutional_knowledge_object")
            if isinstance(primary, dict)
            else False
        ),
        "roic_multi_author": len(authors) >= 3,
        "no_pdf_in_payload": "pdf" not in str(roic_ask.get("provenance")).lower()
        or roic_ask.get("provenance", {}).get("pdf_returned") is False,
        "never_chapter_text": roic_ask.get("provenance", {}).get("chapter_text_returned") is False,
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "books_v3_version": BOOKS_V3_VERSION,
        "roic_authors_seen": sorted(authors),
    }


def soft_slice_for_package(query: str, *, ticker: str | None = None) -> dict[str, Any]:
    """Minimal enrichment block for V2 package_for_query soft-wire."""
    if not is_v3_enabled():
        return {}
    pkg = package_for_query(query, ticker=ticker, limit=6)
    return {
        "books_v3": {
            "enabled": True,
            "version": BOOKS_V3_VERSION,
            "mode": "institutional_knowledge",
            "primary": pkg.get("primary"),
            "institutional_objects": pkg.get("institutional_objects") or [],
            "frameworks": [f.get("name") for f in (pkg.get("frameworks") or [])],
            "decision_rules": [
                {"name": r.get("name"), "then": r.get("then_action")}
                for r in (pkg.get("decision_rules") or [])
            ],
            "reasoning_chains": [c.get("name") for c in (pkg.get("reasoning_chains") or [])],
            "patterns": [p.get("name") for p in (pkg.get("patterns") or [])],
            "lessons": pkg.get("lessons") or [],
            "author_comparison": pkg.get("author_comparison") or [],
            "mental_models": [m.get("name") for m in (pkg.get("mental_models") or [])],
            "checklists": [c.get("name") for c in (pkg.get("checklists") or [])],
            "cases": [
                {"company": c.get("company"), "lessons": c.get("lessons")}
                for c in (pkg.get("cases") or [])
            ],
            "answer_hints": pkg.get("answer_hints") or [],
            "provenance": pkg.get("provenance") or {},
        }
    }


def reset_for_tests() -> None:
    reset_v3_store()
