from kip_v2.document_intelligence import process_document
from kip_v2.evidence import validate_fact
from kip_v2.management_intelligence import build_management_facts, extract_statements_from_paragraph
from kip_v2.schema import Paragraph
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT


def _paragraphs():
    return process_document(
        company_id="COMP_ARAVALI", doc_type="annual_report", period="FY25",
        title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    ).paragraphs


def test_speaker_line_statement_extracted_with_attribution():
    facts = build_management_facts("COMP_ARAVALI", _paragraphs(), period="FY25")
    assert facts
    speakers = {f.extra.get("speaker") for f in facts}
    assert "Suresh Iyer" in speakers


def test_topics_classified_correctly():
    facts = build_management_facts("COMP_ARAVALI", _paragraphs(), period="FY25")
    topics = {f.key for f in facts}
    assert "growth_priorities" in topics
    assert "demand_outlook" in topics


def test_quoted_speech_with_reported_attribution():
    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="management_commentary",
                  page=1, index=0,
                  text='"Our pricing strategy remains disciplined for the coming year," said Anita Rao, CFO.')
    stmts = extract_statements_from_paragraph(p)
    assert stmts
    assert stmts[0]["speaker"] == "Anita Rao"
    assert stmts[0]["topic"] == "pricing"


def test_sentiment_scored_positive_for_confident_language():
    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="management_commentary",
                  page=1, index=0,
                  text="John Doe (CEO): We remain confident in strong demand outlook and robust growth priorities ahead.")
    stmts = extract_statements_from_paragraph(p)
    assert any(s["sentiment"] == "positive" for s in stmts)


def test_sentiment_scored_negative_for_cautious_language():
    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="management_commentary",
                  page=1, index=0,
                  text="John Doe (CEO): We remain cautious given demand outlook headwinds and a challenging pricing environment.")
    stmts = extract_statements_from_paragraph(p)
    assert any(s["sentiment"] == "negative" for s in stmts)


def test_no_topic_match_yields_no_statement():
    p = Paragraph(paragraph_id="x:p0", document_id="x", company_id="C", section="management_commentary",
                  page=1, index=0, text="Jane Smith (CFO): We had lunch at the new cafeteria today.")
    assert extract_statements_from_paragraph(p) == []


def test_all_management_facts_pass_module7_gate():
    facts = build_management_facts("COMP_ARAVALI", _paragraphs(), period="FY25")
    assert facts
    for f in facts:
        ok, errors = validate_fact(f)
        assert ok, errors
