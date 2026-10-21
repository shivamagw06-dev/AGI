"""In-memory Academy Books V3 institutional knowledge store."""

from __future__ import annotations

from threading import Lock
from typing import Any

from academy.books.v3.schema import BOOKS_V3_VERSION
from academy.books.v3.seed_analyst_bases import seed_analyst_bases
from academy.books.v3.seed_core import (
    seed_checklists,
    seed_decision_rules,
    seed_decision_trees,
    seed_mental_models,
    seed_patterns,
    seed_reasoning_chains,
)
from academy.books.v3.seed_synthesis import (
    seed_author_perspectives,
    seed_cases,
    seed_chapter_knowledge,
    seed_concepts,
    seed_failures,
    seed_formulas,
    seed_frameworks,
    seed_institutional_objects,
    seed_sectors,
)


class BooksV3Store:
    def __init__(self) -> None:
        self.version = BOOKS_V3_VERSION
        self.concepts: dict[str, Any] = {}
        self.frameworks: dict[str, Any] = {}
        self.formulas: dict[str, Any] = {}
        self.cases: dict[str, Any] = {}
        self.failures: dict[str, Any] = {}
        self.mental_models: dict[str, Any] = {}
        self.decision_trees: dict[str, Any] = {}
        self.reasoning_chains: dict[str, Any] = {}
        self.checklists: dict[str, Any] = {}
        self.decision_rules: dict[str, Any] = {}
        self.patterns: dict[str, Any] = {}
        self.author_perspectives: dict[str, Any] = {}
        self.sectors: dict[str, Any] = {}
        self.chapters: dict[str, Any] = {}
        self.institutional_objects: dict[str, Any] = {}
        self.analyst_bases: dict[str, Any] = {}
        self.edges: dict[str, Any] = {}
        self._seeded = False

    def seed(self) -> dict[str, Any]:
        if self._seeded:
            return self.snapshot()

        for c in seed_concepts():
            self.concepts[c.concept_id] = c
        for f in seed_frameworks():
            self.frameworks[f.framework_id] = f
        for f in seed_formulas():
            self.formulas[f.formula_id] = f
        for c in seed_cases():
            self.cases[c.case_id] = c
        for f in seed_failures():
            self.failures[f.failure_id] = f
        for m in seed_mental_models():
            self.mental_models[m.model_id] = m
        for t in seed_decision_trees():
            self.decision_trees[t.tree_id] = t
        for r in seed_reasoning_chains():
            self.reasoning_chains[r.chain_id] = r
        for c in seed_checklists():
            self.checklists[c.checklist_id] = c
        for r in seed_decision_rules():
            self.decision_rules[r.rule_id] = r
        for p in seed_patterns():
            self.patterns[p.pattern_id] = p
        for a in seed_author_perspectives():
            self.author_perspectives[a.topic_id] = a
        for s in seed_sectors():
            self.sectors[s.sector_id] = s
        for ch in seed_chapter_knowledge():
            self.chapters[ch.chapter_id] = ch
        for obj in seed_institutional_objects():
            self.institutional_objects[obj.object_id] = obj
        self.analyst_bases = seed_analyst_bases()

        from academy.books.v3.graph_v3 import build_graph

        self.edges = {e.edge_id: e for e in build_graph(self)}
        self._seeded = True
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return {
            "seeded": self._seeded,
            "version": self.version,
            "concepts": len(self.concepts),
            "frameworks": len(self.frameworks),
            "formulas": len(self.formulas),
            "cases": len(self.cases),
            "failures": len(self.failures),
            "mental_models": len(self.mental_models),
            "decision_trees": len(self.decision_trees),
            "reasoning_chains": len(self.reasoning_chains),
            "checklists": len(self.checklists),
            "decision_rules": len(self.decision_rules),
            "patterns": len(self.patterns),
            "author_perspectives": len(self.author_perspectives),
            "sectors": len(self.sectors),
            "chapters": len(self.chapters),
            "institutional_objects": len(self.institutional_objects),
            "analyst_bases": len(self.analyst_bases),
            "edges": len(self.edges),
        }

    def reset(self) -> None:
        self.__init__()  # type: ignore[misc]


_LOCK = Lock()
_STORE: BooksV3Store | None = None


def get_v3_store() -> BooksV3Store:
    global _STORE
    with _LOCK:
        if _STORE is None:
            _STORE = BooksV3Store()
        return _STORE


def reset_v3_store() -> None:
    global _STORE
    with _LOCK:
        if _STORE is not None:
            _STORE.reset()
        _STORE = BooksV3Store()


def ensure_v3_seeded() -> dict[str, Any]:
    store = get_v3_store()
    return store.seed()
