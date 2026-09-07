"""Exa / Firecrawl / Browserbase can be hard-disabled independent of API key
presence — e.g. lapsed billing (402 Payment Required) without needing to
remove the key from the Render dashboard.
"""

from __future__ import annotations

import os
from unittest.mock import patch

from app.faa.connectors.search_api import FirecrawlSearchConnector, available_search_providers
from app.faa.provider_flags import provider_enabled
from app.faa.web_enrichment import browserbase_configured, firecrawl_configured


def test_provider_enabled_defaults_true():
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("FAA_EXA_ENABLED", None)
        assert provider_enabled("exa") is True


def test_provider_enabled_respects_false_variants():
    for val in ("false", "0", "no", "off", "FALSE"):
        with patch.dict(os.environ, {"FAA_EXA_ENABLED": val}, clear=False):
            assert provider_enabled("exa") is False


def test_exa_excluded_when_disabled_even_with_key():
    with patch.dict(
        os.environ,
        {"EXA_API_KEY": "exa-test-key", "FAA_EXA_ENABLED": "false"},
        clear=False,
    ):
        assert "exa" not in available_search_providers()


def test_exa_included_when_key_present_and_not_disabled():
    with patch.dict(os.environ, {"EXA_API_KEY": "exa-test-key"}, clear=False):
        os.environ.pop("FAA_EXA_ENABLED", None)
        assert "exa" in available_search_providers()


def test_firecrawl_excluded_when_disabled_even_with_key():
    with patch.dict(
        os.environ,
        {"FIRECRAWL_API_KEY": "fc-test-key", "FAA_FIRECRAWL_ENABLED": "false"},
        clear=False,
    ):
        assert "firecrawl" not in available_search_providers()
        assert firecrawl_configured() is False
        docs = FirecrawlSearchConnector(live_fetch=False).search(
            __import__("app.faa.models", fromlist=["DiscoveryTask"]).DiscoveryTask(
                description="x", connector_id="firecrawl", query="q"
            )
        )
        assert docs == []


def test_browserbase_excluded_when_disabled_even_with_key():
    with patch.dict(
        os.environ,
        {"BROWSERBASE_API_KEY": "bb-test-key", "FAA_BROWSERBASE_ENABLED": "false"},
        clear=False,
    ):
        assert browserbase_configured() is False


def test_all_three_disabled_matches_render_yaml_intent():
    """Reproduces the exact render.yaml config: keys still present (as they
    are in the dashboard) but all three explicitly turned off."""
    with patch.dict(
        os.environ,
        {
            "EXA_API_KEY": "exa-test-key",
            "FIRECRAWL_API_KEY": "fc-test-key",
            "BROWSERBASE_API_KEY": "bb-test-key",
            "FAA_EXA_ENABLED": "false",
            "FAA_FIRECRAWL_ENABLED": "false",
            "FAA_BROWSERBASE_ENABLED": "false",
        },
        clear=False,
    ):
        providers = available_search_providers()
        assert "exa" not in providers
        assert "firecrawl" not in providers
        assert firecrawl_configured() is False
        assert browserbase_configured() is False


def test_tavily_playwright_unaffected_by_other_kill_switches():
    """Only exa/firecrawl/browserbase were asked to be disabled — other
    providers must keep working normally."""
    with patch.dict(
        os.environ,
        {
            "TAVILY_API_KEY": "tvly-test-key",
            "FAA_EXA_ENABLED": "false",
            "FAA_FIRECRAWL_ENABLED": "false",
            "FAA_BROWSERBASE_ENABLED": "false",
        },
        clear=False,
    ):
        assert "tavily" in available_search_providers()
