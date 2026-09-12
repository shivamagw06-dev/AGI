"""P3.2 Investment Knowledge Graph — production façade."""

from __future__ import annotations

from typing import Any

from investment_knowledge_graph.build import build_company_graph, query_macro_chain, query_theme
from investment_knowledge_graph.retrieve import retrieve_composite
from investment_knowledge_graph.schema import (
    EDGE_TYPES,
    ENGINE_CODE,
    ENGINE_NAME,
    MACRO_CHAINS,
    MILESTONE,
    NODE_TYPES,
    PROGRAMME,
    SECTOR_CHAINS,
    THEME_MAP,
    VERSION,
    WORKSTREAM_ID,
)


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "engine": ENGINE_CODE,
        "engine_name": ENGINE_NAME,
        "version": VERSION,
        "workstream_id": WORKSTREAM_ID,
        "milestone": MILESTONE,
        "node_types": list(NODE_TYPES),
        "edge_types": list(EDGE_TYPES),
        "sector_chains": list(SECTOR_CHAINS.keys()),
        "themes": list(THEME_MAP.keys()),
        "macro_chains": [c["id"] for c in MACRO_CHAINS],
        "extends_ikg": True,
        "modifies_decision_engine": False,
        "decision_engine_consumes_cid_only": True,
        "issues_recommendations": False,
    }


def analyse(ticker: str, *, memory: dict[str, Any] | None = None) -> dict[str, Any]:
    graph = build_company_graph(ticker, memory=memory)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ok": bool(graph.get("n_nodes")),
        "knowledge_graph": graph,
        **graph,
    }


def theme(name: str) -> dict[str, Any]:
    return query_theme(name)


def macro(chain_id: str | None = None) -> dict[str, Any]:
    return query_macro_chain(chain_id)


def retrieve(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = retrieve_composite(ticker, **kwargs)
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        **pack,
    }


def package_for_ask_agi(ticker: str, **kwargs: Any) -> dict[str, Any]:
    pack = retrieve_composite(ticker, include_cid=False, compile_delta=True, persist_delta=False, **kwargs)
    g = pack.get("knowledge_graph") or {}
    return {
        "enabled": True,
        "engine": ENGINE_CODE,
        "version": VERSION,
        "ticker": pack.get("entity"),
        "peers": g.get("peers"),
        "themes": g.get("themes"),
        "sector_chain": g.get("sector_chain"),
        "n_nodes": g.get("n_nodes"),
        "n_edges": g.get("n_edges"),
        "latest_delta_summary": ((pack.get("latest_delta") or {}).get("summary")),
        "memory_version": ((pack.get("company_memory") or {}).get("version")),
        "recommendation_policy": "graph_context_no_buy_sell",
        "modifies_decision_engine": False,
    }
