"""Soft-fail execution of freshness tools planned by Ask AGI."""

from __future__ import annotations

import time
from typing import Any

from app.search import SearchService
from app.tools.executor import ToolExecutionContext, ToolExecutionError, build_core_read_executor


def run_external_research(question: str, tool_plan: dict[str, Any] | None) -> dict[str, Any]:
    started = time.time()
    plan = tool_plan or {}
    names = [str(item.get("name") or "") for item in plan.get("tools") or []]
    requested = [name for name in names if name in {"SEARCH_WEB", "SEARCH_NEWS"}]
    if not requested:
        return {"stage": "external_research", "status": "not_required", "results": [], "trace": []}

    budgets = plan.get("budgets") or {}
    context = ToolExecutionContext(
        max_searches=int(budgets.get("max_searches") or 5),
        max_documents=int(budgets.get("max_documents") or 20),
        max_runtime_seconds=float(budgets.get("max_runtime_seconds") or 30),
    )
    service = SearchService()
    if not service.provider.available():
        return {
            "stage": "external_research",
            "status": "unconfigured",
            "reason": "no_search_provider_key",
            "results": [],
            "trace": [],
            "duration_ms": int((time.time() - started) * 1000),
        }
    executor = build_core_read_executor(search=service)
    outputs: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    for name in requested:
        payload = {"query": question, "max_results": 5}
        try:
            outputs.append({"tool": name, "evidence": executor.execute_sync(name, payload, context)})
        except ToolExecutionError as exc:
            errors.append({"tool": name, "code": exc.code})
    return {
        "stage": "external_research",
        "status": "executed" if outputs else "soft_failed",
        "results": outputs,
        "errors": errors,
        "trace": context.trace,
        "trust_status": "external_evidence_unvalidated",
        "duration_ms": int((time.time() - started) * 1000),
    }
