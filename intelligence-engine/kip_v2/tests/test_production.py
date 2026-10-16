import kip_v2.production as production
from kip_v2.storage import reset_store_for_tests
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT, FY26_ANNUAL_REPORT


def _reset():
    return reset_store_for_tests()


def test_health_reports_all_modules():
    _reset()
    h = production.health()
    assert h["status"] == "ok"
    assert h["version"] == production.KIP_V2_VERSION
    expected_modules = {
        "document_intelligence", "knowledge_builder", "financial_intelligence",
        "management_intelligence", "change_detection", "knowledge_graph", "evidence",
        "executive_summary", "retrieval", "incremental",
    }
    assert expected_modules <= set(h["modules"])


def test_ingest_via_facade_rejects_missing_fields():
    _reset()
    result = production.ingest({"company_id": "COMP_X"})
    assert result["error"] == "missing_required_fields"
    assert "text" in result["missing"]


def test_full_flow_ingest_summary_ask_changes():
    _reset()
    ingest_result = production.ingest(
        {
            "company_id": "COMP_ARAVALI", "company_name": "Aravali Chemicals", "doc_type": "annual_report",
            "period": "FY25", "title": "t", "source": "s.pdf", "text": FY25_ANNUAL_REPORT,
        }
    )
    assert ingest_result["facts_stored"] > 0

    production.ingest(
        {
            "company_id": "COMP_ARAVALI", "company_name": "Aravali Chemicals", "doc_type": "annual_report",
            "period": "FY26", "title": "t2", "source": "s2.pdf", "text": FY26_ANNUAL_REPORT,
        }
    )

    summary = production.get_executive_summary("COMP_ARAVALI")
    assert summary["sections"]["financial_performance"]["status"] == "known"

    answer = production.ask("COMP_ARAVALI", "What is the business model?")
    assert answer["unknown"] is False

    changes = production.get_changes("COMP_ARAVALI", from_period="FY25", to_period="FY26")
    assert changes["count"] > 0

    financials = production.get_financial_metrics("COMP_ARAVALI", metric="revenue")
    assert financials["count"] == 2  # FY25 + FY26 both retained as history

    graph = production.get_knowledge_graph("COMP_ARAVALI")
    assert graph["nodes"]


def test_ask_requires_question():
    _reset()
    result = production.ask("COMP_X", "")
    assert result["error"] == "question_required"


def test_quality_report_reflects_ingested_data():
    _reset()
    production.ingest(
        {
            "company_id": "COMP_ARAVALI", "company_name": "Aravali Chemicals", "doc_type": "annual_report",
            "period": "FY25", "title": "t", "source": "s.pdf", "text": FY25_ANNUAL_REPORT,
        }
    )
    report = production.quality_report(company_id="COMP_ARAVALI")
    assert report["observed"]["documents_ingested"] == 1
    assert report["observed"]["facts_stored"] > 0
    assert report["observed"]["evidence_coverage_pct"] == 100.0
    assert report["observed"]["fact_extraction_precision_pct"] == 100.0
