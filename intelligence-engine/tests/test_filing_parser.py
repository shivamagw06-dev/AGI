"""FIL — document detection / parser."""

from __future__ import annotations

from filing_intelligence.ingestion.detect import detect_doc_type
from filing_intelligence.ingestion.store import documents_for, reset_for_tests
from filing_intelligence.parser.parse import parse_document


def setup_function() -> None:
    reset_for_tests()


def test_detect_quarterly_and_presentation():
    assert detect_doc_type(title="Press Release — Results for quarter ended 30 June 2026")["doc_type"] in {
        "quarterly_results",
        "press_release",
    }
    assert detect_doc_type(title="Q1FY27 Earnings Presentation")["doc_type"] == "investor_presentation"


def test_parse_hdfc_presentation():
    docs = documents_for("HDFCBANK")
    pres = next(d for d in docs if d["doc_id"] == "hdfc_pres_q1fy27")
    parsed = parse_document(pres)
    assert parsed["doc_type"] == "investor_presentation"
    assert parsed["tables"]
    assert "management" in parsed["sections"] or "body" in parsed["sections"]
