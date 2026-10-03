"""Book ingestion pipeline: extract → chapters → concepts/frameworks/formulas → graph."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from academy.books.chapters import detect_hierarchy, hierarchy_stats
from academy.books.extract import extract_from_text
from academy.books.graph import rebuild_graph
from academy.books.schema import BOOKS_VERSION, BookMeta
from academy.books.seed import (
    all_seed_concepts,
    seed_books,
    seed_chapters,
    seed_formulas,
    seed_frameworks,
)
from academy.books.store import BooksStore, get_books_store
from academy.books.text_extract import extract_text

# Load the durable learned snapshot at most once per process.
# Reloading the multi-MB library on every ensure_seeded() call stalls Mission Control / Ask AGI.
_LEARNED_LOADED = False


def ensure_seeded(store: BooksStore | None = None) -> dict[str, Any]:
    global _LEARNED_LOADED
    store = store or get_books_store()
    seeded = False
    if not store.books:
        for b in seed_books():
            store.upsert_book(b)
        for ch in seed_chapters():
            store.upsert_chapter(ch)
        for c in all_seed_concepts():
            store.upsert_concept(c)
        for f in seed_formulas():
            store.upsert_formula(f)
        for fw in seed_frameworks():
            store.upsert_framework(fw)
        rebuild_graph(store)
        seeded = True
    learned = {"ok": False, "skipped": True, "loaded": 0}
    if not _LEARNED_LOADED:
        try:
            from academy.books.persist import load_learned

            # Load durable PDF-learned objects after seed (idempotent upserts).
            learned = load_learned(store)
            if learned.get("ok") and int(learned.get("loaded") or 0) > 0:
                rebuild_graph(store)
            _LEARNED_LOADED = True
        except Exception as exc:
            learned = {"ok": False, "error": str(exc)[:160], "loaded": 0}
            # Still mark loaded to avoid hammering a broken snapshot on every request.
            _LEARNED_LOADED = True
    return {"seeded": seeded, "learned": learned, **store.snapshot()}


def reset_learned_load_flag() -> None:
    """Test helper — allow reloading the learned snapshot after store reset."""
    global _LEARNED_LOADED
    _LEARNED_LOADED = False

def ingest_book(
    *,
    title: str,
    authors: list[str] | None = None,
    content: str = "",
    content_bytes: bytes | None = None,
    filename: str = "",
    subject: str | None = None,
    difficulty: str = "intermediate",
    publication_year: int | None = None,
    publisher: str | None = None,
    edition: str | None = None,
    language: str = "en",
    store: BooksStore | None = None,
) -> dict[str, Any]:
    """
    Ingest one book into structured knowledge.
    Raw text is transient — only short AGI-owned objects are stored.
    """
    store = store or get_books_store()
    ensure_seeded(store)

    # Spreadsheet files route to spreadsheet ingest
    lower_name = (filename or "").lower()
    if lower_name.endswith((".xlsx", ".xls", ".ods", ".csv", ".xlsm")) and content_bytes:
        from academy.books.spreadsheet import ingest_spreadsheet

        return ingest_spreadsheet(
            filename=filename,
            content_bytes=content_bytes,
            title=title,
            store=store,
        )

    extracted = extract_text(filename=filename, content=content, content_bytes=content_bytes)
    text = extracted.get("text") or content or ""
    if not text.strip():
        return {"ok": False, "reason": "no_text", "needs_ocr": bool(extracted.get("needs_ocr"))}

    pdf_meta = extracted.get("metadata") if isinstance(extracted.get("metadata"), dict) else {}
    resolved_title = title or (pdf_meta.get("title") or "").strip() or _book_id(title, filename)
    resolved_authors = list(authors or [])
    if not resolved_authors and pdf_meta.get("author"):
        resolved_authors = [a.strip() for a in str(pdf_meta["author"]).split(",") if a.strip()][:6]
    if not resolved_authors:
        resolved_authors = _guess_authors(resolved_title, filename)

    book_id = _book_id(resolved_title, filename)
    meta = BookMeta(
        book_id=book_id,
        title=resolved_title,
        authors=resolved_authors,
        edition=edition,
        publisher=publisher,
        publication_year=publication_year,
        language=language,
        subject=subject or _guess_subject(text, resolved_title),
        topics=_guess_topics(text),
        difficulty=difficulty,
        source_format=str(extracted.get("format") or "text"),
        academies=[],
    )
    store.upsert_book(meta)

    chapters = detect_hierarchy(book_id, text)
    for ch in chapters:
        store.upsert_chapter(ch)

    academies: set[str] = set()
    concept_n = formula_n = framework_n = 0

    # Extract per chapter using title + summary + a local body window from the book text.
    for ch in chapters:
        window = _chapter_window(text, ch.title, size=9000)
        working = f"{ch.title}. {ch.summary or ''}\n{window}".strip()
        pack = extract_from_text(book_id=book_id, text=working, chapter_title=ch.title)
        for c in pack["concepts"]:
            store.upsert_concept(c)
            academies.add(c.academy)
            concept_n += 1
        for f in pack["formulas"]:
            store.upsert_formula(f)
            academies.add(f.academy)
            formula_n += 1
        for fw in pack["frameworks"]:
            store.upsert_framework(fw)
            academies.add(fw.academy)
            framework_n += 1

    # Multi-slice whole-book pass (front / middle / end) for formulas & frameworks
    n = len(text)
    slices = [
        ("front_matter", text[:20000]),
        ("mid_matter", text[max(0, n // 2 - 10000) : n // 2 + 10000]),
        ("end_matter", text[max(0, n - 20000) :]),
    ]
    # Extra evenly spaced slices for long textbooks
    if n > 60000:
        step = max(15000, n // 8)
        for i, start in enumerate(range(15000, max(15000, n - 15000), step)):
            slices.append((f"slice_{i}", text[start : start + 14000]))
            if len(slices) >= 14:
                break
    for label, chunk in slices:
        pack = extract_from_text(book_id=book_id, text=chunk, chapter_title=label)
        for f in pack["formulas"]:
            store.upsert_formula(f)
            academies.add(f.academy)
            formula_n += 1
        for fw in pack["frameworks"]:
            store.upsert_framework(fw)
            academies.add(fw.academy)
            framework_n += 1
        for c in pack["concepts"][:12]:
            store.upsert_concept(c)
            academies.add(c.academy)
            concept_n += 1

    meta.academies = sorted(academies)
    meta.topics = list(dict.fromkeys(meta.topics + list(academies)))[:16]
    store.upsert_book(meta)
    rebuild_graph(store)

    return {
        "ok": True,
        "book_id": book_id,
        "title": meta.title,
        "author": ", ".join(meta.authors) if meta.authors else None,
        "version": meta.version,
        "format": extracted.get("format"),
        "pages_approx": extracted.get("pages_approx"),
        "pages_processed": extracted.get("pages_processed") or extracted.get("pages_approx"),
        "hierarchy": hierarchy_stats(chapters),
        "extracted": {
            "concepts": concept_n,
            "formulas": formula_n,
            "frameworks": framework_n,
        },
        "academies": meta.academies,
        "books_version": BOOKS_VERSION,
        "raw_text_retained": False,
    }


def _chapter_window(text: str, title: str, *, size: int = 9000) -> str:
    """Return a local body window around a chapter heading for extraction."""
    blob = text or ""
    if not blob or not title:
        return ""
    # Try exact title, then shortened "Chapter N: ..." / bare heading tail.
    candidates = [title]
    if ":" in title:
        candidates.append(title.split(":", 1)[-1].strip())
    if title.lower().startswith("chapter "):
        candidates.append(re.sub(r"(?i)^chapter\s+\d+[:.\s]*", "", title).strip())
    idx = -1
    for cand in candidates:
        if not cand or len(cand) < 4:
            continue
        idx = blob.lower().find(cand.lower())
        if idx >= 0:
            break
    if idx < 0:
        return ""
    start = max(0, idx)
    return blob[start : start + size]


def _book_id(title: str, filename: str) -> str:
    base = title or (Path(filename).stem.replace("_", " ") if filename else "") or "book"
    slug = re.sub(r"[^a-z0-9]+", "_", base.lower()).strip("_")[:48]
    return f"book_{slug}" if not slug.startswith("book_") else slug


def _guess_topics(text: str) -> list[str]:
    keys = [
        "valuation", "dcf", "accounting", "wacc", "roic", "moat", "portfolio",
        "macro", "banking", "fmcg", "behavioural", "risk", "corporate finance",
        "economics", "strategy",
    ]
    blob = (text or "").lower()
    return [k for k in keys if k in blob][:10]


def _guess_authors(title: str, filename: str) -> list[str]:
    blob = f"{title} {filename}".lower()
    if "damodaran" in blob:
        return ["Aswath Damodaran"]
    if "mankiw" in blob:
        return ["N. Gregory Mankiw"]
    return []


def _guess_subject(text: str, title: str) -> str:
    blob = f"{title} {text[:4000]}".lower()
    for label, keys in (
        ("Accounting", ("accounting", "financial statements", "earnings")),
        ("Corporate Finance", ("corporate finance", "capital structure", "capital allocation")),
        ("Valuation", ("valuation", "dcf", "intrinsic")),
        ("Economics", ("economics", "macro", "gdp", "inflation")),
        ("Investment", ("investing", "security analysis", "portfolio")),
    ):
        if any(k in blob for k in keys):
            return label
    return "Investment"


def ingest_markdown_fixture(title: str, markdown: str, **kwargs: Any) -> dict[str, Any]:
    """Test helper — ingest short AGI-authored markdown (not copyrighted books)."""
    return ingest_book(title=title, content=markdown, filename=f"{title}.md", **kwargs)
