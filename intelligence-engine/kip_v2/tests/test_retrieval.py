from kip_v2.pipeline import ingest_document
from kip_v2.retrieval import answer_question
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT


def test_structured_answer_returns_evidence(store):
    ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    )
    result = answer_question(store, "COMP_ARAVALI", "What is Aravali's business model?")
    assert result["unknown"] is False
    assert result["source"] == "structured_knowledge"
    assert result["evidence"]
    assert "specialty chemicals" in result["answer"].lower()


def test_financial_metric_question_answered_from_structured_knowledge(store):
    ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    )
    result = answer_question(store, "COMP_ARAVALI", "What was the revenue?")
    assert result["unknown"] is False
    assert result["key"] == "revenue"


def test_unknown_company_returns_unknown_not_fabricated(store):
    result = answer_question(store, "COMP_NONEXISTENT", "What is the business model?")
    assert result["unknown"] is True
    assert result["answer"] is None
    assert result["evidence"] == []


def test_unrelated_question_does_not_fabricate(store):
    ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    )
    result = answer_question(store, "COMP_ARAVALI", "What is the weather forecast for tomorrow?")
    assert result["unknown"] is True


def test_retrieval_never_reruns_extraction(store, monkeypatch):
    ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    )
    import kip_v2.document_intelligence as di

    def _boom(*args, **kwargs):
        raise AssertionError("retrieval must not re-run document extraction")

    monkeypatch.setattr(di, "process_document", _boom)
    result = answer_question(store, "COMP_ARAVALI", "What is Aravali's business model?")
    assert result["unknown"] is False
