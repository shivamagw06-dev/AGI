from kip_v2.document_intelligence import process_document
from kip_v2.evidence import validate_fact
from kip_v2.knowledge_builder import build_knowledge_facts
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT


def _paragraphs():
    return process_document(
        company_id="COMP_ARAVALI", doc_type="annual_report", period="FY25",
        title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    ).paragraphs


def test_risks_category_detected_with_evidence():
    facts = build_knowledge_facts("COMP_ARAVALI", _paragraphs(), period="FY25")
    risk_facts = [f for f in facts if f.category == "risks"]
    assert risk_facts
    for f in risk_facts:
        ok, errors = validate_fact(f)
        assert ok, errors
        assert "risk" in f.value.lower()


def test_strategy_and_capital_allocation_detected():
    facts = build_knowledge_facts("COMP_ARAVALI", _paragraphs(), period="FY25")
    categories = {f.category for f in facts}
    assert "strategy" in categories
    assert "capital_allocation" in categories


def test_business_model_paragraph_detected():
    facts = build_knowledge_facts("COMP_ARAVALI", _paragraphs(), period="FY25")
    bm = [f for f in facts if f.category == "business_model"]
    assert bm
    assert "specialty chemicals" in bm[0].value.lower()


def test_every_fact_passes_module7_gate():
    facts = build_knowledge_facts("COMP_ARAVALI", _paragraphs(), period="FY25")
    assert facts
    for f in facts:
        ok, _ = validate_fact(f)
        assert ok


def test_irrelevant_paragraph_yields_no_facts():
    from kip_v2.knowledge_builder import classify_paragraph
    from kip_v2.schema import Paragraph

    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="general", page=1,
                  index=0, text="This is a completely unrelated sentence about the weather today.")
    assert classify_paragraph(p) == []
