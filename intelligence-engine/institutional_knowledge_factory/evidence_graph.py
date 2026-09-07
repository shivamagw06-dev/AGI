"""KPE-owned Evidence Graph — infrastructure, not an application layer.

Ownership:
  - KPE writes (Compile + Incremental modes)
  - KR resolves assertion evidence refs via graph pack (never stores raw evidence)
  - IRE / Ask assemble from Knowledge Objects — never query the graph directly

The standalone `institutional_evidence_graph` module is legacy telemetry only.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

GRAPH_VERSION = "kpe-evidence-graph-v1.0.0"


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def store_root() -> Path:
    raw = (os.getenv("KPE_EVIDENCE_GRAPH_ROOT") or "").strip()
    if raw:
        root = Path(raw)
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "kpe" / "evidence_graph"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path(entity_id: str) -> Path:
    return store_root() / f"{entity_id.upper()}.json"


def _empty_graph(entity_id: str) -> dict[str, Any]:
    return {
        "graph_version": GRAPH_VERSION,
        "entity_id": entity_id.upper(),
        "owned_by": "kpe",
        "nodes": {},
        "edges": [],
        "updated_at": None,
    }


def load_graph(entity_id: str) -> dict[str, Any]:
    path = _path(entity_id)
    if not path.exists():
        return _empty_graph(entity_id)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data.setdefault("nodes", {})
            data.setdefault("edges", [])
            return data
    except Exception:
        pass
    return _empty_graph(entity_id)


def save_graph(graph: dict[str, Any]) -> dict[str, Any]:
    entity_id = str(graph.get("entity_id") or "").upper()
    if not entity_id:
        raise ValueError("graph.entity_id required")
    graph["updated_at"] = _now_iso()
    path = _path(entity_id)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(graph, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
    return graph


def add_evidence_node(
    graph: dict[str, Any],
    *,
    evidence_id: str,
    source_id: str | None = None,
    trust_score: int | None = None,
    freshness: int | None = None,
    provenance: str | None = None,
    role: str = "supporting",
) -> dict[str, Any]:
    """Add or update an evidence node. KPE write path only."""
    nodes = graph.setdefault("nodes", {})
    nodes[str(evidence_id)] = {
        "evidence_id": evidence_id,
        "source_id": source_id,
        "trust_score": trust_score,
        "freshness": freshness,
        "source_quality": trust_score or 70,
        "provenance": provenance or "kpe",
        "role": role,
        "updated_at": _now_iso(),
    }
    return graph


def link_assertion(
    graph: dict[str, Any],
    *,
    evidence_id: str,
    claim_id: str,
    relation: str = "supporting",
) -> dict[str, Any]:
    """Link evidence node to assertion (claim). Append-only edges."""
    edge = {
        "evidence_id": evidence_id,
        "claim_id": claim_id,
        "relation": relation,
        "linked_at": _now_iso(),
    }
    edges = graph.setdefault("edges", [])
    if not any(
        e.get("evidence_id") == evidence_id and e.get("claim_id") == claim_id
        for e in edges
    ):
        edges.append(edge)
    return graph


def apply_delta(entity_id: str, delta: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply evidence graph delta from KPE pipeline output. Returns updated graph."""
    graph = load_graph(entity_id)
    for entry in delta:
        if not isinstance(entry, dict):
            continue
        eid = entry.get("evidence_id")
        cid = entry.get("claim_id")
        if not eid:
            continue
        add_evidence_node(
            graph,
            evidence_id=str(eid),
            source_id=entry.get("source_id"),
            trust_score=entry.get("trust_score"),
            freshness=entry.get("freshness"),
            provenance=entry.get("provenance") or "kpe",
        )
        if cid:
            link_assertion(graph, evidence_id=str(eid), claim_id=str(cid))
    return save_graph(graph)


def get_graph_pack(entity_id: str) -> dict[str, Any]:
    """Return graph pack for KR evidence resolution — internal bridge only."""
    graph = load_graph(entity_id)
    nodes = graph.get("nodes") or {}
    return {
        "entity_id": entity_id.upper(),
        "graph_version": GRAPH_VERSION,
        "owned_by": "kpe",
        "items": list(nodes.values()),
        "nodes": nodes,
        "edge_count": len(graph.get("edges") or []),
        "node_count": len(nodes),
    }


def graph_stats(entity_id: str) -> dict[str, Any]:
    graph = load_graph(entity_id)
    nodes = graph.get("nodes") or {}
    edges = graph.get("edges") or []
    claim_ids = {e.get("claim_id") for e in edges if e.get("claim_id")}
    return {
        "entity_id": entity_id.upper(),
        "node_count": len(nodes),
        "edge_count": len(edges),
        "linked_claims": len(claim_ids),
        "updated_at": graph.get("updated_at"),
    }
