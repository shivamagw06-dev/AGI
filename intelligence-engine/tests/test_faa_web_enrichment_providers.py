"""Strategic Exa / Firecrawl / Browserbase wiring for FAA searches."""

from __future__ import annotations

import os
from unittest.mock import patch

from app.faa.connectors.search_api import (
    FirecrawlSearchConnector,
    SearchApiConnector,
    available_search_providers,
    prefer_providers_for_document_type,
    select_search_provider,
)
from app.faa.discovery import DiscoveryService
from app.faa.fetch import FetchService
from app.faa.http_client import HttpClient, HttpResponse
from app.faa.models import CandidateDocument, DiscoveryTask
from app.faa.web_enrichment import (
    deepen_search_results,
    enrichment_status,
    looks_like_hard_host,
    text_is_thin,
)
from acquisition_planner.api_registry import PROVIDERS


def test_provider_preference_research_prefers_exa():
    with patch.dict(
        os.environ,
        {
            "EXA_API_KEY": "exa-test",
            "TAVILY_API_KEY": "tvly-test",
            "FIRECRAWL_API_KEY": "fc-test",
        },
        clear=False,
    ):
        assert "exa" in available_search_providers()
        assert "firecrawl" in available_search_providers()
        prefs = prefer_providers_for_document_type("research_publication")
        assert prefs[0] == "exa"
        assert select_search_provider("industry_report") == "exa"
        news = prefer_providers_for_document_type("news")
        assert news[0] == "tavily"


def test_search_api_emits_exa_url_for_research():
    with patch.dict(os.environ, {"EXA_API_KEY": "exa-test", "TAVILY_API_KEY": "tvly-test"}, clear=False):
        conn = SearchApiConnector(live_fetch=False)
        docs = conn.search(
            DiscoveryTask(
                description="Industry context",
                connector_id="search_api",
                query="HDFC Bank industry report",
                document_type="industry_report",
            )
        )
        assert docs
        assert docs[0].url.startswith("search://exa?")
        assert docs[0].metadata.get("selected_provider") == "exa"


def test_firecrawl_connector_gated_by_key():
    with patch.dict(os.environ, {"FIRECRAWL_API_KEY": ""}, clear=False):
        assert FirecrawlSearchConnector(live_fetch=False).search(
            DiscoveryTask(description="x", connector_id="firecrawl", query="q")
        ) == []
    with patch.dict(os.environ, {"FIRECRAWL_API_KEY": "fc-test"}, clear=False):
        docs = FirecrawlSearchConnector(live_fetch=False).search(
            DiscoveryTask(description="x", connector_id="firecrawl", query="bank credit growth")
        )
        assert docs and docs[0].url.startswith("search://firecrawl?")


def test_discovery_routes_research_to_exa_and_firecrawl():
    with patch.dict(
        os.environ,
        {"EXA_API_KEY": "exa-test", "FIRECRAWL_API_KEY": "fc-test"},
        clear=False,
    ):
        disco = DiscoveryService(live_fetch=False)
        tasks, _ = disco.discover("Should I buy HDFC Bank?")
        cids = {t.connector_id for t in tasks}
        assert "exa" in cids or any(t.document_type == "research_publication" for t in tasks)
        assert "firecrawl" in disco.connectors


def test_enrichment_helpers():
    assert looks_like_hard_host("https://www.nseindia.com/get-quotes/equity")
    assert text_is_thin("short")
    assert not text_is_thin("x" * 500)
    status = enrichment_status()
    assert "exa" in status["roles"]
    assert "firecrawl" in status["roles"]
    assert "browserbase" in status["roles"]


def test_deepen_search_results_uses_firecrawl(monkeypatch):
    client = HttpClient()

    def fake_enrich(client, url, prefer_browserbase=False):
        return {"markdown": "# Page\n" + ("body " * 100), "source": "firecrawl"}

    monkeypatch.setattr("app.faa.web_enrichment.firecrawl_configured", lambda: True)
    monkeypatch.setattr("app.faa.web_enrichment.enrich_url", fake_enrich)
    out = deepen_search_results(
        client,
        [{"title": "A", "url": "https://example.com/a", "snippet": "s"}],
        max_pages=2,
    )
    assert out[0]["enriched_by"] == "firecrawl"
    assert "Page" in out[0]["markdown"]


def test_fetch_search_parses_provider_from_url_and_deepens(monkeypatch):
    cache = __import__("app.faa.cache", fromlist=["DocumentCache"]).DocumentCache()
    fs = FetchService(cache=cache, live_fetch=True)

    def fake_call(provider, query):
        assert provider == "exa"
        return [{"title": "R1", "url": "https://example.com/r1", "snippet": "s1"}]

    monkeypatch.setattr(fs, "_call_search_provider", fake_call)
    monkeypatch.setattr(
        "app.faa.fetch.deepen_search_results",
        lambda client, results, max_pages=3: [
            {**results[0], "markdown": "# Enriched\n" + ("x" * 200), "enriched_by": "firecrawl"}
        ],
    )
    doc = fs._fetch_search(
        CandidateDocument(
            title="Exa: q",
            url="search://exa?q=hdfc",
            connector_id="exa",
            document_type="research_publication",
            metadata={"providers_available": ["exa"], "query": "hdfc bank research", "selected_provider": "exa"},
        )
    )
    assert doc.live_fetch is True
    assert "enriched_by: firecrawl" in (doc.content_text or "")
    assert doc.metadata.get("pages_enriched") == 1


def test_iape_registry_lists_new_providers():
    for pid in ("exa", "firecrawl", "browserbase", "tavily"):
        assert pid in PROVIDERS
        assert PROVIDERS[pid].get("env_key")
