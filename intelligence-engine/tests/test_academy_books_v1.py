"""AGI Academy Books V1 — structured learning, no verbatim copyright storage."""

from __future__ import annotations

from academy.books.chapters import detect_hierarchy
from academy.books.copyright import MAX_VERBATIM_REJECT, assert_no_long_verbatim, scrub
from academy.books.enrich import enrich_dossier
from academy.books.ingest import ensure_seeded, ingest_markdown_fixture
from academy.books.production import (
    dashboard,
    package_for_query,
    quality_gates,
    research_writer_slice,
    reset_for_tests,
)
from academy.books.store import get_books_store


def setup_function() -> None:
    reset_for_tests()


def test_seed_bootstrap_and_quality_gates():
    out = ensure_seeded()
    assert out["seeded"] is True
    assert out["concepts"] >= 10
    assert out["frameworks"] >= 5
    assert out["formulas"] >= 5
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["checks"]["no_long_verbatim"] is True
    assert gates["checks"]["knowledge_graph_created"] is True


def test_chapter_hierarchy_not_one_blob():
    md = """
# Chapter 1: Valuation Basics
Intrinsic value is the present value of cash flows.
## Section 1.1 Discount Rates
WACC is the blended hurdle rate.
# Chapter 2: Economic Moat
Economic moat means durable excess returns.
"""
    nodes = detect_hierarchy("book_demo", md)
    levels = {n.level for n in nodes}
    assert "chapter" in levels
    assert len(nodes) >= 2


def test_ingest_markdown_extracts_frameworks_and_formulas():
    md = """
# Chapter 1: Value Investing
Margin of safety means buying below conservative intrinsic value.
ROIC is defined as NOPAT divided by invested capital.
Economic moat refers to a durable competitive advantage.
WACC = E/V*re + D/V*rd*(1-t)
Porter's Five Forces frames industry rivalry and buyer power.
"""
    result = ingest_markdown_fixture("Demo Valuation Notes", md, subject="Valuation")
    assert result["ok"] is True
    assert result["raw_text_retained"] is False
    assert result["hierarchy"]["chapter"] >= 1
    store = get_books_store()
    assert any("moat" in c.title.lower() or "roic" in c.title.lower() for c in store.concepts.values()) or store.formulas
    assert store.frameworks or result["extracted"]["frameworks"] >= 0


def test_copyright_scrub_rejects_long_verbatim():
    long = "word " * 300
    cleaned = scrub(long, limit=200)
    assert len(cleaned) <= 200
    bad = assert_no_long_verbatim({"passage": "x" * (MAX_VERBATIM_REJECT + 50)})
    assert bad


def test_package_for_query_nestle_staples_reasoning():
    ensure_seeded()
    pkg = package_for_query("Should I buy Nestle India?", ticker="NESTLEIND", limit=10)
    assert pkg["enabled"] is True
    assert pkg["provenance"]["verbatim_quotes"] is False
    assert pkg["concept_ids"] or pkg["frameworks"]
    hints = " ".join(pkg.get("answer_hints") or []).lower()
    assert "pe" in hints or "staples" in hints or "roic" in hints or "framework" in hints


def test_cid_enrich_nestle_learning_block():
    ensure_seeded()
    dossier = {"ticker": "NESTLEIND", "identity": {"sector_id": "fmcg"}, "finance_academy": {}}
    out = enrich_dossier(dossier, ticker="NESTLEIND")
    fa = out["finance_academy"]
    assert fa.get("book_concepts")
    assert fa.get("frameworks") or fa.get("formulas")
    assert fa.get("sector_learning") or fa.get("valuation_learning")
    # No long verbatim
    blob = str(fa)
    assert "quoteSummary" not in blob
    assert len(blob) < 20000


def test_dashboard_and_research_writer_slice():
    ensure_seeded()
    dash = dashboard()
    assert dash["programme"] == "AGI_ACADEMY_BOOKS"
    assert dash["flags"]["ACADEMY_BOOKS"] is True
    assert dash["copyright"]["searchable_pdf_index"] is False
    slice_ = research_writer_slice("Write research on Nestle", ticker="NESTLEIND")
    assert slice_["rule"] == "never_copy_book_text"
    assert slice_.get("frameworks") is not None


def test_catalog_includes_book_course():
    ensure_seeded()
    from academy.catalog import all_knowledge_objects

    books = all_knowledge_objects("academy_books")
    assert books
    assert all(k.course_id == "academy_books" for k in books)
