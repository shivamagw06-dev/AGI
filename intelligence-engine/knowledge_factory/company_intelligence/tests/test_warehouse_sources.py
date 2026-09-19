from knowledge_factory.company_intelligence.collectors import soft
from knowledge_factory.company_intelligence.producers.core import produce_competition, produce_identity


def test_collect_context_prefers_warehouse_identity_and_peers(monkeypatch):
    monkeypatch.setattr(soft, "_warehouse_company", lambda ticker: {
        "symbol": ticker, "company_name": "Example Industries", "isin": "INE000X01000",
        "sector": "Industrials", "industry": "Engineering", "exchange": "NSE",
    })
    monkeypatch.setattr(soft, "_warehouse_peers", lambda ticker: ["PEER1", "PEER2"])
    ctx = soft.collect_company_context("example")
    identity = produce_identity(ctx)
    competition = produce_competition(ctx)
    assert ctx["sector"] == "Industrials"
    assert identity["fields"]["company_name"]["value"] == "Example Industries"
    assert identity["fields"]["isin"]["value"] == "INE000X01000"
    assert identity["fields"]["sector"]["provenance"]["source"] == "institutional_warehouse"
    assert competition["fields"]["primary_competitors"]["value"] == ["PEER1", "PEER2"]
    assert competition["fields"]["primary_competitors"]["provenance"]["source"] == "institutional_warehouse"
