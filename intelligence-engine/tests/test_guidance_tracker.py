"""FIL — guidance tracker."""

from __future__ import annotations

from filing_intelligence.guidance.tracker import extract_guidance
from filing_intelligence.ingestion.store import get_document, reset_for_tests
from filing_intelligence.parser.parse import parse_document
from filing_intelligence.pipeline import analyse_ticker


def setup_function() -> None:
    reset_for_tests()


def test_guidance_maintained_despite_nim():
    doc = get_document("hdfc_pres_q1fy27")
    facts = extract_guidance(parse_document(doc))
    status = next(f for f in facts if f.metric == "Guidance_Status")
    assert status.value == "maintained"
    out = analyse_ticker("HDFCBANK")
    assert out["guidance_tracker"]
