"""Academy Books V2 — personal library + spreadsheet ingestion."""

from __future__ import annotations

from pathlib import Path

from academy.books.batch import ingest_personal_library
from academy.books.library import candidate_roots, scan_library
from academy.books.production import dashboard, reset_for_tests
from academy.books.spreadsheet import ingest_spreadsheet, parse_spreadsheet
from academy.books.store import get_books_store


def setup_function() -> None:
    reset_for_tests()


def test_candidate_roots_include_project_books():
    roots = [str(p) for p in candidate_roots()]
    # tests/ → intelligence-engine → repo root
    project_root = Path(__file__).resolve().parents[2]
    assert str(project_root / "books") in roots or str(project_root / "Books") in roots
    assert "/Users/shivamagarwal/Downloads/AGIB" in roots
    assert "/Users/shivamagarwal/Downloads/AGIB/Books" in roots


def test_library_scan_finds_workspace_books():
    scan = scan_library()
    assert scan["ok"] is True
    assert scan["root"]
    assert (scan.get("counts") or {}).get("books", 0) >= 1


def test_spreadsheet_formula_extraction_csv():
    csv = b"Metric,Value\nROE,0.18\nROIC,0.22\nWACC,0.10\nFCF,120\n"
    parsed = parse_spreadsheet(filename="model.csv", content_bytes=csv)
    assert parsed["ok"] is True
    names = {f["name"].upper() for f in parsed.get("formulas") or []}
    assert "ROE" in names or "ROIC" in names or "WACC" in names
    result = ingest_spreadsheet(filename="model.csv", content_bytes=csv, title="Demo Model")
    assert result["ok"] is True
    assert result["kind"] == "spreadsheet"
    assert result["raw_text_retained"] is False
    store = get_books_store()
    assert store.snapshot().get("spreadsheets", 0) >= 1


def test_batch_ingest_workspace_library_produces_report():
    report = ingest_personal_library(root="/workspace/books", limit=2, include_spreadsheets=True)
    assert report["ok"] is True
    assert report["attempted"] >= 1
    assert report["succeeded"] >= 1
    assert report["reports"]
    row = report["reports"][0]
    assert "concepts_extracted" in row
    assert "frameworks_extracted" in row
    assert "formulas_extracted" in row
    assert row.get("raw_text_retained") is False
    dash = dashboard()
    assert dash["books_version"].startswith("academy-books-v2")
    assert dash["books_successfully_ingested"] >= 1
