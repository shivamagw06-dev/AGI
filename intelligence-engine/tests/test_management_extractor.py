"""FIL — management commentary extractor."""

from __future__ import annotations

from filing_intelligence.ingestion.store import get_document, reset_for_tests
from filing_intelligence.management_commentary.extract import extract_management
from filing_intelligence.parser.parse import parse_document


def setup_function() -> None:
    reset_for_tests()


def test_management_priorities_extracted():
    doc = get_document("hdfc_pres_q1fy27")
    facts = extract_management(parse_document(doc))
    metrics = {f.metric for f in facts}
    assert "Key_Priorities" in metrics or "Margin_Commentary" in metrics
    assert all(f.category == "management" for f in facts)
