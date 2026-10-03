"""Institutional retrieval — CompanyMemory + Graph + Latest Delta + CID."""

from __future__ import annotations

from typing import Any

from investment_knowledge_graph.build import build_company_graph, ownership_concentration


def retrieve_composite(
    ticker: str,
    *,
    include_cid: bool = True,
    compile_delta: bool = True,
    persist_delta: bool = False,
) -> dict[str, Any]:
    """
    Instead of 'give me TCS', retrieve composite institutional context.

    Decision Engine still consumes CID only — this package prepares enrichment.
    """
    from company_memory.resolve import resolve_ticker

    entity = resolve_ticker(ticker)
    memory = None
    delta = None

    if compile_delta:
        try:
            from knowledge_delta_engine.production import compile_incremental

            mem_pack = compile_incremental(entity, persist=persist_delta)
            memory = mem_pack
            delta = mem_pack.get("memory_delta")
        except Exception as exc:  # noqa: BLE001
            delta = {"error": str(exc)[:160]}
    if memory is None:
        try:
            from knowledge_delta_engine.versioning import load_current

            memory = load_current(entity)
        except Exception:
            memory = None
    if memory is None:
        try:
            from company_memory.production import compile as memory_compile

            memory = memory_compile(entity, persist=False, skip_live=False)
        except Exception as exc:  # noqa: BLE001
            memory = {"ok": False, "error": str(exc)[:160]}

    graph = build_company_graph(entity, memory=memory if isinstance(memory, dict) else None)
    concentration = ownership_concentration(graph)

    cid = None
    if include_cid:
        try:
            from cid.production import get_or_build

            cid = get_or_build(entity)
        except Exception as exc:  # noqa: BLE001
            cid = {"error": str(exc)[:160]}

    return {
        "entity": entity,
        "retrieval": "company_memory+knowledge_graph+latest_delta+cid",
        "company_memory": {
            "ok": bool((memory or {}).get("ok")),
            "version": (memory or {}).get("memory_version"),
            "coverage": (memory or {}).get("coverage"),
            "financial_history": (memory or {}).get("financial_history"),
            "ownership_history": (memory or {}).get("ownership_history"),
            "valuation_history": (memory or {}).get("valuation_history"),
            "sector_history": {
                "sector_key": ((memory or {}).get("sector_history") or {}).get("sector_key"),
                "kpi_keys": ((memory or {}).get("sector_history") or {}).get("kpi_keys"),
            },
            "price_intelligence": (memory or {}).get("price_intelligence"),
            "corporate_history": (memory or {}).get("corporate_history"),
        },
        "knowledge_graph": graph,
        "ownership_concentration": concentration,
        "latest_delta": delta,
        "cid": {
            "attached": bool(cid and cid.get("ticker")),
            "coverage_score": (cid or {}).get("coverage_score"),
            "has_memory": bool((cid or {}).get("company_memory") or (cid or {}).get("memory")),
            "has_graph": bool((cid or {}).get("investment_knowledge_graph")),
        }
        if include_cid
        else None,
        "modifies_decision_engine": False,
        "consumes_decision_engine": False,
        "answer_policy": "composite_memory_for_research_not_recommendation",
    }
