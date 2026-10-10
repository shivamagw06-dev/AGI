"""Playwright integration for FAA web search + JS page fetch."""

from __future__ import annotations

import os
from unittest.mock import patch

from app.faa.connectors.company_ir import CompanyIrConnector
from app.faa.connectors.search_api import (
    PlaywrightSearchConnector,
    available_search_providers,
    prefer_providers_for_document_type,
)
from app.faa.discovery import DiscoveryService
from app.faa.http_client import HttpClient
from app.faa.models import CandidateDocument, DiscoveryTask
from app.faa.web_enrichment import enrich_url, enrichment_status
from acquisition_planner.api_registry import PROVIDERS


def test_playwright_listed_when_enabled():
    with patch.dict(os.environ, {"FAA_PLAYWRIGHT": "true"}, clear=False):
        assert "playwright" in available_search_providers()
        prefs = prefer_providers_for_document_type("research_publication")
        assert "playwright" in prefs


def test_playwright_connector_emits_search_url():
    with patch.dict(os.environ, {"FAA_PLAYWRIGHT": "true"}, clear=False):
        docs = PlaywrightSearchConnector(live_fetch=True).search(
            DiscoveryTask(
                description="Industry context",
                connector_id="playwright",
                query="HDFC Bank shareholding pattern",
                document_type="industry_report",
            )
        )
        assert docs
        assert docs[0].url.startswith("search://playwright?")
        assert docs[0].metadata.get("selected_provider") == "playwright"


def test_discovery_includes_playwright_connector():
    disco = DiscoveryService(live_fetch=False)
    assert "playwright" in disco.connectors


def test_enrich_url_hard_host_prefers_playwright(monkeypatch):
    monkeypatch.setenv("FAA_PLAYWRIGHT", "true")
    monkeypatch.setattr("app.faa.web_enrichment.playwright_available", lambda: True)
    monkeypatch.setattr(
        "app.faa.web_enrichment.playwright_fetch_page",
        lambda url: {"markdown": "Promoter holding 50% " + ("x" * 400), "source": "playwright", "title": "SHP"},
    )
    monkeypatch.setattr("app.faa.web_enrichment.firecrawl_configured", lambda: True)
    monkeypatch.setattr(
        "app.faa.web_enrichment.firecrawl_scrape",
        lambda client, url: {"markdown": "should not win " + ("y" * 400), "source": "firecrawl"},
    )
    page = enrich_url(HttpClient(), "https://www.nseindia.com/companies-listing/corporate-filings")
    assert page and page["source"] == "playwright"


def test_company_ir_fetch_uses_playwright(monkeypatch):
    monkeypatch.setenv("FAA_PLAYWRIGHT", "true")
    monkeypatch.setattr(
        "app.faa.playwright_browser.fetch_page",
        lambda url: {
            "markdown": "Annual report hub " + ("z" * 400),
            "title": "IR",
            "source": "playwright",
            "pdf_links": ["https://example.com/ar.pdf"],
            "url": url,
        },
    )
    conn = CompanyIrConnector(live_fetch=True)
    doc = conn.fetch(
        CandidateDocument(
            title="IR",
            url="https://www.ril.com/investors",
            connector_id="company_ir",
            document_type="investor_relations",
        ),
        HttpClient(),
    )
    assert doc is not None
    assert doc.metadata.get("enriched_by") == "playwright"
    assert "ar.pdf" in str(doc.metadata.get("pdf_links"))


def test_fetch_search_provider_playwright(monkeypatch):
    from app.faa.cache import DocumentCache
    from app.faa.fetch import FetchService

    monkeypatch.setenv("FAA_PLAYWRIGHT", "true")
    monkeypatch.setattr(
        "app.faa.playwright_browser.web_search",
        lambda query, limit=5: [{"title": "Hit", "url": "https://example.com/h", "snippet": "s"}],
    )
    monkeypatch.setattr(
        "app.faa.fetch.deepen_search_results",
        lambda client, results, max_pages=3: results,
    )
    fs = FetchService(cache=DocumentCache(), live_fetch=True)
    out = fs._call_search_provider("playwright", "reliance investors")
    assert out and out[0]["url"].startswith("https://")


def test_enrichment_status_includes_playwright_role():
    status = enrichment_status()
    assert "playwright" in status["roles"]
    assert "playwright" in PROVIDERS
    assert PROVIDERS["playwright"]["env_key"] == "FAA_PLAYWRIGHT"


def test_ensure_chromium_defaults_auto_install_off(monkeypatch):
    from app.faa import playwright_browser as pb

    monkeypatch.setenv("FAA_PLAYWRIGHT", "true")
    monkeypatch.delenv("FAA_PLAYWRIGHT_AUTO_INSTALL", raising=False)
    pb._INSTALL_ATTEMPTED = False
    pb._READY = None
    assert pb.ensure_chromium_installed() is False


def test_ensure_chromium_respects_auto_install_off(monkeypatch):
    from app.faa import playwright_browser as pb

    monkeypatch.setenv("FAA_PLAYWRIGHT", "true")
    monkeypatch.setenv("FAA_PLAYWRIGHT_AUTO_INSTALL", "false")
    pb._INSTALL_ATTEMPTED = False
    pb._READY = None
    assert pb.ensure_chromium_installed() is False


def test_playwright_status_does_not_probe_by_default(monkeypatch):
    from app.faa import playwright_browser as pb

    monkeypatch.setenv("FAA_PLAYWRIGHT", "true")
    pb._READY = None
    pb._INIT_ERROR = None
    pb._INSTALL_ATTEMPTED = False
    status = pb.playwright_status(probe=False)
    assert status["enabled"] is True
    assert status["ready"] is False
    assert status["error"] is None
    assert pb._READY is None  # health must not poison readiness


def test_unwrap_soft_slice_flattens_named_wrapper():
    from app.ui.service import _unwrap_soft_slice

    nested = {"hypothesis_engine": {"enabled": True, "version": "1.0.0"}}
    assert _unwrap_soft_slice("hypothesis_engine", nested)["enabled"] is True
    flat = {"enabled": True, "ok": 1}
    assert _unwrap_soft_slice("hypothesis_engine", flat) == flat
