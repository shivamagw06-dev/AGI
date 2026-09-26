"""Process-local Academy Books store (soft; no KIP redesign)."""

from __future__ import annotations

from threading import RLock
from typing import Any

from academy.books.schema import (
    BookConcept,
    BookMeta,
    ChapterNode,
    FormulaObject,
    FrameworkObject,
    GraphEdge,
)


class BooksStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self.books: dict[str, BookMeta] = {}
        self.chapters: dict[str, ChapterNode] = {}
        self.concepts: dict[str, BookConcept] = {}
        self.formulas: dict[str, FormulaObject] = {}
        self.frameworks: dict[str, FrameworkObject] = {}
        self.edges: dict[str, GraphEdge] = {}
        self.versions: dict[str, list[dict[str, Any]]] = {}
        self.usage: dict[str, int] = {}
        self.spreadsheet_ids: set[str] = set()
        self.ingestion_reports: list[dict[str, Any]] = []

    def reset(self) -> None:
        with self._lock:
            self.__init__()

    def upsert_book(self, book: BookMeta) -> BookMeta:
        with self._lock:
            prev = self.books.get(book.book_id)
            if prev:
                book.version = int(prev.version or 1) + 1
            self.books[book.book_id] = book
            self.versions.setdefault(book.book_id, []).append(
                {"version": book.version, "title": book.title, "status": book.status}
            )
            self.versions[book.book_id] = self.versions[book.book_id][-20:]
            return book

    def upsert_chapter(self, node: ChapterNode) -> None:
        with self._lock:
            self.chapters[node.node_id] = node

    def upsert_concept(self, obj: BookConcept) -> None:
        with self._lock:
            self.concepts[obj.concept_id] = obj

    def upsert_formula(self, obj: FormulaObject) -> None:
        with self._lock:
            self.formulas[obj.formula_id] = obj

    def upsert_framework(self, obj: FrameworkObject) -> None:
        with self._lock:
            self.frameworks[obj.framework_id] = obj

    def upsert_edge(self, edge: GraphEdge) -> None:
        with self._lock:
            self.edges[edge.edge_id] = edge

    def touch(self, concept_id: str) -> None:
        with self._lock:
            self.usage[concept_id] = int(self.usage.get(concept_id) or 0) + 1

    def record_spreadsheet(self, book_id: str) -> None:
        with self._lock:
            self.spreadsheet_ids.add(book_id)

    def add_ingestion_report(self, report: dict[str, Any]) -> None:
        with self._lock:
            self.ingestion_reports.append(report)
            self.ingestion_reports = self.ingestion_reports[-50:]

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "books": len(self.books),
                "chapters": len(self.chapters),
                "concepts": len(self.concepts),
                "formulas": len(self.formulas),
                "frameworks": len(self.frameworks),
                "edges": len(self.edges),
                "spreadsheets": len(self.spreadsheet_ids),
                "most_used": sorted(self.usage.items(), key=lambda x: -x[1])[:12],
            }


_STORE: BooksStore | None = None


def get_books_store() -> BooksStore:
    global _STORE
    if _STORE is None:
        _STORE = BooksStore()
    return _STORE


def reset_books_store() -> None:
    global _STORE
    _STORE = BooksStore()
    try:
        from academy.books.ingest import reset_learned_load_flag

        reset_learned_load_flag()
    except Exception:
        pass
