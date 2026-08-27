from unittest.mock import patch

from ask_pipeline.external_research import run_external_research


def test_external_research_skips_when_not_planned():
    result = run_external_research("historical margins", {"tools": [{"name": "GET_FINANCIALS"}]})
    assert result["status"] == "not_required"


def test_external_research_reports_unconfigured_without_network_call():
    with patch.dict("os.environ", {"EXA_API_KEY": "", "TAVILY_API_KEY": ""}, clear=False):
        result = run_external_research("latest RBI policy", {"tools": [{"name": "SEARCH_WEB"}]})
    assert result["status"] == "unconfigured"
    assert result["reason"] == "no_search_provider_key"


def test_external_research_executes_governed_planned_tool():
    fake = {
        "query": "latest RBI policy",
        "provider": "fake",
        "trust_status": "external_evidence_unvalidated",
        "results": [{"title": "RBI", "url": "https://rbi.org.in/a"}],
    }
    with patch("ask_pipeline.external_research.SearchService") as service_class:
        service = service_class.return_value
        service.provider.available.return_value = True
        service.search_web.return_value = fake
        result = run_external_research(
            "latest RBI policy",
            {"tools": [{"name": "SEARCH_WEB"}], "budgets": {"max_searches": 1}},
        )
    assert result["status"] == "executed"
    assert result["results"][0]["evidence"]["trust_status"] == "external_evidence_unvalidated"
    assert result["trace"][0]["tool"] == "SEARCH_WEB"
