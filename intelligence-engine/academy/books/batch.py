"""Batch personal-library ingestion + validation report."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from academy.books.ingest import ensure_seeded, ingest_book
from academy.books.library import BOOK_EXTS, SHEET_EXTS, resolve_library_root, scan_library
from academy.books.schema import BOOKS_VERSION
from academy.books.spreadsheet import ingest_spreadsheet
from academy.books.store import get_books_store


def ingest_personal_library(
    *,
    root: str | Path | None = None,
    limit: int | None = None,
    include_spreadsheets: bool = True,
) -> dict[str, Any]:
    """
    Ingest every supported document in the configured books directory.
    Produces a per-file ingestion report. Never retains raw book text.
    """
    store = get_books_store()
    ensure_seeded(store)
    scan = scan_library(Path(root) if root else None)
    if not scan.get("ok"):
        return {
            "ok": False,
            "reason": "library_root_not_found",
            "candidates": scan.get("candidates") or [],
            "hint": "Put library at /Users/shivamagarwal/Downloads/AGIB (or …/Books) or set ACADEMY_BOOKS_DIR",
            "books_version": BOOKS_VERSION,
        }

    files = list(scan.get("books") or [])
    if include_spreadsheets:
        files.extend(scan.get("spreadsheets") or [])
    if limit is not None:
        files = files[: int(limit)]

    reports: list[dict[str, Any]] = []
    ok_n = 0
    fail_n = 0
    for meta in files:
        path = Path(meta["path"])
        ext = (meta.get("ext") or path.suffix).lower()
        title = path.stem.replace("_", " ").replace("-", " ").strip()
        try:
            raw = path.read_bytes()
        except Exception as exc:
            row = {
                "ok": False,
                "title": title,
                "filename": path.name,
                "reason": f"read_failed:{exc}",
                "extraction_quality": "empty",
            }
            reports.append(row)
            fail_n += 1
            continue

        if ext in SHEET_EXTS or ext == ".csv":
            try:
                row = ingest_spreadsheet(filename=path.name, content_bytes=raw, title=title, store=store)
            except Exception as exc:
                row = {
                    "ok": False,
                    "title": title,
                    "filename": path.name,
                    "reason": f"spreadsheet_ingest_failed:{exc}",
                    "extraction_quality": "empty",
                }
        elif ext in BOOK_EXTS:
            try:
                row = ingest_book(
                    title=title,
                    content_bytes=raw,
                    filename=path.name,
                    store=store,
                )
                row = _normalize_book_report(row, title=title, filename=path.name, store=store)
            except Exception as exc:
                row = {
                    "ok": False,
                    "title": title,
                    "filename": path.name,
                    "reason": f"book_ingest_failed:{exc}",
                    "extraction_quality": "empty",
                }
        else:
            row = {"ok": False, "title": title, "filename": path.name, "reason": "unsupported"}

        row.setdefault("title", title)
        row.setdefault("filename", path.name)
        row.setdefault("bytes", meta.get("bytes"))
        row.setdefault("path", str(path))
        # linked companies/sectors snapshot
        row["companies_linked"] = _companies_for_book(store, row.get("book_id"))
        row["sectors_linked"] = _sectors_for_book(store, row.get("book_id"))
        row["academies_updated"] = row.get("academies") or []
        reports.append(row)
        if row.get("ok"):
            ok_n += 1
        else:
            fail_n += 1

    kf_attach = {}
    try:
        from academy.books.kf_attach import attach_books_to_kf

        kf_attach = attach_books_to_kf()
    except Exception as exc:
        kf_attach = {"enabled": False, "error": str(exc)[:160]}

    summary = {
        "ok": True,
        "books_version": BOOKS_VERSION,
        "library_root": scan.get("root"),
        "scanned": scan.get("counts") or {},
        "attempted": len(files),
        "succeeded": ok_n,
        "failed": fail_n,
        "store": store.snapshot(),
        "spreadsheet_count": store.snapshot().get("spreadsheets") or 0,
        "kf_attach": kf_attach,
        "reports": reports,
        "copyright": {
            "verbatim_storage": False,
            "searchable_pdf_index": False,
        },
    }
    try:
        from academy.books.persist import save_learned

        summary["persisted"] = save_learned(store)
    except Exception as exc:
        summary["persisted"] = {"ok": False, "error": str(exc)[:160]}
    # Soft V3 refresh so institutional objects can consume new academies.
    try:
        from academy.books.flags import flag_books_v3
        from academy.books.v3.production import bootstrap as v3_bootstrap

        if flag_books_v3():
            summary["books_v3"] = v3_bootstrap()
    except Exception as exc:
        summary["books_v3"] = {"enabled": False, "error": str(exc)[:160]}
    store.add_ingestion_report(summary)
    return summary


def latest_ingestion_report() -> dict[str, Any] | None:
    store = get_books_store()
    if not store.ingestion_reports:
        return None
    return store.ingestion_reports[-1]


def _normalize_book_report(row: dict[str, Any], *, title: str, filename: str, store) -> dict[str, Any]:
    if not row.get("ok"):
        return {
            **row,
            "title": title,
            "filename": filename,
            "pages_processed": 0,
            "concepts_extracted": 0,
            "frameworks_extracted": 0,
            "formulas_extracted": 0,
            "knowledge_objects_created": 0,
            "extraction_quality": "empty",
        }
    extracted = row.get("extracted") or {}
    concepts = int(extracted.get("concepts") or 0)
    frameworks = int(extracted.get("frameworks") or 0)
    formulas = int(extracted.get("formulas") or 0)
    pages = int(row.get("pages_approx") or row.get("pages_processed") or 0)
    # recount from store for this book if available
    bid = row.get("book_id")
    if bid:
        concepts = sum(1 for c in store.concepts.values() if c.source_book_id == bid)
        frameworks = sum(1 for f in store.frameworks.values() if f.source_book_id == bid)
        formulas = sum(1 for f in store.formulas.values() if f.source_book_id == bid)
        book = store.books.get(bid)
        if book:
            row["author"] = ", ".join(book.authors) if book.authors else None
            row["subject"] = book.subject
            row["topics"] = book.topics
    quality = "high" if (concepts + frameworks + formulas) >= 12 else (
        "medium" if (concepts + frameworks + formulas) >= 5 else ("low" if concepts or frameworks or formulas else "empty")
    )
    return {
        **row,
        "title": title,
        "filename": filename,
        "pages_processed": pages,
        "concepts_extracted": concepts,
        "frameworks_extracted": frameworks,
        "formulas_extracted": formulas,
        "knowledge_objects_created": concepts + frameworks + formulas,
        "extraction_quality": quality,
        "kind": "book",
    }


def _companies_for_book(store, book_id: str | None) -> list[str]:
    if not book_id:
        return []
    out: set[str] = set()
    for c in store.concepts.values():
        if c.source_book_id == book_id:
            out.update(x.upper() for x in c.linked_companies)
    return sorted(out)


def _sectors_for_book(store, book_id: str | None) -> list[str]:
    if not book_id:
        return []
    out: set[str] = set()
    for c in store.concepts.values():
        if c.source_book_id == book_id:
            out.update(c.linked_industries)
            if c.academy.startswith("sector_"):
                out.add(c.academy.replace("sector_", ""))
    return sorted(out)
