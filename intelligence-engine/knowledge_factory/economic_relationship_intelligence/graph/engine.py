"""Economic Relationship Graph — relationships only. No reasoning."""

from __future__ import annotations

from collections import defaultdict, deque
from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION


def _node_key(kind: str, entity_id: str) -> str:
    k = str(kind or "entity").lower()
    e = str(entity_id or "")
    if k in ("company", "bank"):
        e = e.upper()
    elif k != "policy":
        e = e.lower()
    return f"{k}:{e}"


class EconomicRelationshipGraph:
    """In-memory directed multigraph over stored relationships."""

    def __init__(self, relationships: list[dict[str, Any]] | None = None):
        self.edges: list[dict[str, Any]] = list(relationships or [])
        self.adj: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self.nodes: dict[str, dict[str, Any]] = {}
        for r in self.edges:
            sref = r.get("source_ref") or {}
            tref = r.get("target_ref") or {}
            sk = _node_key(sref.get("kind") or "entity", r.get("source_entity") or sref.get("id"))
            tk = _node_key(tref.get("kind") or "entity", r.get("target_entity") or tref.get("id"))
            self.nodes[sk] = {"node_id": sk, "kind": sref.get("kind"), "id": r.get("source_entity")}
            self.nodes[tk] = {"node_id": tk, "kind": tref.get("kind"), "id": r.get("target_entity")}
            edge = {**r, "from": sk, "to": tk}
            self.adj[sk].append(edge)
            # bidirectional structural edges traversable both ways
            if r.get("direction") == "bidirectional":
                self.adj[tk].append({**r, "from": tk, "to": sk, "traversed_reverse": True})

    def neighbors(self, entity: str, *, kind: str | None = None) -> list[dict[str, Any]]:
        keys = self._match_keys(entity, kind)
        out = []
        for k in keys:
            out.extend(self.adj.get(k) or [])
        return out

    def paths(
        self,
        source: str,
        target: str | None = None,
        *,
        max_depth: int = 3,
        semantics: str | None = None,
        relationship_type: str | None = None,
        limit: int = 25,
    ) -> list[dict[str, Any]]:
        """BFS path enumeration over stored edges only — no inference."""
        start_keys = self._match_keys(source, None)
        if not start_keys:
            return []
        target_keys = set(self._match_keys(target, None)) if target else set()
        found: list[dict[str, Any]] = []

        for start in start_keys:
            q: deque[tuple[str, list[dict[str, Any]]]] = deque([(start, [])])
            visited_depth: dict[str, int] = {start: 0}
            while q:
                node, path = q.popleft()
                depth = len(path)
                if depth > 0 and (not target_keys or node in target_keys):
                    found.append(self._path_payload(path))
                    if len(found) >= limit:
                        return found
                    if target_keys:
                        continue
                if depth >= max_depth:
                    continue
                for edge in self.adj.get(node) or []:
                    if semantics and str(edge.get("semantics") or "") != semantics:
                        continue
                    if relationship_type and str(edge.get("relationship_type") or "") != relationship_type:
                        continue
                    nxt = edge["to"]
                    nd = depth + 1
                    if nxt in visited_depth and visited_depth[nxt] < nd:
                        continue
                    # allow revisit at same/shallower only once per BFS branch via path nodes
                    if any(e.get("to") == nxt for e in path) or nxt == start:
                        continue
                    visited_depth[nxt] = nd
                    q.append((nxt, path + [edge]))
        return found

    def ego_network(self, entity: str, *, depth: int = 1, limit: int = 100) -> dict[str, Any]:
        keys = self._match_keys(entity, None)
        nodes: dict[str, dict[str, Any]] = {}
        edges: list[dict[str, Any]] = []
        frontier = set(keys)
        seen_edges: set[str] = set()
        for d in range(max(1, depth)):
            nxt: set[str] = set()
            for k in frontier:
                nodes[k] = self.nodes.get(k) or {"node_id": k}
                for edge in self.adj.get(k) or []:
                    eid = edge.get("relationship_id")
                    if eid in seen_edges:
                        continue
                    seen_edges.add(str(eid))
                    edges.append(edge)
                    nodes[edge["to"]] = self.nodes.get(edge["to"]) or {"node_id": edge["to"]}
                    nxt.add(edge["to"])
                    if len(edges) >= limit:
                        return {
                            "entity": entity,
                            "depth": depth,
                            "nodes": list(nodes.values()),
                            "edges": edges[:limit],
                            "n_nodes": len(nodes),
                            "n_edges": min(len(edges), limit),
                            "version": IERI_VERSION,
                            "reasoning": False,
                        }
            frontier = nxt
        return {
            "entity": entity,
            "depth": depth,
            "nodes": list(nodes.values()),
            "edges": edges,
            "n_nodes": len(nodes),
            "n_edges": len(edges),
            "version": IERI_VERSION,
            "reasoning": False,
        }

    def _match_keys(self, entity: str | None, kind: str | None) -> list[str]:
        if not entity:
            return []
        e = str(entity)
        candidates = []
        if kind:
            candidates.append(_node_key(kind, e))
        else:
            for k in (
                "company",
                "industry",
                "commodity",
                "policy",
                "macro",
                "sector",
                "bank",
                "port",
                "railway",
                "utility",
            ):
                candidates.append(_node_key(k, e))
        return [c for c in candidates if c in self.nodes or c in self.adj]

    @staticmethod
    def _path_payload(path: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            "length": len(path),
            "orders": [e.get("transmission_order") or i + 1 for i, e in enumerate(path)],
            "nodes": [path[0]["from"]] + [e["to"] for e in path] if path else [],
            "relationship_ids": [e.get("relationship_id") for e in path],
            "types": [e.get("relationship_type") for e in path],
            "semantics": [e.get("semantics") for e in path],
            "confidences": [e.get("confidence") for e in path],
            "min_confidence": min((float(e.get("confidence") or 0) for e in path), default=0.0),
            "evidence": [e.get("evidence") for e in path],
            "fabricated": False,
        }


def build_graph(*, as_of: str | None = None) -> EconomicRelationshipGraph:
    rows = ieri_store.list_relationships(as_of=as_of)
    return EconomicRelationshipGraph(rows)
