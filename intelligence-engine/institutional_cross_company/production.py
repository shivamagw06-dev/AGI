"""CCI-01 production façades — relationships APIs / Relationship Center / query."""

from __future__ import annotations

import re
import time
from typing import Any, Optional

from institutional_cross_company.clustering import build_clusters, cluster_for_ticker, clusters_pack
from institutional_cross_company.diagnostics import build_diagnostics, relationship_center_board
from institutional_cross_company.flags import flags_dict, is_enabled
from institutional_cross_company.impact_engine import impact_query
from institutional_cross_company.kg_bridge import soft_get_company_graph
from institutional_cross_company.models import RelationshipQueryResult
from institutional_cross_company.propagation import propagate
from institutional_cross_company.relationship_engine import (
    group_by_type,
    provider_catalog,
    relationships_for_company,
    relationships_for_macro,
    relationships_for_sector,
)
from institutional_cross_company.relationship_registry import reset_registry_for_tests
from institutional_cross_company.schema import (
    CCI_PRODUCT,
    CCI_ROLE,
    CCI_SPEC,
    CCI_VERSION,
    CCI_WORKSTREAM_ID,
    GRAPH_SYSTEM_OF_RECORD,
    RELATIONSHIP_ENGINE_VERSION,
)
from institutional_cross_company.similarity import similar_companies, similarity_pack
from institutional_cross_company.traversal import traverse
from institutional_cross_company.validator import validate_relationships

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


_CACHE: dict[str, Any] = {}


def reset_for_tests() -> None:
    _CACHE.clear()
    reset_registry_for_tests()


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "workstream_id": CCI_WORKSTREAM_ID,
        "product": CCI_PRODUCT,
        "version": CCI_VERSION,
        "role": CCI_ROLE,
        "llm": False,
        "generates_recommendations": False,
        "owns_graph": False,
        "graph_system_of_record": GRAPH_SYSTEM_OF_RECORD,
        "predictive": False,
        "dependency_propagation_only": True,
        "relationship_engine_version": RELATIONSHIP_ENGINE_VERSION,
        "providers": provider_catalog(),
        "flags": flags_dict(),
        "enabled": is_enabled(),
        "spec": CCI_SPEC,
        "brand": "AGI",
        "phase": 5,
        "as_of": now_iso(),
    }


def soft_slice_mission_control() -> dict[str, Any]:
    h = health()
    board = relationship_center_board(list(_CACHE.values()))
    return {
        "status": h.get("status"),
        "workstream_id": CCI_WORKSTREAM_ID,
        "product": CCI_PRODUCT,
        "version": CCI_VERSION,
        "llm": False,
        "relationship_center": True,
        "owns_graph": False,
        "graph_system_of_record": GRAPH_SYSTEM_OF_RECORD,
        **board,
    }


def get_company_relationships(ticker: str, *, portfolio_id: str = "agi-core-equity") -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": CCI_WORKSTREAM_ID}
    t0 = time.perf_counter()
    t = str(ticker or "").upper().strip()
    rels = relationships_for_company(t, portfolio_id=portfolio_id)
    ok, validation = validate_relationships(rels)
    latency = (time.perf_counter() - t0) * 1000.0
    diag = build_diagnostics(ok, latency_ms=latency, validation=validation)
    kg = soft_get_company_graph(t)
    pack = {
        "ok": True,
        "workstream_id": CCI_WORKSTREAM_ID,
        "ticker": t,
        "relationships": [r.to_dict() for r in ok],
        "by_type": group_by_type(ok),
        "competitors": [r.target_entity for r in ok if r.relationship_type == "competitor"],
        "macro_drivers": [r.target_entity for r in ok if r.category == "macro"],
        "similar": [s.to_dict() for s in similar_companies(t)],
        "clusters": [c.to_dict() for c in cluster_for_ticker(t)],
        "traversal": traverse(t, max_depth=1),
        "kg_ref": {
            "system": GRAPH_SYSTEM_OF_RECORD,
            "available": bool(kg.get("available")),
            "ok": bool(kg.get("ok")),
            "node_count": kg.get("node_count"),
            "relationship_count": kg.get("relationship_count"),
        },
        "diagnostics": diag,
        "owns_graph": False,
        "generates_recommendations": False,
        "latency_ms": round(latency, 2),
    }
    _CACHE[f"company:{t}"] = pack
    return pack


def get_sector_relationships(sector: str) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": CCI_WORKSTREAM_ID}
    t0 = time.perf_counter()
    rels = relationships_for_sector(sector)
    ok, validation = validate_relationships(rels)
    latency = (time.perf_counter() - t0) * 1000.0
    pack = {
        "ok": True,
        "workstream_id": CCI_WORKSTREAM_ID,
        "sector": sector,
        "relationships": [r.to_dict() for r in ok[:80]],
        "by_type": group_by_type(ok),
        "clusters": clusters_pack(),
        "diagnostics": build_diagnostics(ok, latency_ms=latency, validation=validation),
        "owns_graph": False,
    }
    _CACHE[f"sector:{sector}"] = pack
    return pack


def get_macro_relationships(driver: str) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": CCI_WORKSTREAM_ID}
    t0 = time.perf_counter()
    rels = relationships_for_macro(driver)
    ok, validation = validate_relationships(rels)
    prop = propagate(driver)
    latency = (time.perf_counter() - t0) * 1000.0
    pack = {
        "ok": True,
        "workstream_id": CCI_WORKSTREAM_ID,
        "driver": prop.driver,
        "relationships": [r.to_dict() for r in ok],
        "propagation": prop.to_dict(),
        "diagnostics": build_diagnostics(ok, latency_ms=latency, validation=validation),
        "owns_graph": False,
        "predictive": False,
    }
    _CACHE[f"macro:{prop.driver}"] = pack
    return pack


def _extract_ticker(text: str) -> str:
    known = (
        "HDFCBANK",
        "ICICIBANK",
        "KOTAKBANK",
        "AXISBANK",
        "INFY",
        "TCS",
        "WIPRO",
        "HCLTECH",
        "TATAMOTORS",
        "MARUTI",
        "ADANIPORTS",
        "RELIANCE",
        "SBIN",
    )
    upper = text.upper()
    for t in known:
        if t in upper:
            return t
    m = re.search(r"\b([A-Z]{2,12}(?:&[A-Z]+)?)\b", upper)
    return m.group(1) if m else ""


def query_relationships(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "workstream_id": CCI_WORKSTREAM_ID}
    body = dict(payload or {})
    question = str(body.get("question") or body.get("query") or body.get("q") or "").strip()
    portfolio_id = str(body.get("portfolio_id") or "agi-core-equity")
    ticker = str(body.get("ticker") or _extract_ticker(question) or "").upper()
    q = question.lower()

    intent = "company"
    if any(k in q for k in ("similar", "most like", "resemble")):
        intent = "similarity"
    elif any(k in q for k in ("oil", "rates", "interest", "rbi", "fx", "inflation", "gdp", "credit", "macro", "benefit")):
        intent = "macro_impact"
    elif any(k in q for k in ("cluster", "group", "private banks", "nbfc", "it services")):
        intent = "cluster"
    elif any(k in q for k in ("compete", "competitor", "rival")):
        intent = "competitors"
    elif any(k in q for k in ("portfolio", "holding", "shared macro", "common risk")):
        intent = "portfolio"
    elif any(k in q for k in ("connected", "network", "relate")):
        intent = "network"

    result = RelationshipQueryResult(query=question, intent=intent)

    if intent == "similarity" and ticker:
        result.similarities = list(similar_companies(ticker))
        result.relationships = relationships_for_company(ticker, portfolio_id=portfolio_id)
    elif intent in {"macro_impact"}:
        driver = "interest_rates"
        if "oil" in q:
            driver = "oil"
        elif "fx" in q or "currency" in q:
            driver = "fx"
        elif "inflation" in q:
            driver = "inflation"
        elif "gdp" in q:
            driver = "gdp"
        elif "credit" in q:
            driver = "credit_cycle"
        result.propagation = propagate(driver, portfolio_id=portfolio_id)
        result.relationships = relationships_for_macro(driver)
    elif intent == "cluster":
        result.clusters = list(build_clusters())
    elif intent == "portfolio":
        from institutional_cross_company.relationship_registry import discover_all

        result.relationships = discover_all({"portfolio_id": portfolio_id, "ticker": ticker})
    elif ticker:
        result.relationships = relationships_for_company(ticker, portfolio_id=portfolio_id)
        result.similarities = list(similar_companies(ticker))
        result.clusters = list(cluster_for_ticker(ticker))
        if intent == "network":
            result.kg_refs = [soft_get_company_graph(ticker)]
    else:
        result.clusters = list(build_clusters())

    ok, validation = validate_relationships(result.relationships)
    result.relationships = ok
    result.diagnostics = build_diagnostics(ok, validation=validation)
    out = result.to_dict()
    out["ok"] = True
    out["workstream_id"] = CCI_WORKSTREAM_ID
    out["impact"] = impact_query(ticker=ticker, driver=result.propagation.driver if result.propagation else "")
    _CACHE[f"query:{intent}:{ticker or 'na'}"] = out
    return out


def get_similarity(ticker: str) -> dict[str, Any]:
    return {"ok": True, "workstream_id": CCI_WORKSTREAM_ID, **similarity_pack(ticker)}


def get_clusters() -> dict[str, Any]:
    return {"ok": True, "workstream_id": CCI_WORKSTREAM_ID, **clusters_pack()}


def get_propagation(driver: str) -> dict[str, Any]:
    return {"ok": True, "workstream_id": CCI_WORKSTREAM_ID, **propagate(driver).to_dict()}


def get_impact(payload: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    body = dict(payload or {})
    return impact_query(
        driver=str(body.get("driver") or ""),
        ticker=str(body.get("ticker") or ""),
        portfolio_id=str(body.get("portfolio_id") or "agi-core-equity"),
    )
