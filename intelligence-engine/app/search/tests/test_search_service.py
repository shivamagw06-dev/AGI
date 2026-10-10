from app.search.service import ExternalSearchProvider, SearchProvider, SearchService, WebEvidenceStore
from app.tools.executor import ToolExecutionContext, build_core_read_executor

import asyncio


class FakeProvider(SearchProvider):
    provider_id = "fake"

    def __init__(self, rows=None, available=True, fails=False):
        self.rows = rows or []
        self.is_available = available
        self.fails = fails
        self.calls = []

    def available(self):
        return self.is_available

    def search(self, query, **kwargs):
        self.calls.append((query, kwargs))
        if self.fails:
            from app.search.service import SearchUnavailable
            raise SearchUnavailable("failed")
        return self.rows


def test_ranks_primary_sources_and_keeps_evidence_untrusted():
    provider = FakeProvider([
        {"title": "Commentary", "url": "https://example.com/a", "snippet": "x"},
        {"title": "RBI", "url": "https://www.rbi.org.in/report", "snippet": "official"},
    ])
    store = WebEvidenceStore()
    result = SearchService(provider, store).search_web("policy rate")
    assert result["trust_status"] == "external_evidence_unvalidated"
    assert result["results"][0]["title"] == "RBI"
    assert result["results"][0]["primary_source"] is True
    assert len(store.records()) == 1


def test_rejects_local_and_credentialed_urls():
    provider = FakeProvider([
        {"title": "Local", "url": "http://127.0.0.1/private", "snippet": "x"},
        {"title": "Creds", "url": "https://user:pass@example.com", "snippet": "x"},
        {"title": "Valid", "url": "https://example.com/public", "snippet": "x"},
    ])
    result = SearchService(provider).search_web("query")
    assert [item["title"] for item in result["results"]] == ["Valid"]


def test_external_router_fails_over_and_prefers_tavily_for_news():
    exa = FakeProvider(available=True, fails=True); exa.provider_id = "exa"
    tavily = FakeProvider([{"url": "https://reuters.com/a"}]); tavily.provider_id = "tavily"
    router = ExternalSearchProvider([exa, tavily])
    rows = router.search("latest", topic="news", max_results=3)
    assert rows[0]["provider"] == "tavily"
    assert not exa.calls


def test_governed_executor_binds_web_and_news_search():
    provider = FakeProvider([{"title": "RBI", "url": "https://rbi.org.in/a", "snippet": "official"}])
    executor = build_core_read_executor(search=SearchService(provider))
    assert executor.bound_tools == ["SEARCH_NEWS", "SEARCH_WEB"]
    response = asyncio.run(executor.execute("SEARCH_WEB", {"query": "inflation"}, ToolExecutionContext()))
    assert response["results"][0]["primary_source"] is True


def test_evidence_store_is_bounded():
    store = WebEvidenceStore(max_records=2)
    service = SearchService(FakeProvider([{"url": "https://example.com"}]), store)
    service.search_web("one"); service.search_web("two"); service.search_web("three")
    assert [item["query"] for item in store.records()] == ["two", "three"]
