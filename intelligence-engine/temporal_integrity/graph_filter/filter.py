"""Evidence graph node/edge temporal filter."""

from __future__ import annotations

from typing import Any

from temporal_integrity.object_filter.filter import filter_objects
from temporal_integrity.validator.dates import text_has_future_year


def filter_graph(evidence_graph: dict[str, Any] | None, *, as_of: str | None) -> dict[str, Any]:
    eg = dict(evidence_graph or {})
    if not as_of:
        return {
            "evidence_graph": eg,
            "n_checked": 0,
            "n_rejected": 0,
            "rejected": [],
            "as_of": as_of,
            "fabricated": False,
        }

    nodes = list(eg.get("nodes") or [])
    edges = list(eg.get("edges") or [])
    node_res = filter_objects(nodes, as_of=as_of, source="evidence_graph_node", reject_unknown=False)
    kept_ids = {
        str(n.get("node_id") or n.get("id") or "")
        for n in node_res["kept"]
    }
    kept_edges = []
    edge_rejected = []
    for e in edges:
        src = str(e.get("source") or e.get("from") or "")
        dst = str(e.get("target") or e.get("to") or "")
        af = e.get("available_from")
        # Drop edges whose endpoints were rejected or edge itself is future-dated
        edge_obj = dict(e)
        if "available_from" not in edge_obj and af:
            edge_obj["available_from"] = af
        eres = filter_objects([edge_obj], as_of=as_of, source="evidence_graph_edge", reject_unknown=False)
        if eres["n_rejected"]:
            edge_rejected.extend(eres["rejected"])
            continue
        if kept_ids and src and dst and (src not in kept_ids or dst not in kept_ids):
            edge_rejected.append(
                {
                    "object": e,
                    "contract": {
                        "object_id": e.get("edge_id") or f"{src}->{dst}",
                        "temporal_status": "rejected",
                        "reason_if_rejected": "endpoint_rejected_or_missing",
                    },
                }
            )
            continue
        kept_edges.append(e)

    # Sanitize surface bullets — reject future-year labels (never silent substitute of content)
    bullets = list(eg.get("surface_bullets") or [])
    kept_bullets = []
    bullet_rejected = []
    for b in bullets:
        if text_has_future_year(b, as_of):
            bullet_rejected.append(
                {
                    "object": {"text": b},
                    "contract": {
                        "object_id": "surface_bullet",
                        "temporal_status": "rejected",
                        "reason_if_rejected": "surface_future_year",
                    },
                }
            )
        else:
            kept_bullets.append(b)

    eg["nodes"] = node_res["kept"]
    eg["edges"] = kept_edges
    eg["n_nodes"] = len(eg["nodes"])
    eg["n_edges"] = len(eg["edges"])
    eg["surface_bullets"] = kept_bullets
    eg["temporal_integrity"] = {
        "guard": "graph_filter",
        "as_of": as_of,
        "n_nodes_rejected": node_res["n_rejected"],
        "n_edges_rejected": len(edge_rejected),
        "n_bullets_rejected": len(bullet_rejected),
    }

    rejected = list(node_res["rejected"]) + edge_rejected + bullet_rejected
    return {
        "evidence_graph": eg,
        "n_checked": node_res["n_checked"] + len(edges) + len(bullets),
        "n_rejected": len(rejected),
        "rejected": rejected,
        "as_of": as_of,
        "fabricated": False,
    }
