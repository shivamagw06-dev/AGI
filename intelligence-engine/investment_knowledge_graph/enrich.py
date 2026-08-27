"""Soft-attach Investment Knowledge Graph context into CID."""

from __future__ import annotations

from typing import Any


def merge_graph_into_dossier(dossier: dict[str, Any], graph_pack: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(dossier, dict) or not isinstance(graph_pack, dict):
        return dossier
    out = dict(dossier)
    graph = graph_pack.get("knowledge_graph") if "knowledge_graph" in graph_pack else graph_pack
    if not isinstance(graph, dict) or not graph.get("nodes"):
        return out

    out["investment_knowledge_graph"] = {
        "enabled": True,
        "ok": True,
        "entity": graph.get("entity"),
        "sector_key": graph.get("sector_key"),
        "n_nodes": graph.get("n_nodes"),
        "n_edges": graph.get("n_edges"),
        "peers": graph.get("peers") or [],
        "themes": graph.get("themes") or [],
        "sector_chain": graph.get("sector_chain") or [],
        "nodes": graph.get("nodes") or [],
        "edges": graph.get("edges") or [],
        "ownership_concentration": graph_pack.get("ownership_concentration"),
        "version": graph_pack.get("version"),
    }

    # Soft peer fill for identity
    identity = dict(out.get("identity") or {})
    if not identity.get("peers") and graph.get("peers"):
        identity["peers"] = list(graph.get("peers") or [])
    out["identity"] = identity

    evidence = list(out.get("evidence") or [])
    evidence.append(
        {
            "evidence_type": "investment_knowledge_graph",
            "source_id": "investment_knowledge_graph",
            "ticker": graph.get("entity"),
            "payload": {
                "n_nodes": graph.get("n_nodes"),
                "n_edges": graph.get("n_edges"),
                "themes": graph.get("themes"),
                "sector_chain": graph.get("sector_chain"),
            },
            "confidence": 0.85,
        }
    )
    out["evidence"] = evidence[-200:]
    return out
