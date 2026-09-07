"""Persist Academy Books learned knowledge (AGI-owned objects only).

Never stores raw PDF text or searchable book corpora.
Snapshot reloads on bootstrap so intelligence keeps what it learned.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from academy.books.schema import (
    BookConcept,
    BookMeta,
    ChapterNode,
    FormulaObject,
    FrameworkObject,
    GraphEdge,
)
from academy.books.store import BooksStore, get_books_store

LEARNED_DIR = Path(__file__).resolve().parent / "learned"
SNAPSHOT_PATH = LEARNED_DIR / "library_snapshot.json"


def snapshot_path() -> Path:
    return SNAPSHOT_PATH


def export_learned(store: BooksStore | None = None) -> dict[str, Any]:
    store = store or get_books_store()
    # Persist only non-seed books + objects sourced from them (plus graph edges).
    learned_book_ids = {
        b.book_id
        for b in store.books.values()
        if (b.source_format or "") != "seed" and not str(b.book_id).startswith("seed_")
    }
    books = [b.to_dict() for b in store.books.values() if b.book_id in learned_book_ids]
    chapters = [
        ch.to_dict()
        for ch in store.chapters.values()
        if ch.book_id in learned_book_ids
    ]
    concepts = [
        c.to_dict()
        for c in store.concepts.values()
        if c.source_book_id in learned_book_ids or (c.source_book_id or "").startswith("book_")
    ]
    formulas = [
        f.to_dict()
        for f in store.formulas.values()
        if f.source_book_id in learned_book_ids or (f.source_book_id or "").startswith("book_")
    ]
    frameworks = [
        f.to_dict()
        for f in store.frameworks.values()
        if f.source_book_id in learned_book_ids or (f.source_book_id or "").startswith("book_")
    ]
    learned_ids = {c["concept_id"] for c in concepts} | {f["formula_id"] for f in formulas} | {
        f["framework_id"] for f in frameworks
    }
    edges = [
        e.to_dict()
        for e in store.edges.values()
        if e.source in learned_ids or e.target in learned_ids
    ]
    return {
        "version": 1,
        "policy": "agi_owned_objects_only",
        "verbatim_storage": False,
        "searchable_pdf_index": False,
        "books": books,
        "chapters": chapters,
        "concepts": concepts,
        "formulas": formulas,
        "frameworks": frameworks,
        "edges": edges,
        "counts": {
            "books": len(books),
            "chapters": len(chapters),
            "concepts": len(concepts),
            "formulas": len(formulas),
            "frameworks": len(frameworks),
            "edges": len(edges),
        },
    }


def save_learned(store: BooksStore | None = None, path: Path | None = None) -> dict[str, Any]:
    store = store or get_books_store()
    target = path or SNAPSHOT_PATH
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = export_learned(store)
    target.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "path": str(target), **payload["counts"]}


def load_learned(store: BooksStore | None = None, path: Path | None = None) -> dict[str, Any]:
    store = store or get_books_store()
    target = path or SNAPSHOT_PATH
    if not target.exists():
        return {"ok": False, "reason": "no_snapshot", "loaded": 0}
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"ok": False, "reason": f"read_failed:{exc}", "loaded": 0}

    loaded = 0
    for row in payload.get("books") or []:
        try:
            store.upsert_book(BookMeta(**{k: v for k, v in row.items() if k in BookMeta.__dataclass_fields__}))
            loaded += 1
        except Exception:
            continue
    for row in payload.get("chapters") or []:
        try:
            store.upsert_chapter(
                ChapterNode(**{k: v for k, v in row.items() if k in ChapterNode.__dataclass_fields__})
            )
            loaded += 1
        except Exception:
            continue
    for row in payload.get("concepts") or []:
        try:
            store.upsert_concept(
                BookConcept(**{k: v for k, v in row.items() if k in BookConcept.__dataclass_fields__})
            )
            loaded += 1
        except Exception:
            continue
    for row in payload.get("formulas") or []:
        try:
            store.upsert_formula(
                FormulaObject(**{k: v for k, v in row.items() if k in FormulaObject.__dataclass_fields__})
            )
            loaded += 1
        except Exception:
            continue
    for row in payload.get("frameworks") or []:
        try:
            store.upsert_framework(
                FrameworkObject(**{k: v for k, v in row.items() if k in FrameworkObject.__dataclass_fields__})
            )
            loaded += 1
        except Exception:
            continue
    for row in payload.get("edges") or []:
        try:
            store.upsert_edge(GraphEdge(**{k: v for k, v in row.items() if k in GraphEdge.__dataclass_fields__}))
            loaded += 1
        except Exception:
            continue
    return {
        "ok": True,
        "path": str(target),
        "loaded": loaded,
        "counts": payload.get("counts") or {},
    }
