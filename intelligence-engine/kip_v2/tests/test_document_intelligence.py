from kip_v2.document_intelligence import (
    detect_section,
    process_document,
    recognize_entities,
)
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT


def test_process_document_parses_sections_and_paragraphs():
    result = process_document(
        company_id="COMP_ARAVALI", doc_type="annual_report", period="FY25",
        title="Aravali FY25 Annual Report", source="aravali_fy25.pdf", text=FY25_ANNUAL_REPORT,
    )
    assert result.stats["parse_success"] is True
    assert len(result.paragraphs) > 5
    sections = {p.section for p in result.paragraphs}
    assert "risk_factors" in sections
    assert "financial_statements" in sections
    assert "strategy_outlook" in sections


def test_paragraphs_have_full_evidence_envelope():
    result = process_document(
        company_id="COMP_ARAVALI", doc_type="annual_report", period="FY25",
        title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    )
    for p in result.paragraphs:
        assert p.document_id == result.document.document_id
        assert p.page >= 1
        assert p.paragraph_id.startswith(result.document.document_id)
        assert p.evidence_hash
        assert isinstance(p.embedding, list) and len(p.embedding) > 0
        assert 0.0 <= p.importance_score <= 1.0


def test_financial_paragraph_scores_higher_importance_than_boilerplate():
    result = process_document(
        company_id="C", doc_type="annual_report", period="FY25", title="t", source="s",
        text=FY25_ANNUAL_REPORT,
    )
    fin_scores = [p.importance_score for p in result.paragraphs if p.section == "financial_statements"]
    overview_scores = [p.importance_score for p in result.paragraphs if p.section == "business_overview"]
    assert fin_scores and overview_scores
    assert max(fin_scores) > min(overview_scores)


def test_section_detection_known_headings():
    assert detect_section("RISK FACTORS") == "risk_factors"
    assert detect_section("Management Discussion and Analysis") == "management_discussion"
    assert detect_section("random body text.") is None


def test_entity_recognition_matches_known_dictionary():
    entities = recognize_entities("Reliance Industries reported strong growth.", {"reliance industries": "COMP_RELIANCE"})
    assert "COMP_RELIANCE" in entities


def test_pages_split_on_form_feed():
    text = "Page one content here.\fPage two content here."
    result = process_document(company_id="C", doc_type="filing", period="FY25", title="t", source="s", text=text)
    pages = {p.page for p in result.paragraphs}
    assert pages == {1, 2}


def test_document_id_is_stable_for_same_inputs():
    r1 = process_document(company_id="C", doc_type="annual_report", period="FY25", title="t", source="src.pdf", text="hello world paragraph text")
    r2 = process_document(company_id="C", doc_type="annual_report", period="FY25", title="t", source="src.pdf", text="hello world paragraph text")
    assert r1.document.document_id == r2.document.document_id
