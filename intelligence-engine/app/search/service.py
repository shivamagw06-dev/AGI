"""Provider-neutral search and untrusted web-evidence boundary for Ask AGI."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import ipaddress
import json
import os
import threading
from typing import Any
from urllib.parse import urlparse

from app.faa.http_client import HttpClient
from app.faa.provider_flags import provider_enabled


class SearchUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str
    provider: str
    published_at: str | None = None
    source_tier: str = "web"
    authority_score: int = 3
    primary_source: bool = False

    def public(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SearchResponse:
    query: str
    provider: str
    results: list[SearchResult]
    searched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    trust_status: str = "external_evidence_unvalidated"

    def public(self) -> dict[str, Any]:
        return {
            "query": self.query,
            "provider": self.provider,
            "searched_at": self.searched_at,
            "trust_status": self.trust_status,
            "results": [item.public() for item in self.results],
        }


class SearchProvider(ABC):
    provider_id = "base"

    @abstractmethod
    def available(self) -> bool:
        pass

    @abstractmethod
    def search(
        self,
        query: str,
        *,
        max_results: int = 5,
        domains: list[str] | None = None,
        topic: str = "general",
        date_range: str | None = None,
    ) -> list[dict[str, Any]]:
        pass


class TavilySearchProvider(SearchProvider):
    provider_id = "tavily"

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient(timeout=12, max_retries=2)

    def available(self) -> bool:
        return provider_enabled("tavily") and bool((os.environ.get("TAVILY_API_KEY") or "").strip())

    def search(self, query: str, *, max_results: int = 5, domains=None, topic="general", date_range=None):
        key = (os.environ.get("TAVILY_API_KEY") or "").strip()
        if not key:
            raise SearchUnavailable("search_provider_unconfigured")
        payload: dict[str, Any] = {
            "api_key": key,
            "query": query,
            "max_results": max_results,
            "include_answer": False,
            "topic": "news" if topic == "news" else "general",
        }
        if domains:
            payload["include_domains"] = domains
        if topic == "news" and date_range:
            payload["days"] = _date_range_days(date_range)
        response = self.client.post_json("https://api.tavily.com/search", payload, connector_id="ask_search_tavily")
        if not response.ok:
            raise SearchUnavailable(f"search_provider_error:{response.status_code or 'network'}")
        data = json.loads(response.text or "{}")
        return [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("content"),
                "published_at": item.get("published_date"),
            }
            for item in data.get("results") or []
            if isinstance(item, dict)
        ]


class ExaSearchProvider(SearchProvider):
    provider_id = "exa"

    def __init__(self, client: HttpClient | None = None) -> None:
        self.client = client or HttpClient(timeout=12, max_retries=2)

    def available(self) -> bool:
        return provider_enabled("exa") and bool((os.environ.get("EXA_API_KEY") or "").strip())

    def search(self, query: str, *, max_results: int = 5, domains=None, topic="general", date_range=None):
        key = (os.environ.get("EXA_API_KEY") or "").strip()
        if not key:
            raise SearchUnavailable("search_provider_unconfigured")
        payload: dict[str, Any] = {
            "query": query,
            "numResults": max_results,
            "type": "auto",
            "contents": {"text": {"maxCharacters": 1_200}},
        }
        if domains:
            payload["includeDomains"] = domains
        response = self.client.post_json(
            "https://api.exa.ai/search",
            payload,
            connector_id="ask_search_exa",
            headers={"x-api-key": key},
        )
        if not response.ok:
            raise SearchUnavailable(f"search_provider_error:{response.status_code or 'network'}")
        data = json.loads(response.text or "{}")
        return [
            {
                "title": item.get("title"),
                "url": item.get("url"),
                "snippet": item.get("text") or _first(item.get("highlights")),
                "published_at": item.get("publishedDate"),
            }
            for item in data.get("results") or []
            if isinstance(item, dict)
        ]


class ExternalSearchProvider(SearchProvider):
    """Provider router; adding AGI's own index later requires no Ask changes."""

    provider_id = "external_router"

    def __init__(self, providers: list[SearchProvider] | None = None) -> None:
        self.providers = providers or [ExaSearchProvider(), TavilySearchProvider()]

    def available(self) -> bool:
        return any(provider.available() for provider in self.providers)

    def search(self, query: str, **kwargs: Any) -> list[dict[str, Any]]:
        errors: list[str] = []
        providers = list(self.providers)
        if kwargs.get("topic") == "news":
            providers.sort(key=lambda item: item.provider_id != "tavily")
        for provider in providers:
            if not provider.available():
                continue
            try:
                rows = provider.search(query, **kwargs)
                return [{**row, "provider": provider.provider_id} for row in rows]
            except SearchUnavailable as exc:
                errors.append(str(exc))
        raise SearchUnavailable(errors[-1] if errors else "search_provider_unconfigured")


class WebEvidenceStore:
    """Bounded request-scoped evidence storage; never promotes knowledge."""

    def __init__(self, max_records: int = 50) -> None:
        self.max_records = max(1, min(max_records, 200))
        self._records: list[dict[str, Any]] = []
        self._lock = threading.Lock()

    def add(self, response: SearchResponse) -> None:
        with self._lock:
            self._records.append(response.public())
            self._records = self._records[-self.max_records :]

    def records(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._records)


class SearchService:
    def __init__(self, provider: SearchProvider | None = None, store: WebEvidenceStore | None = None) -> None:
        self.provider = provider or ExternalSearchProvider()
        self.store = store or WebEvidenceStore()

    def search_web(self, query: str, *, date_range=None, domains=None, max_results=5) -> dict[str, Any]:
        return self._search(query, max_results=max_results, domains=domains, topic="general", date_range=date_range)

    def search_news(self, query: str, *, date_from=None, max_results=5) -> dict[str, Any]:
        return self._search(query, max_results=max_results, domains=None, topic="news", date_range=date_from)

    def _search(self, query: str, *, max_results: int, domains, topic: str, date_range) -> dict[str, Any]:
        raw = self.provider.search(
            query,
            max_results=max(1, min(int(max_results), 10)),
            domains=_clean_domains(domains),
            topic=topic,
            date_range=date_range,
        )
        results: list[SearchResult] = []
        for item in raw:
            url = _safe_public_url(item.get("url"))
            if not url:
                continue
            tier, authority, primary = _classify_source(url)
            results.append(
                SearchResult(
                    title=str(item.get("title") or "Untitled source")[:300],
                    url=url,
                    snippet=str(item.get("snippet") or "")[:2_000],
                    provider=str(item.get("provider") or self.provider.provider_id),
                    published_at=item.get("published_at"),
                    source_tier=tier,
                    authority_score=authority,
                    primary_source=primary,
                )
            )
        results.sort(key=lambda item: (item.authority_score, bool(item.published_at)), reverse=True)
        response = SearchResponse(query=query, provider=self.provider.provider_id, results=results)
        self.store.add(response)
        return response.public()


_PRIMARY_DOMAINS = {
    "rbi.org.in", "sebi.gov.in", "nseindia.com", "bseindia.com", "gov.in",
    "mospi.gov.in", "commerce.gov.in", "pib.gov.in", "mca.gov.in",
}
_HIGH_AUTHORITY = {"reuters.com", "imf.org", "worldbank.org", "bis.org", "oecd.org", "ilo.org", "unctad.org"}


def _classify_source(url: str) -> tuple[str, int, bool]:
    host = (urlparse(url).hostname or "").lower()
    if any(host == domain or host.endswith(f".{domain}") for domain in _PRIMARY_DOMAINS):
        return "primary", 10, True
    if any(host == domain or host.endswith(f".{domain}") for domain in _HIGH_AUTHORITY):
        return "authoritative", 8, False
    return "web", 3, False


def _safe_public_url(value: Any) -> str | None:
    try:
        parsed = urlparse(str(value or "").strip())
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
            return None
        try:
            address = ipaddress.ip_address(parsed.hostname)
            if not address.is_global:
                return None
        except ValueError:
            if parsed.hostname.lower() in {"localhost", "localhost.localdomain"}:
                return None
        return parsed.geturl()
    except Exception:
        return None


def _clean_domains(values: list[str] | None) -> list[str] | None:
    clean = []
    for value in values or []:
        domain = str(value).strip().lower().removeprefix("https://").removeprefix("http://").split("/")[0]
        if domain and len(domain) <= 253 and all(char.isalnum() or char in ".-" for char in domain):
            clean.append(domain)
    return clean[:12] or None


def _date_range_days(value: str) -> int:
    digits = "".join(char for char in str(value or "") if char.isdigit())
    return max(1, min(int(digits or "30"), 365))


def _first(value: Any) -> str:
    return str(value[0]) if isinstance(value, list) and value else ""
