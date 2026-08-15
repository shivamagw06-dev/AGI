import asyncio
import time

import pytest

from app.tools.executor import (
    GovernedToolExecutor,
    ToolExecutionContext,
    ToolExecutionError,
    build_core_read_executor,
)


def run(coro):
    return asyncio.run(coro)


def test_executes_explicit_read_handler_and_sanitizes_trace():
    executor = GovernedToolExecutor({"GET_COMPANY": lambda company_id, fields=None: {"id": company_id}})
    context = ToolExecutionContext()
    result = run(executor.execute("GET_COMPANY", {"company_id": "ZEN"}, context))
    assert result == {"id": "ZEN"}
    assert context.trace[0]["status"] == "success"
    assert context.trace[0]["input_keys"] == ["company_id"]
    assert "payload" not in context.trace[0]


def test_sync_executor_uses_same_governance_boundary():
    executor = GovernedToolExecutor({"GET_COMPANY": lambda company_id, fields=None: {"id": company_id}})
    context = ToolExecutionContext()
    assert executor.execute_sync("GET_COMPANY", {"company_id": "ZEN"}, context) == {"id": "ZEN"}
    assert context.trace[0]["status"] == "success"


def test_rejects_unknown_arguments_before_handler():
    executor = GovernedToolExecutor({"GET_COMPANY": lambda **_: {}})
    context = ToolExecutionContext()
    with pytest.raises(ToolExecutionError, match="tool_input_invalid:unknown_tool_arguments:sql"):
        run(executor.execute("GET_COMPANY", {"company_id": "ZEN", "sql": "drop table x"}, context))
    assert context.trace[0]["status"] == "error"


def test_blocks_write_and_proposal_permissions():
    executor = GovernedToolExecutor({"PROPOSE_KNOWLEDGE": lambda **_: {}, "APPROVE_KNOWLEDGE": lambda **_: {}})
    with pytest.raises(ToolExecutionError, match="proposal_permission_denied"):
        run(executor.execute("PROPOSE_KNOWLEDGE", {"document_id": "d1", "payload": {"x": 1}}, ToolExecutionContext()))
    with pytest.raises(ToolExecutionError, match="controlled_write_permission_denied"):
        run(executor.execute("APPROVE_KNOWLEDGE", {"candidate_id": "c1", "review_reason": "reviewed"}, ToolExecutionContext()))


def test_enforces_per_tool_call_budget():
    executor = GovernedToolExecutor({"GET_DOCUMENT": lambda document_id: {"id": document_id}})
    context = ToolExecutionContext()
    run(executor.execute("GET_DOCUMENT", {"document_id": "d1"}, context))
    with pytest.raises(ToolExecutionError, match="tool_call_budget_exceeded"):
        run(executor.execute("GET_DOCUMENT", {"document_id": "d2"}, context))


def test_enforces_runtime_budget_and_unbound_tools():
    context = ToolExecutionContext(max_runtime_seconds=0, started_at=time.monotonic() - 1)
    with pytest.raises(ToolExecutionError, match="runtime_budget_exceeded"):
        run(GovernedToolExecutor({"GET_COMPANY": lambda **_: {}}).execute("GET_COMPANY", {"company_id": "ZEN"}, context))
    with pytest.raises(ToolExecutionError, match="tool_handler_unavailable"):
        run(GovernedToolExecutor().execute("GET_COMPANY", {"company_id": "ZEN"}, ToolExecutionContext()))


def test_core_factory_binds_existing_services():
    class Kip:
        def search(self, query, **kwargs):
            return {"query": query, "filters": kwargs}

        def get_document(self, document_id):
            return {"document_id": document_id}

    executor = build_core_read_executor(kip=Kip())
    assert executor.bound_tools == [
        "CALCULATE", "GET_BANK_VALUATION", "GET_CAUSAL_RESEARCH", "GET_COMPANY_ANALYSIS",
        "GET_DOCUMENT", "GET_FINANCIAL_VALUATION", "SEARCH_RESEARCH",
    ]
    result = run(executor.execute("SEARCH_RESEARCH", {"query": "defence", "company": "ZEN"}, ToolExecutionContext()))
    assert result["filters"]["ticker"] == "ZEN"


def test_core_factory_binds_afe_calculate_by_default():
    executor = build_core_read_executor()
    result = executor.execute_sync(
        "CALCULATE",
        {"operation": "ROE", "inputs": {"pat": 100, "opening_equity": 600, "closing_equity": 650}},
        ToolExecutionContext(),
    )
    assert result["status"] == "SUCCESS"
    assert result["display_value"] == 16.0
    assert result["model_generated_formula"] is False
