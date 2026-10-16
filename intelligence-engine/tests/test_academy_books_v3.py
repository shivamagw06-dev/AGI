"""Academy Books V3 — institutional knowledge transformation tests."""

from __future__ import annotations

from academy.books.production import package_for_query as v2_package
from academy.books.production import quality_gates as v2_quality_gates
from academy.books.production import reset_for_tests as reset_v2
from academy.books.v3.production import (
    dashboard,
    package_for_query,
    quality_gates,
    reset_for_tests,
)
from academy.books.v3.retrieval import institutional_ask
from academy.books.v3.schema import BOOKS_V3_VERSION
from academy.books.v3.store import ensure_v3_seeded


def setup_function() -> None:
    reset_for_tests()
    reset_v2()


def test_v3_seed_and_quality_gates():
    snap = ensure_v3_seeded()
    assert snap["seeded"] is True
    assert snap["concepts"] >= 6
    assert snap["frameworks"] >= 8
    assert snap["mental_models"] >= 10
    assert snap["sectors"] >= 10
    assert snap["institutional_objects"] >= 2
    assert snap["edges"] >= 20
    gates = quality_gates()
    assert gates["passed"] is True
    assert gates["checks"]["roic_returns_synthesis_not_paragraph"] is True
    assert gates["checks"]["roic_multi_author"] is True
    assert len(gates["roic_authors_seen"]) >= 3


def test_roic_ask_returns_unified_institutional_object():
    result = institutional_ask("How should I interpret high ROIC?", analyst="valuation")
    assert result["retrieval_policy"]["never_retrieve"] == [
        "chapters",
        "paragraphs",
        "pdfs",
        "verbatim_book_text",
    ]
    assert result["provenance"]["pdf_returned"] is False
    assert result["provenance"]["chapter_text_returned"] is False
    assert result["provenance"]["cross_book_synthesis"] is True
    primary = result["primary"]
    assert primary["type"] == "institutional_knowledge_object"
    obj = primary["object"]
    assert obj["topic"] == "ROIC"
    authors = set(obj.get("source_authors") or [])
    assert "Damodaran" in authors
    assert len(authors) >= 3
    assert result["decision_rules"]
    assert result["frameworks"]
    assert result["lessons"]
    # Must not look like a single-book paragraph dump
    blob = str(result).lower()
    assert "page " not in blob
    assert ".pdf" not in blob


def test_never_returns_chapter_text_or_pdf():
    result = institutional_ask("Give me frameworks and cases for pricing power")
    assert "chapters" not in (result.get("primary") or {})
    assert result.get("provenance", {}).get("chapter_text_returned") is False
    # chapter knowledge may exist in store but ask path returns structured objects only
    assert "raw_text" not in result
    assert "pdf_bytes" not in result
    assert result.get("frameworks") or result.get("concepts") or result.get("patterns")


def test_author_comparison_and_patterns():
    result = institutional_ask("margin of safety intrinsic value Graham Klarman Damodaran")
    assert result["author_comparison"] or result["institutional_objects"]
    result2 = institutional_ask("value trap cyclical compounder patterns")
    names = {p.get("name", "").lower() for p in result2.get("patterns") or []}
    assert "value trap" in names or "cyclical" in names or "compounder" in names


def test_analyst_knowledge_bases():
    for analyst in ("business", "financial", "valuation", "risk", "macro"):
        pack = institutional_ask(f"{analyst} frameworks decision rules", analyst=analyst)
        assert pack["analyst_knowledge_base"] is not None
        assert pack["analyst_knowledge_base"]["analyst"] == analyst
        assert pack["analyst_knowledge_base"]["receives"]


def test_package_and_dashboard():
    pkg = package_for_query("How should I interpret high ROIC?", analyst="valuation")
    assert pkg["enabled"] is True
    assert pkg["books_v3_version"] == BOOKS_V3_VERSION
    assert pkg["institutional_objects"]
    dash = dashboard()
    assert dash["programme"] == "AGI_ACADEMY_BOOKS_V3"
    assert "banking" in " ".join(s.lower() for s in dash["sectors"])
    assert "ROIC" in dash["institutional_topics"]


def test_v2_soft_wire_includes_v3():
    from academy.books.ingest import ensure_seeded

    ensure_seeded()
    pkg = v2_package("How should I interpret high ROIC?", ticker=None, limit=8)
    assert pkg["enabled"] is True
    assert "books_v3" in pkg
    assert pkg["books_v3"]["mode"] == "institutional_knowledge"
    assert pkg["provenance"].get("books_v3") is True
    gates = v2_quality_gates()
    assert gates["checks"].get("books_v3_institutional") is True


def test_iai_soft_consume_valuation():
    from institutional_analysts.valuation.brain.knowledge.catalog import knowledge_pack

    pack = knowledge_pack()
    assert "academy_institutional" in pack
    inst = pack["academy_institutional"]
    assert inst.get("enabled") is True
    assert inst.get("primary") or inst.get("frameworks") or inst.get("institutional_objects")
