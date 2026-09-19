"""Optional PDF provenance enrichment — never requires committing books."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from academy.accounting.curriculum import CHAPTERS as ACC_CHAPTERS
from academy.accounting.curriculum import chapter_meta as acc_chapter_meta
from academy.corporate_finance.curriculum import CHAPTERS as ACF_CHAPTERS
from academy.corporate_finance.curriculum import chapter_meta as acf_chapter_meta
from academy.curriculum import CHAPTERS as ECO_CHAPTERS
from academy.curriculum import PDF_PAGE_OFFSET, chapter_meta as eco_chapter_meta


MANKIW_CANDIDATES = [
    Path("/workspace/books/Mankiw_Principles_of_Economics.pdf"),
    Path.home() / "Downloads" / "AGIB" / "books" / "Mankiw_Principles_of_Economics.pdf",
    Path.home() / "Downloads" / "AGIB" / "Books" / "Mankiw_Principles_of_Economics.pdf",
]

DAMODARAN_ACCOUNTING_CANDIDATES = [
    Path("/workspace/books/Damodaran_Understanding_Financial_Statements.pdf"),
    Path("/workspace/books/Damodaran_Accounting_Prep.pdf"),
    Path("/workspace/books/Damodaran_Measuring_Earnings.pdf"),
    Path.home() / "Downloads" / "AGIB" / "books" / "Damodaran_Understanding_Financial_Statements.pdf",
    Path.home() / "Downloads" / "AGIB" / "Books" / "Minimalist_Accounting.pdf",
]

DAMODARAN_ACF_CANDIDATES = [
    Path("/workspace/books/Damodaran_Applied_Corporate_Finance.pdf"),
    Path.home() / "Downloads" / "AGIB" / "books" / "Damodaran_Applied_Corporate_Finance.pdf",
    Path.home() / "Downloads" / "AGIB" / "Books" / "Applied_Corporate_Finance.pdf",
]


def _first_existing(paths: list[Path]) -> Path | None:
    for p in paths:
        if p.exists():
            return p
    return None


def locate_pdf(explicit: str | None = None, *, course: str = "economics") -> Path | None:
    if explicit:
        p = Path(explicit)
        return p if p.exists() else None
    if course in ("acf", "corporate_finance", "applied_corporate_finance"):
        env = os.environ.get("AGI_ACADEMY_ACF_PDF")
        if env and Path(env).exists():
            return Path(env)
        return _first_existing(DAMODARAN_ACF_CANDIDATES)
    if course in ("accounting", "damodaran", "minimalist_accounting"):
        env = os.environ.get("AGI_ACADEMY_DAMODARAN_PDF")
        if env and Path(env).exists():
            return Path(env)
        return _first_existing(DAMODARAN_ACCOUNTING_CANDIDATES)
    env = os.environ.get("AGI_ACADEMY_MANKIW_PDF")
    if env and Path(env).exists():
        return Path(env)
    return _first_existing(MANKIW_CANDIDATES)


def _pdf_meta(path: Path | None) -> dict[str, Any]:
    if path is None:
        return {"pdf_found": False, "pdf_path": None, "pdf_pages": None}
    try:
        from pypdf import PdfReader

        return {"pdf_found": True, "pdf_path": str(path), "pdf_pages": len(PdfReader(str(path)).pages)}
    except Exception as exc:  # noqa: BLE001
        return {"pdf_found": True, "pdf_path": str(path), "pdf_pages": None, "error": str(exc)}


def provenance_status(pdf_path: str | None = None) -> dict[str, Any]:
    eco_path = locate_pdf(pdf_path, course="economics")
    acc_path = locate_pdf(course="accounting")
    acf_path = locate_pdf(course="acf")
    eco_chapters = []
    for row in ECO_CHAPTERS:
        meta = eco_chapter_meta(row["chapter"])
        eco_chapters.append(
            {
                "chapter": meta["chapter"],
                "title": meta["title"],
                "printed_page": meta["printed_page"],
                "pdf_page_estimate": meta["pdf_page"],
            }
        )
    acc_chapters = []
    for row in ACC_CHAPTERS:
        meta = acc_chapter_meta(row["chapter"])
        acc_chapters.append(
            {
                "chapter": meta["chapter"],
                "title": meta["title"],
                "printed_page": meta.get("printed_page"),
                "pdf_page_estimate": meta.get("pdf_page"),
                "source": meta.get("source"),
            }
        )
    acf_chapters = []
    for row in ACF_CHAPTERS:
        meta = acf_chapter_meta(row["chapter"])
        acf_chapters.append(
            {
                "chapter": meta["chapter"],
                "title": meta["title"],
                "printed_page": meta.get("printed_page"),
                "pdf_page_estimate": meta.get("pdf_page"),
            }
        )
    return {
        "note": "PDFs are gitignored; provenance uses local paths only",
        "economics": {**_pdf_meta(eco_path), "pdf_page_offset": PDF_PAGE_OFFSET, "chapters": eco_chapters},
        "accounting": {
            **_pdf_meta(acc_path),
            "materials": [str(p) for p in DAMODARAN_ACCOUNTING_CANDIDATES if p.exists()],
            "chapters": acc_chapters,
        },
        "corporate_finance": {
            **_pdf_meta(acf_path),
            "materials": [str(p) for p in DAMODARAN_ACF_CANDIDATES if p.exists()],
            "chapters": acf_chapters,
        },
        "pdf_found": eco_path is not None or acc_path is not None or acf_path is not None,
        "pdf_page_offset": PDF_PAGE_OFFSET,
        "chapters": eco_chapters,
    }


def enrich_concept_pages(concept_id: str, section_hint: str | None = None) -> dict[str, Any]:
    """Best-effort page hit search inside local PDF; soft-fails if unavailable."""
    from academy.catalog import knowledge_by_id

    ko = knowledge_by_id().get(concept_id)
    if not ko:
        raise KeyError(concept_id)
    base = {
        "concept_id": concept_id,
        "sources": [s.to_dict() for s in ko.sources],
        "section_hint": section_hint,
        "course_id": ko.course_id,
    }
    if "corporate_finance" in (ko.course_id or "") or "course:corporate_finance" in ko.tags:
        course = "acf"
    elif "accounting" in (ko.course_id or "") or "course:accounting" in ko.tags:
        course = "accounting"
    else:
        course = "economics"
    path = locate_pdf(course=course)
    if path is None:
        return {**base, "enriched": False, "reason": "pdf_not_found"}
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        needle = ko.concept.split()[0].lower()
        primary = ko.sources[0]
        start = max(0, (primary.pdf_page or 1) - 2)
        end = min(len(reader.pages), start + 40)
        hits = []
        for i in range(start, end):
            text = (reader.pages[i].extract_text() or "").lower()
            if needle in text:
                hits.append(i + 1)
            if len(hits) >= 5:
                break
        return {**base, "enriched": True, "pdf_path": str(path), "page_hits": hits}
    except Exception as exc:  # noqa: BLE001
        return {**base, "enriched": False, "reason": str(exc)}
