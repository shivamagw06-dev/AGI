"""FIL — notes extractor."""

from __future__ import annotations

from filing_intelligence.ingestion.store import get_document, reset_for_tests
from filing_intelligence.notes_extractor.extract import extract_notes
from filing_intelligence.parser.parse import parse_document


def setup_function() -> None:
    reset_for_tests()


def test_notes_from_hdfc_presentation():
    doc = get_document("hdfc_pres_q1fy27")
    assert doc
    notes = extract_notes(parse_document(doc))
    metrics = {n.metric for n in notes}
    assert "Exceptional_Items" in metrics or "Goodwill" in metrics
