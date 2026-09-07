from kip_v2.document_intelligence import process_document
from kip_v2.evidence import validate_fact
from kip_v2.financial_intelligence import build_financial_facts, extract_metrics_from_paragraph
from kip_v2.schema import Paragraph
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT


def _paragraphs():
    return process_document(
        company_id="COMP_ARAVALI", doc_type="annual_report", period="FY25",
        title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    ).paragraphs


def test_revenue_extracted_with_correct_value_and_period():
    facts = build_financial_facts("COMP_ARAVALI", _paragraphs(), default_period="FY25")
    revenue = [f for f in facts if f.key == "revenue"]
    assert revenue
    assert revenue[0].value == 4250.0
    assert revenue[0].unit == "crore"
    assert revenue[0].currency == "INR"
    assert revenue[0].period == "FY25"


def test_ebitda_margin_extracted_as_percentage():
    facts = build_financial_facts("COMP_ARAVALI", _paragraphs(), default_period="FY25")
    margin = [f for f in facts if f.key == "ebitda_margin"]
    assert margin
    assert margin[0].value == 16.0
    assert margin[0].unit == "%"


def test_eps_and_dividend_extracted():
    facts = build_financial_facts("COMP_ARAVALI", _paragraphs(), default_period="FY25")
    keys = {f.key: f for f in facts}
    assert keys["eps"].value == 42.50
    assert keys["dividend_per_share"].value == 8.00


def test_all_financial_facts_pass_module7_gate():
    facts = build_financial_facts("COMP_ARAVALI", _paragraphs(), default_period="FY25")
    assert facts
    for f in facts:
        ok, errors = validate_fact(f)
        assert ok, errors


def test_margin_without_percent_qualifier_is_not_extracted():
    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="general", page=1,
                  index=0, text="ROE improved to 18 this year, a notable improvement over the prior period.")
    hits = extract_metrics_from_paragraph(p)
    assert not any(h["metric"] == "roe" for h in hits)


def test_margin_with_percent_qualifier_is_extracted():
    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="general", page=1,
                  index=0, text="ROE improved to 18% this year, a notable improvement over the prior period.")
    hits = extract_metrics_from_paragraph(p)
    roe_hits = [h for h in hits if h["metric"] == "roe"]
    assert roe_hits and roe_hits[0]["value"] == 18.0 and roe_hits[0]["unit"] == "%"


def test_no_number_near_keyword_yields_no_extraction():
    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="general", page=1,
                  index=0, text="Revenue growth remained strong across all our business segments this year.")
    hits = extract_metrics_from_paragraph(p)
    assert hits == []
