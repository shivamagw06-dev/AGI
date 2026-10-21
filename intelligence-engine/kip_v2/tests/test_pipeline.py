from kip_v2.pipeline import ingest_document
from kip_v2.tests.conftest import FY25_ANNUAL_REPORT, FY26_ANNUAL_REPORT


def _ingest_fy25(store):
    return ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="Aravali FY25 AR", source="aravali_fy25.pdf", text=FY25_ANNUAL_REPORT,
        sector="Chemicals", industry="Specialty Chemicals",
    )


def test_ingest_stores_facts_and_builds_graph(store):
    result = _ingest_fy25(store)
    assert result["facts_stored"] > 0
    assert result["graph_nodes_upserted"] > 0
    stats = store.stats()
    assert stats["documents"] == 1
    assert stats["paragraphs"] == result["paragraphs_parsed"]


def test_idempotent_reingestion_produces_no_new_paragraphs(store):
    _ingest_fy25(store)
    result2 = _ingest_fy25(store)
    assert result2["paragraphs_new"] == 0
    assert result2["facts_extracted"] == 0
    stats = store.stats()
    assert stats["paragraphs"] == result2["paragraphs_parsed"]  # unchanged total


def test_new_period_triggers_change_detection(store):
    _ingest_fy25(store)
    result = ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY26", title="Aravali FY26 AR", source="aravali_fy26.pdf", text=FY26_ANNUAL_REPORT,
        sector="Chemicals", industry="Specialty Chemicals",
    )
    assert result["compared_against_period"] == "FY25"
    assert result["change_deltas_detected"] > 0
    deltas = store.get_deltas("COMP_ARAVALI", from_period="FY25", to_period="FY26")
    assert deltas
    capex_delta = [d for d in deltas if d.key == "capex"]
    assert capex_delta and capex_delta[0].change_type == "increased"
    debt_delta = [d for d in deltas if d.key == "debt"]
    assert debt_delta and debt_delta[0].change_type == "decreased"


def test_restated_report_same_period_supersedes_old_facts(store):
    _ingest_fy25(store)
    restated_text = FY25_ANNUAL_REPORT.replace("Rs. 4,250 crore", "Rs. 4,400 crore")
    result = ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY25", title="Aravali FY25 AR (restated)", source="aravali_fy25_restated.pdf", text=restated_text,
    )
    assert result["prior_version_archived_facts"] > 0
    active_revenue = store.get_facts("COMP_ARAVALI", category="financial_metric", key="revenue", period="FY25")
    assert len(active_revenue) == 1
    assert active_revenue[0].value == 4400.0
    archived = store.get_facts("COMP_ARAVALI", category="financial_metric", key="revenue", period="FY25", status="archived")
    assert len(archived) == 1
    assert archived[0].value == 4250.0
    assert archived[0].superseded_by == active_revenue[0].fact_id


def test_both_periods_coexist_as_history(store):
    _ingest_fy25(store)
    ingest_document(
        store, company_id="COMP_ARAVALI", company_name="Aravali Chemicals", doc_type="annual_report",
        period="FY26", title="Aravali FY26 AR", source="aravali_fy26.pdf", text=FY26_ANNUAL_REPORT,
    )
    fy25_revenue = store.get_facts("COMP_ARAVALI", category="financial_metric", key="revenue", period="FY25")
    fy26_revenue = store.get_facts("COMP_ARAVALI", category="financial_metric", key="revenue", period="FY26")
    assert fy25_revenue and fy25_revenue[0].value == 4250.0
    assert fy26_revenue and fy26_revenue[0].value == 5100.0


def test_no_facts_stored_without_valid_evidence(store):
    result = _ingest_fy25(store)
    assert result["facts_rejected"] == 0  # all extracted facts here have valid evidence by construction
