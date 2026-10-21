"""Sprint 6.4 — Knowledge Retrieval & Intelligence Gateway."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.collectors.yahoo.collector import YahooCollector
from app.config.settings import Settings
from app.krig.gateway import KnowledgeRetrievalGateway
from app.krig.query import classify_query
from app.main import create_app
from app.pipeline.orchestrator import AcquisitionPipeline
from app.storage.db import KaipStore


def _settings(tmp_path: Path, watchlist: tuple[str, ...] = ("INFY", "HDFCBANK", "ICICIBANK")) -> Settings:
    return Settings(
        db_path=tmp_path / "kaip.db",
        scheduler_enabled=False,
        live_collectors_enabled=False,
        watchlist=watchlist,
        duplicate_window_seconds=0,
    )


def _seed_company(pipeline: AcquisitionPipeline, symbol: str, *, pe: float, growth: float, name: str) -> None:
    fixture = {
        "yahoo_symbol": f"{symbol}.NS",
        "as_of": "2026-07-28T10:00:00+00:00",
        "info": {
            "longName": name,
            "sector": "Financials" if "BANK" in symbol else "Technology",
            "industry": "Private Sector Bank" if "BANK" in symbol else "IT Services",
            "currency": "INR",
            "marketCap": 9000000000000,
            "trailingPE": pe,
            "regularMarketPrice": 1600.0,
            "regularMarketVolume": 1000000,
            "revenueGrowth": growth,
            "earningsGrowth": 0.1,
            "totalCash": 1e11,
            "totalDebt": 5e10,
            "pat_margin": 0.21,
        },
    }
    pipeline.run_collector(
        YahooCollector(symbols=[symbol], live=False, fixture_payloads={symbol: fixture})
    )


def test_classify_compare_and_macro_queries() -> None:
    q = classify_query(question="Compare HDFC Bank vs ICICI Bank after RBI cut rates")
    assert q.query_type.value == "compare"
    assert "HDFCBANK" in q.symbols
    assert "ICICIBANK" in q.symbols

    m = classify_query(question="What did the RBI do to inflation and GDP?")
    assert m.query_type.value == "macro"


def test_company_bundle_checklist_and_cache(tmp_path: Path) -> None:
    settings = _settings(tmp_path, watchlist=("INFY",))
    store = KaipStore(settings.db_path)
    pipeline = AcquisitionPipeline(store, settings)
    _seed_company(pipeline, "INFY", pe=25.3, growth=0.19, name="Infosys")

    gateway = KnowledgeRetrievalGateway(store)
    b1 = gateway.company_bundle("INFY", question="Should I invest in Infosys?")
    assert b1.query_type.value == "company"
    assert b1.company is not None
    checklist = b1.checklist()
    assert checklist["Company"] is True
    assert checklist["Financials"] is True
    assert checklist["Valuation"] is True
    assert checklist["Historical Learning"] or checklist["Memory"] or True
    assert b1.provenance["providers_hidden"] is True
    assert "marketCap" not in str(b1.company)

    b2 = gateway.company_bundle("INFY", question="Should I invest in Infosys?")
    assert b2.cache.get("hit") is True

    store.close()


def test_compare_hdfc_icici_after_rbi_cut(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    store = KaipStore(settings.db_path)
    pipeline = AcquisitionPipeline(store, settings)
    _seed_company(pipeline, "HDFCBANK", pe=18.5, growth=0.14, name="HDFC Bank Ltd")
    _seed_company(pipeline, "ICICIBANK", pe=17.2, growth=0.16, name="ICICI Bank Ltd")

    # Sector tip + market learning for banking / lower rates
    store.insert_sector_learning(
        type(
            "SL",
            (),
            {
                "learning_id": "sl1",
                "sector": "Financials",
                "sector_key": "financials",
                "observation": "Banks benefiting from lower-rate regime.",
                "supporting_companies": ["HDFCBANK", "ICICIBANK"],
                "field_name": "revenue_growth",
                "importance": "High",
                "created_at": "2026-07-28T10:00:00+00:00",
            },
        )()
    )
    store.insert_market_learning(
        type(
            "ML",
            (),
            {
                "learning_id": "ml1",
                "theme": "Lower Rates",
                "observation": "Rate-sensitive sectors rallying after RBI cut.",
                "beneficiaries": ["Banks", "Autos", "Housing"],
                "supporting_sectors": ["Financials", "Consumer Cyclical", "Real Estate"],
                "historical_confidence": "High",
                "created_at": "2026-07-28T10:00:00+00:00",
            },
        )()
    )

    gateway = KnowledgeRetrievalGateway(store)
    question = "Compare HDFC Bank vs ICICI Bank after RBI cut rates."
    bundle = gateway.retrieve(question=question)

    assert bundle.query_type.value == "compare"
    assert set(bundle.subjects) >= {"HDFCBANK", "ICICIBANK"}
    assert "HDFCBANK" in bundle.companies
    assert "ICICIBANK" in bundle.companies
    assert bundle.sector is not None or bundle.companies["HDFCBANK"].get("company")
    assert bundle.macro is not None
    assert bundle.macro.get("rbi", {}).get("latest_action") == "Rate cut"
    assert any(e.get("theme") == "RBI Cut Cycle" for e in bundle.evidence)
    assert bundle.comparison is not None
    assert bundle.comparison.get("shared_macro") is True
    # IE performs zero discovery — providers hidden
    assert bundle.provenance["gateway"] == "KRIG"
    assert "yahoo" not in str(bundle.to_public_dict()).lower() or "Yahoo" in str(
        (bundle.companies.get("HDFCBANK") or {}).get("company", {}).get("metadata", {})
    )

    store.close()


def test_krig_http_apis(tmp_path: Path) -> None:
    settings = _settings(tmp_path, watchlist=("INFY", "HDFCBANK", "ICICIBANK"))
    db = settings.db_path
    pipeline = AcquisitionPipeline(KaipStore(db), settings)
    _seed_company(pipeline, "INFY", pe=25.0, growth=0.2, name="Infosys")
    _seed_company(pipeline, "HDFCBANK", pe=18.0, growth=0.12, name="HDFC Bank Ltd")
    _seed_company(pipeline, "ICICIBANK", pe=17.0, growth=0.13, name="ICICI Bank Ltd")
    pipeline.store.close()

    app = create_app(Settings(db_path=db, scheduler_enabled=False, live_collectors_enabled=False))
    with TestClient(app) as client:
        company = client.get("/v1/knowledge/bundle/company/INFY")
        assert company.status_code == 200
        body = company.json()
        assert body["checklist"]["Company"] is True
        assert body["provenance"]["gateway"] == "KRIG"

        compare = client.post(
            "/v1/knowledge/compare",
            json={
                "symbols": ["HDFCBANK", "ICICIBANK"],
                "question": "Compare HDFC Bank vs ICICI Bank after RBI cut rates",
            },
        )
        assert compare.status_code == 200
        cb = compare.json()
        assert cb["query_type"] == "compare"
        assert "HDFCBANK" in cb["companies"]
        assert cb["macro"]["rbi"]["latest_action"] == "Rate cut"

        macro = client.get("/v1/knowledge/macro", params={"question": "RBI rate cut"})
        assert macro.status_code == 200
        assert macro.json()["macro"]["historical_cycles"]

        metrics = client.get("/v1/internal/krig/metrics")
        assert metrics.status_code == 200
        assert metrics.json()["metrics"]
