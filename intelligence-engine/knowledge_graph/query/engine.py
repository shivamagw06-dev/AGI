"""Graph query engine — institutional natural-language-ish / structured queries."""

from __future__ import annotations

from typing import Any

from knowledge_graph.dependency_engine.engine import dependencies_for, traverse
from knowledge_graph.entity_resolution.resolve import resolve_entity, resolve_ticker
from knowledge_graph.graph.store import edges, node_for, nodes
from knowledge_graph.relationship_engine.engine import relationships_for


def find_path(source: str, target: str, *, max_depth: int = 5) -> dict[str, Any]:
    src = resolve_entity(source)
    dst = resolve_entity(target)
    if not src or not dst:
        return {"found": False, "source": source, "target": target, "paths": []}
    sid, tid = src["canonical_id"], dst["canonical_id"]
    paths = [p for p in traverse(sid, max_depth=max_depth, max_paths=20) if tid in (p.get("path") or [])]
    # Also try reverse if empty
    if not paths:
        rev = [p for p in traverse(tid, max_depth=max_depth, max_paths=20) if sid in (p.get("path") or [])]
        for p in rev:
            p = dict(p)
            p["path"] = list(reversed(p["path"]))
            p["path_labels"] = list(reversed(p["path_labels"]))
            p["start"], p["end"] = sid, tid
            paths.append(p)
    return {
        "found": bool(paths),
        "source": sid,
        "target": tid,
        "paths": paths[:8],
        "reproducible": True,
    }


def query_graph(payload: dict[str, Any] | None = None, *, question: str | None = None) -> dict[str, Any]:
    payload = payload or {}
    q = (question or payload.get("question") or payload.get("query") or "").strip()
    q_l = q.lower()
    entity = payload.get("entity") or payload.get("ticker") or payload.get("id")
    relation = payload.get("relation")
    exposed_to = payload.get("exposed_to") or payload.get("factor")

    # Structured: suppliers of X
    if entity and (payload.get("ask") == "suppliers" or "supplier" in q_l):
        dep = dependencies_for(str(entity))
        return {"ok": True, "intent": "suppliers", "result": dep}

    if entity and (payload.get("ask") == "relationships" or "connected" in q_l or "relationship" in q_l):
        return {"ok": True, "intent": "relationships", "result": relationships_for(str(entity))}

    # copper / oil exposure
    factor = exposed_to
    if not factor:
        for token, fid in (
            ("copper", "copper"),
            ("oil", "oil"),
            ("semiconductor", "semiconductor"),
            ("ai", "ai_infra"),
            ("repo", "repo_rate"),
            ("rbi rate", "event_rbi_rate_hike"),
        ):
            if token in q_l:
                factor = fid
                break
    if factor:
        fid = resolve_entity(str(factor))
        fid = fid["canonical_id"] if fid else str(factor)
        companies: list[str] = []
        sector_hits: list[str] = []

        def _absorb(nid: str) -> None:
            node = node_for(str(nid)) or {}
            if node.get("type") == "company":
                companies.append(str(nid))
            elif node.get("type") in {"sector", "industry"}:
                sector_hits.append(str(nid))

        for e in edges():
            if str(e.get("source")) == fid:
                _absorb(str(e.get("target")))
            if str(e.get("target")) == fid:
                _absorb(str(e.get("source")))
        # traverse from factor to companies / sectors
        for p in traverse(fid, max_depth=4, max_paths=25):
            for nid in p.get("path") or []:
                _absorb(str(nid))
        # Expand sector/industry hits to member companies
        for e in edges():
            if e.get("relation") == "member_of" and str(e.get("target")) in set(sector_hits):
                if (node_for(str(e.get("source"))) or {}).get("type") == "company":
                    companies.append(str(e.get("source")))
        return {
            "ok": True,
            "intent": "exposure",
            "factor": fid,
            "companies": sorted(set(companies)),
            "sectors": sorted(set(sector_hits)),
            "question": q or None,
        }

    # banks affected by RBI
    if "bank" in q_l and ("rbi" in q_l or "rate" in q_l):
        out = query_graph({"exposed_to": "event_rbi_rate_hike"})
        banks = [c for c in out.get("companies") or [] if (node_for(c) or {}).get("sector") == "banks" or c in {"HDFCBANK", "KOTAKBANK", "SBIN"}]
        # also sector_banks members
        for e in edges():
            if e.get("relation") == "member_of" and str(e.get("target")) == "sector_banks":
                banks.append(str(e.get("source")))
        return {"ok": True, "intent": "banks_rate_sensitivity", "companies": sorted(set(banks)), "question": q}

    # connected to Tata Motors
    if "tata motors" in q_l or "tatamotors" in q_l.replace(" ", ""):
        return {"ok": True, "intent": "relationships", "result": relationships_for("TATAMOTORS"), "question": q}

    # portfolio AI exposure
    if "portfolio" in q_l and "ai" in q_l:
        ai = query_graph({"exposed_to": "ai_infra"})
        return {
            "ok": True,
            "intent": "portfolio_ai_exposure",
            "companies": ai.get("companies"),
            "note": "Soft exposure map for Portfolio Office — not an order",
            "question": q,
        }

    # semiconductor dependency
    if "semiconductor" in q_l:
        return query_graph({"exposed_to": "semiconductor", "question": q})

    # path query
    if payload.get("source") and payload.get("target"):
        return {"ok": True, "intent": "path", "result": find_path(str(payload["source"]), str(payload["target"]))}

    # default entity resolve + relationships
    if entity:
        t = resolve_ticker(str(entity)) or str(entity)
        return {"ok": True, "intent": "entity", "result": relationships_for(t)}

    if q:
        # try resolve question as entity
        hit = resolve_entity(q)
        if hit:
            return {"ok": True, "intent": "entity", "result": relationships_for(hit["canonical_id"])}

    return {
        "ok": False,
        "intent": "unknown",
        "hint": "Try entity, exposed_to, suppliers, or path source/target",
        "sample_entities": [n["id"] for n in nodes() if n.get("type") == "company"][:10],
        "question": q or None,
    }
