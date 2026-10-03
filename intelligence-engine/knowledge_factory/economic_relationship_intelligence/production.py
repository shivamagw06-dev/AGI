"""IERI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence import store as ieri_store
from knowledge_factory.economic_relationship_intelligence.company_links.views import (
    company_relationships,
)
from knowledge_factory.economic_relationship_intelligence.dashboards import relationship_dashboard
from knowledge_factory.economic_relationship_intelligence.government_links.views import (
    policy_relationships,
)
from knowledge_factory.economic_relationship_intelligence.graph.engine import build_graph
from knowledge_factory.economic_relationship_intelligence.industry_links.views import (
    industry_relationships,
)
from knowledge_factory.economic_relationship_intelligence.macro_links.views import (
    macro_relationships,
)
from knowledge_factory.economic_relationship_intelligence.pipeline import (
    run_economic_relationship_pipeline,
)
from knowledge_factory.economic_relationship_intelligence.registry.catalog import registry_snapshot
from knowledge_factory.economic_relationship_intelligence.schema import (
    FREEZE_LOCKS,
    IERI_VERSION,
    LAYER,
    PROGRAMME,
)
from knowledge_factory.economic_relationship_intelligence.transmission.orders import (
    transmission_from_entity,
)


def _ensure() -> None:
    if ieri_store.relationship_count() == 0:
        run_economic_relationship_pipeline()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": IERI_VERSION,
        "architecture_status": "SOFT_ECONOMIC_RELATIONSHIP_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "not_a_graph_database_project": True,
        "not_a_planner": True,
        "never_fabricate": True,
        "point_in_time_integrity": True,
        "soft_wire_only": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/relationship",
        "economic_semantics": [
            "structural",
            "financial",
            "policy",
            "market",
            "operational",
            "behavioural",
        ],
        "modules": [
            "Relationship Objects",
            "Relationship Registry",
            "Company Links",
            "Industry Links",
            "Commodity Links",
            "Government Links",
            "Macro Links",
            "Economic Transmission",
            "Economic Relationship Graph",
            "Historical Replay",
            "Morning Board",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return relationship_dashboard(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_economic_relationship_pipeline()


def registry() -> dict[str, Any]:
    return registry_snapshot()


def company(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    return company_relationships(ticker, as_of=as_of)


def industry(name: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    return industry_relationships(name, as_of=as_of)


def commodity(name: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    cid = str(name or "").lower().replace(" ", "_").replace("-", "_")
    obj = ieri_store.get_commodity(cid)
    links = ieri_store.list_relationships(entity=cid, as_of=as_of)
    tx = transmission_from_entity(cid, as_of=as_of)
    return {
        "commodity": obj,
        "relationships": links,
        "transmission": {
            "first_order": tx.get("first_order"),
            "second_order": tx.get("second_order"),
            "third_order": tx.get("third_order"),
        },
        "n": len(links),
        "version": IERI_VERSION,
        "fabricated": False,
    }


def policy(name: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    return policy_relationships(name, as_of=as_of)


def macro(name: str, *, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    return macro_relationships(name, as_of=as_of)


def network(entity: str, *, depth: int = 2, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    g = build_graph(as_of=as_of)
    return g.ego_network(entity, depth=depth)


def path_query(
    *,
    source: str,
    target: str | None = None,
    max_depth: int = 3,
    semantics: str | None = None,
    relationship_type: str | None = None,
    as_of: str | None = None,
    limit: int = 25,
) -> dict[str, Any]:
    _ensure()
    g = build_graph(as_of=as_of)
    paths = g.paths(
        source,
        target,
        max_depth=max_depth,
        semantics=semantics,
        relationship_type=relationship_type,
        limit=limit,
    )
    return {
        "source": source,
        "target": target,
        "max_depth": max_depth,
        "semantics": semantics,
        "relationship_type": relationship_type,
        "as_of": as_of,
        "n": len(paths),
        "paths": paths,
        "version": IERI_VERSION,
        "fabricated": False,
        "reasoning": False,
    }


def search(
    q: str = "",
    *,
    semantics: str | None = None,
    relationship_type: str | None = None,
    limit: int = 50,
    as_of: str | None = None,
) -> dict[str, Any]:
    _ensure()
    query = str(q or "").strip().lower()
    rows = ieri_store.list_relationships(
        relationship_type=relationship_type,
        semantics=semantics,
        as_of=as_of,
    )
    hits = []
    for r in rows:
        blob = " ".join(
            [
                str(r.get("relationship_id") or ""),
                str(r.get("source_entity") or ""),
                str(r.get("target_entity") or ""),
                str(r.get("relationship_type") or ""),
                str(r.get("semantics") or ""),
                str(r.get("shock_direction") or ""),
                " ".join(str(x) for x in (r.get("evidence") or [])),
            ]
        ).lower()
        if not query or query in blob:
            hits.append(
                {
                    "relationship_id": r.get("relationship_id"),
                    "source": r.get("source_entity"),
                    "target": r.get("target_entity"),
                    "relationship_type": r.get("relationship_type"),
                    "semantics": r.get("semantics"),
                    "confidence": r.get("confidence"),
                    "strength": r.get("strength"),
                    "shock_direction": r.get("shock_direction"),
                    "transmission_order": r.get("transmission_order"),
                }
            )
        if len(hits) >= limit:
            break
    return {"q": q, "n": len(hits), "results": hits, "version": IERI_VERSION}


def replay(*, as_of: str) -> dict[str, Any]:
    """Point-in-time relationship replay — available_from <= as_of only."""
    _ensure()
    rows = ieri_store.list_relationships(as_of=as_of)
    return {
        "as_of": as_of,
        "n": len(rows),
        "relationships": [
            {
                "relationship_id": r.get("relationship_id"),
                "source": r.get("source_entity"),
                "target": r.get("target_entity"),
                "relationship_type": r.get("relationship_type"),
                "available_from": r.get("available_from"),
                "effective_date": r.get("effective_date"),
                "confidence": r.get("confidence"),
            }
            for r in rows
        ],
        "future_leak": False,
        "version": IERI_VERSION,
        "fabricated": False,
    }


def shock_impact(
    entity: str,
    *,
    direction: str | None = None,
    max_order: int = 3,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Structured beneficiaries / losers from stored shock_direction fields + paths."""
    _ensure()
    tx = transmission_from_entity(
        entity, max_order=max_order, shock_filter=direction, as_of=as_of
    )
    rows = ieri_store.list_relationships(entity=entity, as_of=as_of)
    beneficiaries = []
    losers = []
    for r in rows:
        shock = str(r.get("shock_direction") or "")
        item = {
            "entity": r.get("target_entity")
            if str(r.get("source_entity")).lower() == str(entity).lower()
            or str(r.get("source_entity")).upper() == str(entity).upper()
            else r.get("source_entity"),
            "relationship_id": r.get("relationship_id"),
            "relationship_type": r.get("relationship_type"),
            "semantics": r.get("semantics"),
            "confidence": r.get("confidence"),
            "shock_direction": shock,
            "transmission_order": r.get("transmission_order") or 1,
            "evidence": r.get("evidence"),
        }
        if "benefit" in shock or "eases" in shock or "benefits" in shock:
            beneficiaries.append(item)
        if "hurt" in shock or "cost_up" in shock or "pressure" in shock:
            losers.append(item)
    return {
        "entity": entity,
        "direction_filter": direction,
        "beneficiaries": beneficiaries,
        "losers": losers,
        "transmission": tx,
        "version": IERI_VERSION,
        "fabricated": False,
        "reasoning": False,
        "note": "Answers from stored evidence-backed relationships only.",
    }
