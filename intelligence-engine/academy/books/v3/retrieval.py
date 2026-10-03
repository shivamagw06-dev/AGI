"""Institutional knowledge retrieval — never chapters, paragraphs, or PDFs."""

from __future__ import annotations

import re
from typing import Any

from academy.books.v3.store import ensure_v3_seeded, get_v3_store

# Tokens that indicate the user wants institutional knowledge shapes
_KNOWLEDGE_SHAPES = (
    "framework",
    "case",
    "decision",
    "reasoning",
    "lesson",
    "example",
    "counter",
    "checklist",
    "mental",
    "pattern",
    "formula",
    "rule",
    "roic",
    "moat",
    "valuation",
    "margin",
    "safety",
)


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(t) > 2}


def _score_blob(blob: str, tokens: set[str]) -> float:
    b = blob.lower()
    score = 0.0
    for t in tokens:
        if t in b:
            score += 1.0
    return score


def _to_dicts(items: list[Any], limit: int = 8) -> list[dict[str, Any]]:
    out = []
    for item in items[:limit]:
        if hasattr(item, "to_dict"):
            out.append(item.to_dict())
        elif isinstance(item, dict):
            out.append(item)
    return out


def institutional_ask(
    question: str,
    *,
    analyst: str | None = None,
    ticker: str | None = None,
    limit: int = 8,
) -> dict[str, Any]:
    """Ask the Academy for knowledge — frameworks, cases, rules, chains, lessons.

    Never returns raw PDF text, chapter dumps, or paragraph retrieval.
    Cross-book topics resolve to unified InstitutionalKnowledgeObjects when present.
    """
    ensure_v3_seeded()
    store = get_v3_store()
    q = question or ""
    tokens = _tokens(q)
    analyst_key = (analyst or "").lower().strip() or None

    # Prefer unified institutional objects for core topics
    ikos = []
    for obj in store.institutional_objects.values():
        blob = f"{obj.topic} {obj.unified_definition} {obj.synthesis} {' '.join(obj.source_authors)}"
        score = _score_blob(blob, tokens) + (2.0 if obj.topic.lower() in q.lower() else 0.0)
        if analyst_key and analyst_key in obj.analysts:
            score += 1.5
        if score > 0:
            ikos.append((score, obj))
    ikos.sort(key=lambda x: -x[0])

    concepts = []
    for c in store.concepts.values():
        blob = f"{c.name} {c.definition} {c.purpose} {' '.join(c.source_authors)} {' '.join(c.related_concepts)}"
        score = _score_blob(blob, tokens)
        if analyst_key and analyst_key in c.analysts_using:
            score += 1.2
        if score > 0:
            concepts.append((score + c.confidence, c))
    concepts.sort(key=lambda x: -x[0])

    frameworks = []
    for fw in store.frameworks.values():
        blob = f"{fw.name} {fw.purpose} {fw.objective} {' '.join(fw.inputs)} {' '.join(fw.related_concepts)}"
        score = _score_blob(blob, tokens)
        if analyst_key and analyst_key in fw.analysts_using:
            score += 1.0
        if score > 0:
            frameworks.append((score, fw))
    frameworks.sort(key=lambda x: -x[0])

    formulas = []
    for f in store.formulas.values():
        blob = f"{f.name} {f.expression} {f.purpose} {' '.join(f.related_concepts)}"
        score = _score_blob(blob, tokens)
        if score > 0:
            formulas.append((score, f))
    formulas.sort(key=lambda x: -x[0])

    cases = []
    for c in store.cases.values():
        blob = f"{c.company} {c.industry} {c.situation} {' '.join(c.lessons)} {' '.join(c.related_concepts)}"
        score = _score_blob(blob, tokens)
        if ticker and ticker.upper() in (c.company or "").upper():
            score += 3.0
        if score > 0:
            cases.append((score, c))
    cases.sort(key=lambda x: -x[0])

    rules = []
    for r in store.decision_rules.values():
        blob = f"{r.name} {' '.join(r.if_conditions)} {r.then_action} {' '.join(r.related_concepts)}"
        score = _score_blob(blob, tokens)
        if analyst_key and analyst_key in r.analysts_using:
            score += 1.0
        if score > 0:
            rules.append((score, r))
    rules.sort(key=lambda x: -x[0])

    chains = []
    for ch in store.reasoning_chains.values():
        blob = f"{ch.name} {ch.purpose} {' '.join(ch.steps)} {' '.join(ch.related_concepts)}"
        score = _score_blob(blob, tokens)
        if score > 0:
            chains.append((score, ch))
    chains.sort(key=lambda x: -x[0])

    trees = []
    for t in store.decision_trees.values():
        blob = f"{t.name} {t.purpose} {t.root} {' '.join(t.related_concepts)}"
        score = _score_blob(blob, tokens)
        if score > 0:
            trees.append((score, t))
    trees.sort(key=lambda x: -x[0])

    mental = []
    for m in store.mental_models.values():
        blob = f"{m.name} {m.definition} {m.purpose} {' '.join(m.related_concepts)}"
        score = _score_blob(blob, tokens)
        if score > 0:
            mental.append((score, m))
    mental.sort(key=lambda x: -x[0])

    patterns = []
    for p in store.patterns.values():
        blob = f"{p.name} {p.definition} {' '.join(p.recognition_signals)} {' '.join(p.related_concepts)}"
        score = _score_blob(blob, tokens)
        if score > 0:
            patterns.append((score, p))
    patterns.sort(key=lambda x: -x[0])

    checklists = []
    for c in store.checklists.values():
        blob = f"{c.name} {c.domain} {' '.join(c.items)}"
        score = _score_blob(blob, tokens)
        if analyst_key and analyst_key in c.analysts_using:
            score += 2.0
        if score > 0:
            checklists.append((score, c))
    checklists.sort(key=lambda x: -x[0])

    authors = []
    for a in store.author_perspectives.values():
        blob = f"{a.topic} {a.unified_institutional_view} {' '.join(a.agreements)}"
        score = _score_blob(blob, tokens) + (
            3.0 if any(p.get("author", "").lower() in q.lower() for p in a.perspectives) else 0.0
        )
        if score > 0:
            authors.append((score, a))
    authors.sort(key=lambda x: -x[0])

    failures = []
    for f in store.failures.values():
        blob = f"{f.name} {' '.join(f.lessons)} {' '.join(f.warning_signals)} {' '.join(f.domains)}"
        score = _score_blob(blob, tokens)
        if score > 0:
            failures.append((score, f))
    failures.sort(key=lambda x: -x[0])

    # Soft analyst base overlay
    analyst_pack = None
    if analyst_key and analyst_key in store.analyst_bases:
        base = store.analyst_bases[analyst_key]
        analyst_pack = {
            "analyst": analyst_key,
            "receives": base.get("receives") or [],
            "preferred_frameworks": [
                store.frameworks[i].to_dict()
                for i in base.get("framework_ids") or []
                if i in store.frameworks
            ][:limit],
            "preferred_concepts": [
                store.concepts[i].to_dict()
                for i in base.get("concept_ids") or []
                if i in store.concepts
            ][:limit],
            "preferred_patterns": [
                store.patterns[i].to_dict()
                for i in base.get("pattern_ids") or []
                if i in store.patterns
            ][:limit],
            "preferred_checklists": [
                store.checklists[i].to_dict()
                for i in base.get("checklist_ids") or []
                if i in store.checklists
            ],
        }

    lessons: list[str] = []
    for _, obj in ikos[:3]:
        lessons.extend(obj.lessons)
    for _, c in cases[:3]:
        lessons.extend(c.lessons)
    for _, f in failures[:2]:
        lessons.extend(f.lessons)
    # de-dupe preserve order
    seen: set[str] = set()
    uniq_lessons = []
    for L in lessons:
        if L not in seen:
            seen.add(L)
            uniq_lessons.append(L)

    examples: list[str] = []
    counter_examples: list[str] = []
    for _, c in concepts[:3]:
        examples.extend(c.examples)
        counter_examples.extend(c.counter_examples)
    for _, obj in ikos[:2]:
        counter_examples.extend(obj.counter_examples)

    primary = None
    if ikos:
        primary = {
            "type": "institutional_knowledge_object",
            "object": ikos[0][1].to_dict(),
            "note": "Cross-book synthesis — one institutional object, not separate book paragraphs.",
        }
    elif concepts:
        primary = {
            "type": "concept_card",
            "object": concepts[0][1].to_dict(),
            "note": "Concept card with multi-author lineage.",
        }

    return {
        "enabled": True,
        "mode": "institutional_knowledge",
        "books_v3_version": store.version,
        "question": question,
        "analyst": analyst_key,
        "ticker": ticker,
        "retrieval_policy": {
            "retrieve": [
                "knowledge",
                "reasoning",
                "frameworks",
                "lessons",
                "cases",
                "decision_rules",
            ],
            "never_retrieve": ["chapters", "paragraphs", "pdfs", "verbatim_book_text"],
        },
        "primary": primary,
        "institutional_objects": _to_dicts([o for _, o in ikos], limit=3),
        "concepts": _to_dicts([c for _, c in concepts], limit=limit),
        "frameworks": _to_dicts([f for _, f in frameworks], limit=limit),
        "formulas": _to_dicts([f for _, f in formulas], limit=5),
        "cases": _to_dicts([c for _, c in cases], limit=limit),
        "decision_rules": _to_dicts([r for _, r in rules], limit=limit),
        "reasoning_chains": _to_dicts([c for _, c in chains], limit=5),
        "decision_trees": _to_dicts([t for _, t in trees], limit=5),
        "mental_models": _to_dicts([m for _, m in mental], limit=limit),
        "patterns": _to_dicts([p for _, p in patterns], limit=limit),
        "checklists": _to_dicts([c for _, c in checklists], limit=5),
        "author_comparison": _to_dicts([a for _, a in authors], limit=3),
        "failure_patterns": _to_dicts([f for _, f in failures], limit=5),
        "lessons": uniq_lessons[:12],
        "examples": examples[:8],
        "counter_examples": counter_examples[:8],
        "analyst_knowledge_base": analyst_pack,
        "provenance": {
            "source": "academy_books_v3",
            "verbatim_quotes": False,
            "pdf_returned": False,
            "chapter_text_returned": False,
            "cross_book_synthesis": bool(ikos),
        },
    }


def knowledge_for_analyst(analyst: str, *, question: str = "", limit: int = 8) -> dict[str, Any]:
    """Convenience: analyst-scoped institutional ask."""
    return institutional_ask(question or f"{analyst} institutional knowledge", analyst=analyst, limit=limit)
