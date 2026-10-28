"""Academy Books — durable PDF-learned snapshot (AGI-owned objects only)."""

from __future__ import annotations

import json
from pathlib import Path

from academy.books.ingest import ensure_seeded, ingest_book
from academy.books.persist import LEARNED_DIR, SNAPSHOT_PATH, load_learned, save_learned
from academy.books.production import package_for_query, reset_for_tests
from academy.books.store import get_books_store


def setup_function() -> None:
    reset_for_tests()


def test_persist_roundtrip_keeps_pdf_learned_concepts(tmp_path: Path):
    markdown = """
# Measuring Earnings Quality

Earnings quality is the degree to which reported income reflects sustainable cash earnings.
Accrual accounting can inflate income when cash conversion is weak.
Free cash flow and ROIC help distinguish accounting earnings from economic earnings.
WACC is the blended cost of equity and debt used in valuation.
"""
    result = ingest_book(
        title="Persist Fixture Earnings",
        content=markdown,
        filename="persist_fixture_earnings.md",
        authors=["Test Author"],
    )
    assert result["ok"] is True
    store = get_books_store()
    before = store.snapshot()
    assert before["concepts"] >= 1

    snap = tmp_path / "library_snapshot.json"
    saved = save_learned(store, path=snap)
    assert saved["ok"] is True
    assert saved["books"] >= 1
    payload = json.loads(snap.read_text(encoding="utf-8"))
    assert payload["verbatim_storage"] is False
    assert payload["searchable_pdf_index"] is False
    assert payload["policy"] == "agi_owned_objects_only"

    reset_for_tests()
    store2 = get_books_store()
    loaded = load_learned(store2, path=snap)
    assert loaded["ok"] is True
    assert loaded["loaded"] >= 1
    assert any("persist_fixture" in bid for bid in store2.books)
    pkg = package_for_query("earnings quality accrual accounting ROIC WACC", limit=8)
    assert pkg["enabled"] is True
    titles = " ".join(c.get("title", "") for c in pkg.get("concepts") or []).lower()
    assert "earning" in titles or "accrual" in titles or "roic" in titles or "wacc" in titles


def test_ensure_seeded_reloads_committed_library_snapshot():
    """If the committed learned snapshot exists, bootstrap restores PDF books."""
    if not SNAPSHOT_PATH.is_file():
        # Snapshot is produced by library ingest; skip when absent in bare checkouts.
        return
    reset_for_tests()
    out = ensure_seeded()
    assert out.get("learned", {}).get("ok") is True
    store = get_books_store()
    pdf_books = [b for b in store.books.values() if (b.source_format or "") == "pdf"]
    assert len(pdf_books) >= 1
    assert any("damodaran" in b.book_id or "mankiw" in b.book_id for b in pdf_books)
    assert LEARNED_DIR.is_dir()
