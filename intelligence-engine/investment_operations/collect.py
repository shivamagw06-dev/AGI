"""Collect compiled intelligence packs — soft orchestration only, no raw APIs."""

from __future__ import annotations

from typing import Any

from investment_operations.util import resolve_ticker, soft_call


def collect_company(
    ticker: str,
    *,
    injected: dict[str, Any] | None = None,
    persist_memory: bool = False,
    include_soft_reasoning: bool = True,
) -> dict[str, Any]:
    """Gather CompanyMemory/Delta/Graph/Opportunity (+ soft engines) for one ticker."""
    if isinstance(injected, dict) and injected.get("ok") and injected.get("entity"):
        return injected

    entity = resolve_ticker(ticker)
    display = "TATAMOTORS" if entity == "TMPV" else entity
    out: dict[str, Any] = {
        "ok": False,
        "entity": entity,
        "display": display,
        "memory": None,
        "memory_delta": None,
        "knowledge_graph": None,
        "opportunity": None,
        "scenarios": None,
        "hypotheses": None,
        "contradictions": None,
        "causal": None,
        "errors": [],
    }

    # Prefer cached / versioned memory (no live rebuild unless missing)
    mem = soft_call("memory_current", _load_current_memory, entity)
    if not (mem.get("_ok") and mem.get("ok")):
        mem = soft_call("memory_incremental", _load_memory, entity, persist=persist_memory)
    if mem.get("_ok") and mem.get("ok"):
        out["memory"] = mem
        out["memory_delta"] = mem.get("memory_delta")
        out["ok"] = True
        out["display"] = mem.get("display") or display
    elif mem.get("error"):
        out["errors"].append(mem["error"])

    graph = soft_call("investment_knowledge_graph", _load_graph, entity, out.get("memory"))
    if graph.get("_ok") and graph.get("n_nodes"):
        out["knowledge_graph"] = graph

    # Opportunity from compiled memory (avoid nested recompile)
    if out.get("memory"):
        oie = soft_call(
            "opportunity_intelligence",
            _analyse_opportunity_injected,
            entity,
            out["memory"],
            out.get("knowledge_graph"),
        )
    else:
        oie = soft_call(
            "opportunity_intelligence",
            _analyse_opportunity,
            entity,
            persist_memory=persist_memory,
        )
    if oie.get("_ok") and oie.get("ok"):
        out["opportunity"] = oie
        out["ok"] = True
        out["display"] = oie.get("display") or out["display"]
    elif oie.get("error"):
        out["errors"].append(oie["error"])

    if include_soft_reasoning:
        scen = soft_call("scenario", _load_scenarios, entity)
        if scen.get("_ok"):
            out["scenarios"] = scen
        hyp = soft_call("hypothesis", _load_hypotheses, entity)
        if hyp.get("_ok"):
            out["hypotheses"] = hyp
        # Skip contradiction/causal in default ops path — expensive / query-shaped
        # Callers can request via workspace include_soft_reasoning + explicit extensions later

    return out


def collect_universe(
    universe: list[str] | tuple[str, ...] | None = None,
    *,
    injected_by_ticker: dict[str, dict[str, Any]] | None = None,
    persist_memory: bool = False,
    include_soft_reasoning: bool = False,
) -> list[dict[str, Any]]:
    from investment_operations.util import default_universe

    tickers = list(universe) if universe else list(default_universe())
    inj = injected_by_ticker or {}
    rows = []
    for t in tickers:
        key = resolve_ticker(t)
        rows.append(
            collect_company(
                t,
                injected=inj.get(t) or inj.get(key),
                persist_memory=persist_memory,
                include_soft_reasoning=include_soft_reasoning,
            )
        )
    return rows


def _load_current_memory(entity: str) -> dict[str, Any]:
    from knowledge_delta_engine.versioning import load_current

    mem = load_current(entity)
    if isinstance(mem, dict) and mem.get("ok"):
        return mem
    try:
        from company_memory.persist import load_memory

        mem2 = load_memory(entity)
        if isinstance(mem2, dict) and mem2.get("ok"):
            return mem2
    except Exception:
        pass
    return {"ok": False, "entity": entity, "error": "memory_cache_miss"}


def _analyse_opportunity(entity: str, *, persist_memory: bool = False) -> dict[str, Any]:
    from opportunity_intelligence.production import analyse

    return analyse(entity, persist_memory=persist_memory)


def _analyse_opportunity_injected(entity: str, memory: dict[str, Any], graph: dict[str, Any] | None) -> dict[str, Any]:
    from opportunity_intelligence.production import analyse

    return analyse(
        entity,
        injected_memory=memory,
        injected_graph=graph,
        compile_if_missing=False,
        persist_memory=False,
    )


def _load_memory(entity: str, *, persist: bool = False) -> dict[str, Any]:
    from knowledge_delta_engine.compile import incremental_compile

    return incremental_compile(entity, persist=persist)


def _load_graph(entity: str, memory: dict[str, Any] | None) -> dict[str, Any]:
    from investment_knowledge_graph.build import build_company_graph

    return build_company_graph(entity, memory=memory if isinstance(memory, dict) else None)


def _load_scenarios(entity: str) -> dict[str, Any]:
    from institutional_scenario_intelligence.production import company

    return company(entity)


def _load_hypotheses(entity: str) -> dict[str, Any]:
    from hypothesis_engine.production import health

    h = health()
    return {"enabled": h.get("status") == "ok", "ticker": entity, "hypotheses": []}
