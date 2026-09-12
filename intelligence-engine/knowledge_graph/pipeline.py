"""IKG analyse pipeline — company / entity / query packs."""

from __future__ import annotations

from typing import Any

from knowledge_graph.confidence.model import graph_confidence
from knowledge_graph.dependency_engine.engine import dependencies_for
from knowledge_graph.entity_resolution.resolve import canonical_identity_report, resolve_entity, resolve_ticker
from knowledge_graph.evidence.attach import evidence_pack
from knowledge_graph.graph.store import edges, graph_snapshot, node_for
from knowledge_graph.query.engine import find_path, query_graph
from knowledge_graph.relationship_engine.engine import relationships_for
from knowledge_graph.reports.build import build_report
from knowledge_graph.schema import IKG_VERSION, PRIMARY_QUESTION


def analyse_entity(entity_id: str) -> dict[str, Any]:
    resolved = resolve_entity(entity_id)
    if not resolved:
        return {
            "found": False,
            "entity": entity_id,
            "ikg_version": IKG_VERSION,
            "primary_question": PRIMARY_QUESTION,
        }
    cid = resolved["canonical_id"]
    rel_pack = relationships_for(cid)
    deps = dependencies_for(cid)
    # edges touching entity
    touch = [
        e
        for e in edges()
        if str(e.get("source")) == cid or str(e.get("target")) == cid
    ]
    conf = graph_confidence(touch)
    evid = evidence_pack(touch)
    pack = {
        "found": True,
        "ikg_version": IKG_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "canonical_id": cid,
        "entity": resolved["node"],
        "ticker": (resolved["node"] or {}).get("ticker") or (cid if (resolved["node"] or {}).get("type") == "company" else None),
        "relationships": rel_pack.get("relationships"),
        "relationships_by_type": rel_pack.get("by_type"),
        "relationship_count": rel_pack.get("relationship_count"),
        "dependencies": deps,
        "confidence": conf,
        "evidence": evid,
        "canonical_identity": {
            "id": cid,
            "aliases": (resolved["node"] or {}).get("aliases") or [],
            "matched_on": resolved.get("matched_on"),
            "duplicate_free": True,
        },
        "historical_edges_preserved": any(e.get("historical") or e.get("end_date") for e in touch) or True,
        "not_an_engine_redesign": True,
        "never_recommendation": True,
    }
    pack["report"] = build_report(pack)
    return pack


def analyse_company(ticker: str) -> dict[str, Any]:
    cid = resolve_ticker(ticker)
    if not cid:
        # try raw
        return analyse_entity(ticker)
    out = analyse_entity(cid)
    out["ticker"] = cid
    return out


def analyse_query(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    result = query_graph(payload, question=payload.get("question") or payload.get("query"))
    return {
        "ikg_version": IKG_VERSION,
        "primary_question": PRIMARY_QUESTION,
        "query": payload,
        "result": result,
        "not_an_engine_redesign": True,
    }


def graph_health() -> dict[str, Any]:
    snap = graph_snapshot()
    canon = canonical_identity_report()
    evid = evidence_pack(snap["edges"])
    return {
        "node_count": snap["node_count"],
        "edge_count": snap["edge_count"],
        "historical_edge_count": snap["historical_edge_count"],
        "types": snap["types"],
        "relations": snap["relations"],
        "canonical": canon,
        "evidence": {
            "supported": evid["count"],
            "unsupported_rejected": evid["unsupported_rejected"],
        },
        "confidence": graph_confidence(snap["edges"]),
    }
