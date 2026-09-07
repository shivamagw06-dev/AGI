"""Institutional data production hardening — persistence, connectors, QA."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("KF_HD_STORE_ROOT", str(tmp_path / "hd"))
    monkeypatch.setenv("CGL_STORE_ROOT", str(tmp_path / "cgl"))
    monkeypatch.setenv("LIDI_STORE_ROOT", str(tmp_path / "lidi"))
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path / "kip"))
    monkeypatch.setenv("KF_HD_LIVE_COLLECTORS", "false")
    monkeypatch.setenv("KF_HD_FIXTURE_QUARTERLY", "true")
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("INSTITUTIONAL_DATA_CONNECTORS", "true")
    from knowledge_factory.historical_depth import store as hd_store
    from live_data import store as lidi_store

    hd_store.reset_store() if hasattr(hd_store, "reset_store") else None
    lidi_store.reset_runtime()
    yield
    lidi_store.reset_runtime()


def test_atomic_checkpoint_and_resume(tmp_path, monkeypatch):
    monkeypatch.setenv("KIP_DATA_DIR", str(tmp_path / "kip"))
    from institutional_data.persistence.checkpoint import CheckpointManager
    from institutional_data.persistence.queue_persistence import QueuePersistence
    from institutional_data.persistence.resume import ResumeManager

    ck = CheckpointManager()
    ck.save("demo", {"cursor": 3})
    assert ck.load("demo")["cursor"] == 3

    qp = QueuePersistence()
    qp.save_queue(
        {
            "companies": [
                {"company": "INFY", "status": "running"},
                {"company": "TCS", "status": "pending"},
            ]
        }
    )
    rm = ResumeManager()
    report = rm.recover()
    assert report["stuck_running_reset"] >= 1
    q = qp.load_queue()
    statuses = {c["company"]: c["status"] for c in q["companies"]}
    assert statuses["INFY"] == "pending"


def test_bse_connector_injected_csv():
    from institutional_data.connectors.bse import BSECorporateActionsConnector
    from pathlib import Path

    sample = Path(__file__).resolve().parents[2] / "live_data" / "samples" / "bse_corporate_actions.csv"
    text = sample.read_text(encoding="utf-8") if sample.exists() else "Security Name,Purpose,Ex Date\nINFOSYS LTD,Dividend,2024-06-01\n"
    conn = BSECorporateActionsConnector()
    result = conn.run(injected_csv=text)
    assert result.ok
    assert result.normalized
    assert result.diagnostics.get("strategies")


def test_rbi_connector_injected_and_warnings():
    from institutional_data.connectors.rbi import RBIMacroConnector

    payload = {
        "effective_date": "2024-06-01",
        "series": [{"metric": "repo_rate", "value": 6.5, "unit": "percent", "as_of": "2024-06-01"}],
    }
    result = RBIMacroConnector().run(injected_json=payload)
    assert result.ok
    assert result.normalized[0]["series_id"] == "rbi.repo_rate"
    assert result.diagnostics.get("series_missing", 0) >= 1


def test_financial_validate_pit():
    from institutional_data.connectors.financials import FinancialStatementsConnector

    conn = FinancialStatementsConnector()
    records = [
        {
            "entity": "INFY",
            "statement": "income",
            "frequency": "annual",
            "period": "FY24",
            "period_end": "2024-03-31",
            "available_from": "2024-05-15",
            "accounts": {"revenue": 100, "net_income": 20},
            "quality_score": 0.9,
        }
    ]
    v = conn.validate(records)
    assert v["ok"] is True
    bad = [{**records[0], "available_from": "2024-01-01"}]
    assert conn.validate(bad)["ok"] is False


def test_yahoo_financial_records_keep_provider_and_rupee_unit():
    from institutional_data.connectors.financials import FinancialStatementsConnector

    payload = {
        "quoteSummary": {
            "result": [{
                "incomeStatementHistory": {
                    "incomeStatementHistory": [{
                        "endDate": {"raw": 1711843200},
                        "totalRevenue": {"raw": 1_000_000_000},
                    }]
                }
            }]
        }
    }
    rows = FinancialStatementsConnector()._extract_statements(
        payload, entity="INFY", frequency="annual",
    )
    assert rows[0]["units_in"] == "rupee"
    assert rows[0]["metadata"]["provider"] == "yahoo_finance"
    assert rows[0]["metadata"]["parser_path"] == "yahoo_quotesummary"


def test_shareholding_normalize_and_store():
    from institutional_data.connectors.shareholding import ShareholdingConnector
    from knowledge_factory.historical_depth import store as hd_store

    conn = ShareholdingConnector()
    injected = [
        {
            "entity": "INFY",
            "period": "2024-03-31",
            "period_end": "2024-03-31",
            "promoter": 14.0,
            "fii": 33.0,
            "dii": 25.0,
            "mutual_funds": 12.0,
            "public": 16.0,
            "pledged": 0.0,
        }
    ]
    result = conn.run(entity="INFY", injected=injected)
    assert result.ok
    series = hd_store.get_series("shareholding", "INFY")
    assert series and series.get("records")


def test_ir_classify_and_document_intel():
    from institutional_data.connectors.ir_discovery import IRDiscoveryConnector
    from institutional_data.connectors.document_intel import extract_document_intelligence

    conn = IRDiscoveryConnector()
    assert conn.classify("Annual Report 2024", "https://x.com/ar.pdf") == "annual_report"
    assert conn.classify("Earnings Call Transcript", "https://x.com/t.pdf") == "earnings_transcript"
    intel = extract_document_intelligence(
        "INFY",
        {"doc_type": "annual_report", "url": "https://example.com/ar.pdf"},
        text="Our business model and capital allocation strategy drive competitive advantage. Capex guidance raised.",
    )
    assert "business_model" in intel["themes"] or "strategy" in intel["themes"]
    assert intel["confidence"] > 0


def test_chunked_backfill_plan():
    from institutional_data.backfill.chunked import ChunkedBackfillEngine

    eng = ChunkedBackfillEngine(chunk_years=5)
    chunks = eng.plan_chunks(target_years=15)
    assert len(chunks) >= 3
    assert chunks[0][0] < chunks[-1][1]


def test_ops_dashboard_includes_institutional(monkeypatch):
    from continuous_gather_learn.ops_observability import ops_dashboard

    monkeypatch.setattr(
        "knowledge_factory.historical_depth.universe_priority.supported_universe",
        lambda: ["INFY", "TCS"],
    )
    board = ops_dashboard()
    assert "financial_coverage" in board
    assert "shareholding_coverage" in board
    assert "checkpoint_status" in board
    assert "kpis" in board


def test_production_kpis_shape():
    from institutional_data.kpis import production_kpis

    k = production_kpis()
    assert "collector_success_rate" in k
    assert "financial_coverage_pct" in k
    assert "north_star" in k
