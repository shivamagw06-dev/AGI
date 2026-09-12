"""CCI-01 ↔ KG-01 bridge — soft-read only; never builds or mutates the graph."""

from __future__ import annotations

from typing import Any, Optional

from institutional_cross_company.schema import GRAPH_PACKAGE, GRAPH_SYSTEM_OF_RECORD


def soft_get_company_graph(ticker: str, *, include_inference: bool = True) -> dict[str, Any]:
    """Read KG-01 company graph. CCI must not invent nodes/edges here."""
    t = str(ticker or "").strip().upper()
    if not t:
        return {"ok": False, "available": False, "reason": "ticker required", "system": GRAPH_SYSTEM_OF_RECORD}
    try:
        from institutional_graph.production import get_company_graph

        graph = get_company_graph(t, include_paths=False, include_inference=include_inference)
        if isinstance(graph, dict):
            return {
                "ok": graph.get("ok", True) is not False and not graph.get("rejected"),
                "available": True,
                "system": GRAPH_SYSTEM_OF_RECORD,
                "package": GRAPH_PACKAGE,
                "ticker": t,
                "graph": graph,
                "node_count": len(graph.get("nodes") or graph.get("entities") or {}),
                "relationship_count": len(graph.get("relationships") or {}),
                "scope": graph.get("scope") or "single_company",
            }
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "available": False,
            "system": GRAPH_SYSTEM_OF_RECORD,
            "package": GRAPH_PACKAGE,
            "ticker": t,
            "error": str(exc),
        }
    return {"ok": False, "available": False, "system": GRAPH_SYSTEM_OF_RECORD, "ticker": t}


def soft_kg_sector(ticker: str) -> Optional[str]:
    pack = soft_get_company_graph(ticker)
    if not pack.get("ok"):
        return None
    graph = pack.get("graph") or {}
    # Prefer explicit sector fields, then node scan
    meta = graph.get("meta") or {}
    if meta.get("sector"):
        return str(meta["sector"])
    for node in (graph.get("nodes") or {}).values() if isinstance(graph.get("nodes"), dict) else []:
        if isinstance(node, dict) and (node.get("type") or node.get("entity_type")) == "Sector":
            return str(node.get("label") or node.get("name") or "")
    nodes_list = graph.get("nodes") if isinstance(graph.get("nodes"), list) else []
    for node in nodes_list:
        if isinstance(node, dict) and (node.get("type") or node.get("entity_type")) == "Sector":
            return str(node.get("label") or node.get("name") or "")
    return None


def kg_evidence_refs(ticker: str) -> list[dict[str, Any]]:
    pack = soft_get_company_graph(ticker)
    if not pack.get("available"):
        return []
    return [
        {
            "evidence_id": f"kg:{ticker}",
            "label": f"KG-01 company graph for {ticker}",
            "source": GRAPH_SYSTEM_OF_RECORD,
            "snippet": f"nodes={pack.get('node_count')} relationships={pack.get('relationship_count')}",
        }
    ]
