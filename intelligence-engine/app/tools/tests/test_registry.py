from __future__ import annotations

import pytest

from app.tools.registry import ToolValidationError, get_tool, list_tools, plan_tools, validate_tool_input


def test_registry_exposes_governed_permissions():
    names = {tool["name"] for tool in list_tools()}
    assert {"SEARCH_RESEARCH", "SEARCH_WEB", "GET_FINANCIALS", "CALCULATE", "PROPOSE_KNOWLEDGE"} <= names
    assert get_tool("APPROVE_KNOWLEDGE").permission == "controlled_write"
    assert get_tool("PROPOSE_KNOWLEDGE").permission == "propose"


def test_tool_input_validation_rejects_unknown_and_oversized_arguments():
    assert validate_tool_input("SEARCH_RESEARCH", {"query": "Airtel tariff", "limit": 5})["limit"] == 5
    with pytest.raises(ToolValidationError, match="unknown_tool_arguments"):
        validate_tool_input("SEARCH_RESEARCH", {"query": "Airtel", "sql": "select *"})
    with pytest.raises(ToolValidationError, match="argument_above_limit"):
        validate_tool_input("SEARCH_WEB", {"query": "rates", "max_results": 100})


def test_current_causal_question_gets_freshness_and_reasoning_tools():
    plan = plan_tools("How does the latest RBI rate cut affect bank margins?", ticker_hint="HDFCBANK")
    names = {tool["name"] for tool in plan["tools"]}
    assert {"SEARCH_RESEARCH", "SEARCH_WEB", "GET_LATEST_EVENTS", "GET_COMPANY", "GET_FINANCIALS", "GET_CAUSAL_GRAPH", "CALCULATE"} <= names
    assert plan["controlled_writes_allowed"] is False
    assert plan["budgets"]["max_searches"] == 5
