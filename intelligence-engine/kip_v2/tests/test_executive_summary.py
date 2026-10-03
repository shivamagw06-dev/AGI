from kip_v2.executive_summary import generate_executive_summary
from kip_v2.pipeline import ingest_document
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT


def test_summary_built_only_from_structured_knowledge(store):
    ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    )
    summary = generate_executive_summary(store, "COMP_ARAVALI")
    assert summary["generated_from"] == "structured_knowledge_only"
    assert summary["sections"]["risks"]["status"] == "known"
    assert summary["sections"]["financial_performance"]["status"] == "known"
    for entry in summary["sections"]["risks"]["entries"]:
        assert "evidence" in entry and entry["evidence"]["document_id"]


def test_unknown_section_marked_when_no_facts(store):
    summary = generate_executive_summary(store, "COMP_UNKNOWN")
    for section in summary["sections"].values():
        assert section["status"] == "unknown"
        assert section["entries"] == []
    assert summary["coverage"] == 0.0


def test_financial_performance_entries_have_evidence_and_period(store):
    ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="t", source="s.pdf", text=FY25_ANNUAL_REPORT,
    )
    summary = generate_executive_summary(store, "COMP_ARAVALI")
    fin = summary["sections"]["financial_performance"]["entries"]
    assert fin
    revenue = [e for e in fin if e["metric"] == "revenue"]
    assert revenue and revenue[0]["period"] == "FY25"
    assert revenue[0]["evidence"]["page"] >= 1
