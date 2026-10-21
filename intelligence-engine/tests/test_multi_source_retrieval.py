"""Multi-source Ask retrieval — Private Markets, Valuation CMS, Nifty router."""

from __future__ import annotations

from multi_source.intent_router import route_sources
from multi_source.orchestrator import retrieve_multi_source
from multi_source.private_markets import PrivateMarketsSource
from multi_source.valuation_cms import ValuationCmsSource


def test_route_private_markets_for_pe_questions():
    routing = route_sources("What companies does KKR own in healthcare?")
    assert routing["private_markets"] is True
    assert routing["valuation_monitor"] is True


def test_route_nifty_for_ticker_questions():
    routing = route_sources("Is TCS quality improving?", ticker="TCS")
    assert routing["nifty_research"] is True


def test_route_valuation_questions():
    routing = route_sources("Is Reliance expensive on EV/EBITDA?")
    assert routing["valuation_monitor"] is True


def test_private_markets_adapter_finds_kkr():
    src = PrivateMarketsSource()
    hits = src.search("KKR healthcare acquisition")
    assert isinstance(hits, list)
    assert hits, "expected seeded PE entities/transactions to match KKR/healthcare"
    assert any("private_markets" == h.source for h in hits)


def test_valuation_cms_adapter_returns_published_rows():
    src = ValuationCmsSource()
    hits = src.search("valuation multiples healthcare")
    assert isinstance(hits, list)
    # Seeded CMS has valuation + transaction rows
    assert hits


def test_orchestrator_soft_returns_pack():
    pack = retrieve_multi_source("What did Blackstone acquire?", ticker=None)
    assert pack.get("enabled") is True
    assert "routing" in pack
    assert "sources_queried" in pack
    assert pack.get("fabricated") is False
    assert pack.get("evidence_count", 0) >= 1
    assert pack.get("ask_agi_hints")
