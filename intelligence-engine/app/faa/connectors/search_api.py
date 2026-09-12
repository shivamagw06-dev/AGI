"""Public search API connectors — Exa / Tavily / Firecrawl / SerpAPI / Bing / Google CSE.

Strategic roles:
  • Exa        — semantic research / industry / publications (preferred for research)
  • Tavily     — general + news web search
  • Firecrawl  — deep search that returns page-ready content (when configured)
  • Others     — fallback coverage

Discovery-only adapters. Actual provider calls run in FetchService when live.
"""

from __future__ import annotations

import os
from typing import Any
from urllib.parse import quote_plus

from app.faa.connectors.base import AcquisitionConnector
from app.faa.models import CandidateDocument, DiscoveryTask
from app.faa.provider_flags import provider_enabled

# Preference order by document class (first configured wins).
_RESEARCH_PREF = ("exa", "firecrawl", "tavily", "playwright", "serpapi", "bing", "google_cse")
_NEWS_PREF = ("tavily", "exa", "firecrawl", "playwright", "serpapi", "bing", "google_cse")
_GENERAL_PREF = ("exa", "tavily", "firecrawl", "playwright", "serpapi", "bing", "google_cse")


def _playwright_search_ready() -> bool:
    raw = (os.environ.get("FAA_PLAYWRIGHT") or os.environ.get("PLAYWRIGHT") or "").strip().lower()
    if raw in {"0", "false", "no", "off"}:
        return False
    if raw in {"1", "true", "yes", "on"}:
        return True
    live = (os.environ.get("FAA_LIVE_FETCH") or "").strip().lower()
    return live in {"1", "true", "yes", "on"}


def available_search_providers() -> list[str]:
    """All configured AND enabled providers (unsorted inventory).

    A provider is only used when it has a key AND its FAA_<NAME>_ENABLED
    flag isn't explicitly false — this lets a provider be hard-disabled
    (e.g. lapsed billing) without needing to remove its API key.
    """
    out: list[str] = []
    if provider_enabled("exa") and (os.environ.get("EXA_API_KEY") or "").strip():
        out.append("exa")
    if provider_enabled("tavily") and (os.environ.get("TAVILY_API_KEY") or "").strip():
        out.append("tavily")
    if provider_enabled("firecrawl") and (os.environ.get("FIRECRAWL_API_KEY") or "").strip():
        out.append("firecrawl")
    if provider_enabled("playwright") and _playwright_search_ready():
        out.append("playwright")
    if provider_enabled("serpapi") and (
        os.environ.get("SERPAPI_API_KEY") or os.environ.get("SERPAPI_KEY") or ""
    ).strip():
        out.append("serpapi")
    if provider_enabled("bing") and (os.environ.get("BING_SEARCH_API_KEY") or "").strip():
        out.append("bing")
    if (
        provider_enabled("google_cse")
        and (os.environ.get("GOOGLE_CSE_ID") or "").strip()
        and (os.environ.get("GOOGLE_CSE_API_KEY") or "").strip()
    ):
        out.append("google_cse")
    return out


def prefer_providers_for_document_type(document_type: str | None) -> list[str]:
    """Return configured providers ordered for the document class."""
    dt = (document_type or "general_web").lower()
    if dt in {"industry_report", "research_publication", "fred", "imf", "world_bank", "transcript"}:
        order = _RESEARCH_PREF
    elif dt in {"news", "press_release"}:
        order = _NEWS_PREF
    else:
        order = _GENERAL_PREF
    available = set(available_search_providers())
    return [p for p in order if p in available]


def select_search_provider(document_type: str | None = None) -> str | None:
    prefs = prefer_providers_for_document_type(document_type)
    return prefs[0] if prefs else None


class SearchApiConnector(AcquisitionConnector):
    connector_id = "search_api"
    name = "Public Search APIs"
    tier = 6
    max_per_minute = 20
    document_types = ["general_web", "news", "industry_report", "research_publication"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        providers = prefer_providers_for_document_type(task.document_type)
        q = task.query or task.description
        if not providers:
            return [
                CandidateDocument(
                    title=f"Search deferred (no API key): {q}",
                    url=f"search://unconfigured?q={quote_plus(q)}",
                    connector_id=self.connector_id,
                    document_type=task.document_type or "general_web",
                    company=task.company,
                    symbol=task.symbol,
                    organisation="search_api",
                    discovery_task_id=task.task_id,
                    metadata={"providers_available": [], "deferred": True, "authority": 2},
                )
            ]
        provider = providers[0]
        return [
            CandidateDocument(
                title=f"Search ({provider}): {q}",
                url=f"search://{provider}?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation=provider,
                discovery_task_id=task.task_id,
                metadata={
                    "providers_available": providers,
                    "selected_provider": provider,
                    "query": q,
                    "authority": 4,
                    "strategy": "research_first" if provider == "exa" else "coverage",
                },
            )
        ]

    def health(self) -> dict[str, Any]:
        base = super().health()
        base["providers_available"] = available_search_providers()
        base["research_preference"] = prefer_providers_for_document_type("research_publication")
        base["news_preference"] = prefer_providers_for_document_type("news")
        return base


class TavilyConnector(SearchApiConnector):
    connector_id = "tavily"
    name = "Tavily Search"

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if "tavily" not in available_search_providers():
            return []
        q = task.query or task.description
        return [
            CandidateDocument(
                title=f"Tavily: {q}",
                url=f"search://tavily?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation="tavily",
                discovery_task_id=task.task_id,
                metadata={"providers_available": ["tavily"], "selected_provider": "tavily", "query": q, "authority": 4},
            )
        ]


class ExaConnector(SearchApiConnector):
    connector_id = "exa"
    name = "Exa Neural Search"

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if "exa" not in available_search_providers():
            return []
        q = task.query or task.description
        return [
            CandidateDocument(
                title=f"Exa: {q}",
                url=f"search://exa?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation="exa",
                discovery_task_id=task.task_id,
                metadata={
                    "providers_available": ["exa"],
                    "selected_provider": "exa",
                    "query": q,
                    "authority": 5,
                    "strategy": "semantic_research",
                },
            )
        ]


class FirecrawlSearchConnector(SearchApiConnector):
    """Firecrawl as a search provider — deep results often include page markdown."""

    connector_id = "firecrawl"
    name = "Firecrawl Search"
    document_types = ["general_web", "industry_report", "research_publication", "news"]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if "firecrawl" not in available_search_providers():
            return []
        q = task.query or task.description
        return [
            CandidateDocument(
                title=f"Firecrawl: {q}",
                url=f"search://firecrawl?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation="firecrawl",
                discovery_task_id=task.task_id,
                metadata={
                    "providers_available": ["firecrawl"],
                    "selected_provider": "firecrawl",
                    "query": q,
                    "authority": 4,
                    "strategy": "deep_page_search",
                },
            )
        ]


class PlaywrightSearchConnector(SearchApiConnector):
    """Playwright free web search (DuckDuckGo HTML) + JS page fetch capability."""

    connector_id = "playwright"
    name = "Playwright Web Search"
    document_types = [
        "general_web",
        "industry_report",
        "research_publication",
        "news",
        "investor_relations",
        "html",
    ]

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if "playwright" not in available_search_providers():
            return []
        q = task.query or task.description
        return [
            CandidateDocument(
                title=f"Playwright: {q}",
                url=f"search://playwright?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation="playwright",
                discovery_task_id=task.task_id,
                metadata={
                    "providers_available": ["playwright"],
                    "selected_provider": "playwright",
                    "query": q,
                    "authority": 3,
                    "strategy": "headless_web_search",
                },
            )
        ]

    def fetch(self, candidate, client):  # type: ignore[no-untyped-def]
        """JS-render non-search URLs assigned to this connector."""
        url = (candidate.url or "").strip()
        if not url or url.startswith("search://"):
            return None
        from app.faa.models import FetchedDocument, sha256_text, utc_now
        from app.faa.playwright_browser import fetch_page

        page = fetch_page(url)
        if not page or not page.get("markdown"):
            return None
        text = str(page["markdown"])
        return FetchedDocument(
            candidate_id=candidate.candidate_id,
            title=page.get("title") or candidate.title,
            url=str(page.get("url") or url),
            connector_id=self.connector_id,
            document_type=candidate.document_type,
            company=candidate.company,
            symbol=candidate.symbol,
            organisation=candidate.organisation or "playwright",
            published_at=candidate.published_at or utc_now().date().isoformat(),
            content_type="text/plain",
            content_text=text[:200_000],
            content_bytes_len=len(text.encode("utf-8")),
            checksum=sha256_text(text),
            live_fetch=True,
            metadata={
                "enriched_by": "playwright",
                "pdf_links": page.get("pdf_links") or [],
                "authority": (candidate.metadata or {}).get("authority"),
            },
        )


class SerpApiConnector(SearchApiConnector):
    connector_id = "serpapi"
    name = "SerpAPI"

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if "serpapi" not in available_search_providers():
            return []
        q = task.query or task.description
        return [
            CandidateDocument(
                title=f"SerpAPI: {q}",
                url=f"search://serpapi?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation="serpapi",
                discovery_task_id=task.task_id,
                metadata={"providers_available": ["serpapi"], "selected_provider": "serpapi", "query": q, "authority": 4},
            )
        ]


class GoogleCseConnector(SearchApiConnector):
    connector_id = "google_cse"
    name = "Google Custom Search"

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if "google_cse" not in available_search_providers():
            return []
        q = task.query or task.description
        return [
            CandidateDocument(
                title=f"Google CSE: {q}",
                url=f"search://google_cse?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation="google_cse",
                discovery_task_id=task.task_id,
                metadata={"providers_available": ["google_cse"], "selected_provider": "google_cse", "query": q, "authority": 4},
            )
        ]


class BingConnector(SearchApiConnector):
    connector_id = "bing"
    name = "Bing Search API"

    def search(self, task: DiscoveryTask) -> list[CandidateDocument]:
        if "bing" not in available_search_providers():
            return []
        q = task.query or task.description
        return [
            CandidateDocument(
                title=f"Bing: {q}",
                url=f"search://bing?q={quote_plus(q)}",
                connector_id=self.connector_id,
                document_type=task.document_type or "general_web",
                company=task.company,
                symbol=task.symbol,
                organisation="bing",
                discovery_task_id=task.task_id,
                metadata={"providers_available": ["bing"], "selected_provider": "bing", "query": q, "authority": 4},
            )
        ]
