"""IIVI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from knowledge_factory.industry_intelligence import store as iivi_store
from knowledge_factory.industry_intelligence.dashboards import industry_dashboard
from knowledge_factory.industry_intelligence.objects.compile import compile_all_industries, compile_industry
from knowledge_factory.industry_intelligence.pipeline import run_industry_intelligence_pipeline
from knowledge_factory.industry_intelligence.schema import (
    FREEZE_LOCKS,
    FUTURE_ECONOMIC_NETWORK_GRAPH,
    IIVI_VERSION,
    LAYER,
    PROGRAMME,
)


def _ensure() -> None:
    if iivi_store.industry_count() == 0:
        run_industry_intelligence_pipeline()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": IIVI_VERSION,
        "architecture_status": "SOFT_INDUSTRY_VALUE_CHAIN_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "never_fabricate": True,
        "point_in_time_integrity": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/industry",
        "future_roadmap": FUTURE_ECONOMIC_NETWORK_GRAPH,
        "modules": [
            "Industry Registry",
            "Business Model",
            "Value Chain",
            "Supply Chain",
            "Economics",
            "Accounting Playbooks",
            "Valuation Playbooks",
            "KPI Library",
            "Cycles",
            "Institutional Playbooks",
            "Knowledge Graph (references)",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return industry_dashboard(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_industry_intelligence_pipeline()


def get_industry(name: str, *, refresh: bool = False) -> dict[str, Any]:
    _ensure()
    iid = str(name or "").lower().replace(" ", "_").replace("-", "_")
    if not refresh:
        row = iivi_store.get_industry(iid)
        if row:
            return row
    # try name match
    for obj in iivi_store.list_industries():
        if obj.get("industry_id") == iid or str(obj.get("name") or "").lower() == str(name or "").lower():
            return obj
    return compile_industry(iid, persist=True)


def search(q: str, *, limit: int = 25) -> dict[str, Any]:
    _ensure()
    query = str(q or "").strip().lower()
    hits = []
    for obj in iivi_store.list_industries():
        blob = f"{obj.get('industry_id')} {obj.get('name')} {obj.get('sector')}".lower()
        if not query or query in blob:
            hits.append(
                {
                    "industry_id": obj.get("industry_id"),
                    "name": obj.get("name"),
                    "sector": obj.get("sector"),
                    "member_count": obj.get("member_count"),
                    "intelligence_score": obj.get("intelligence_score"),
                    "institutional_ready": obj.get("institutional_ready"),
                }
            )
        if len(hits) >= limit:
            break
    return {"q": q, "n": len(hits), "results": hits, "version": IIVI_VERSION}


def _module_view(name: str, module: str) -> dict[str, Any]:
    obj = get_industry(name)
    mod = (obj.get("modules") or {}).get(module) or {}
    return {
        "industry_id": obj.get("industry_id"),
        "name": obj.get("name"),
        "module": module,
        "data": mod.get("data"),
        "provenance": mod.get("provenance"),
        "version": IIVI_VERSION,
        "fabricated": False,
    }


def playbook(name: str) -> dict[str, Any]:
    return _module_view(name, "playbook")


def value_chain(name: str) -> dict[str, Any]:
    return _module_view(name, "value_chain")


def accounting(name: str) -> dict[str, Any]:
    return _module_view(name, "accounting")


def valuation(name: str) -> dict[str, Any]:
    return _module_view(name, "valuation")


def cycles(name: str) -> dict[str, Any]:
    return _module_view(name, "cycles")


def kpis(name: str) -> dict[str, Any]:
    return _module_view(name, "kpis")


def company_industry(ticker: str) -> dict[str, Any]:
    _ensure()
    t = str(ticker or "").upper()
    iid = iivi_store.get_company_industry(t)
    return {
        "ticker": t,
        "industry_id": iid,
        "industry": get_industry(iid) if iid else None,
        "version": IIVI_VERSION,
    }
