"""FIL — financial statement extractor."""

from __future__ import annotations

from filing_intelligence.ingestion.store import documents_for, reset_for_tests
from filing_intelligence.parser.parse import parse_document
from filing_intelligence.statement_extractor.extract import extract_statements


def setup_function() -> None:
    reset_for_tests()


def test_extract_hdfc_cet1_and_nim():
    docs = documents_for("HDFCBANK")
    facts = []
    for d in docs:
        facts.extend(extract_statements(parse_document(d)))
    metrics = {(f.metric, f.period): f.value for f in facts}
    assert metrics[("CET1", "Q1FY27")] == 17.4
    assert metrics[("NIM", "Q1FY27")] == 3.26
    assert metrics[("CASA", "Q1FY27")] == 32.3
    assert metrics[("PAT", "Q1FY27")] == 190.6
