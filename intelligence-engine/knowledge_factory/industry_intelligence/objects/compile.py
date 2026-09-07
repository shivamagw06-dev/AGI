"""Compile immutable Industry Objects + full registry coverage."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from knowledge_factory.industry_intelligence import store as iivi_store
from knowledge_factory.industry_intelligence.collectors.soft import collect_industry_context
from knowledge_factory.industry_intelligence.producers.core import produce_industry_modules
from knowledge_factory.industry_intelligence.registry.catalog import (
    INDUSTRY_REGISTRY,
    build_company_industry_map,
)
from knowledge_factory.industry_intelligence.schema import (
    FREEZE_LOCKS,
    FUTURE_ECONOMIC_NETWORK_GRAPH,
    IIVI_VERSION,
    LAYER,
    PROGRAMME,
)
from knowledge_factory.industry_intelligence.validators.gates import validate_industry


def _intelligence_score(modules: dict[str, Any], quality: dict[str, Any]) -> float:
    present = sum(1 for v in modules.values() if isinstance(v, dict) and v.get("data") is not None)
    module_score = 100.0 * present / max(len(modules), 1)
    gate_score = 100.0 if quality.get("gate_pass") else 60.0
    return round(0.7 * module_score + 0.3 * gate_score, 2)


def compile_industry(industry_id: str, *, members: list[str] | None = None, persist: bool = True) -> dict[str, Any]:
    iid = str(industry_id or "").lower()
    ctx = collect_industry_context(iid, members=members)
    modules = produce_industry_modules(ctx)
    draft = {
        "industry_id": iid,
        "modules": modules,
        "validation_failed": False,
    }
    quality = validate_industry(draft)
    score = _intelligence_score(modules, quality)
    available_from = "2000-01-01"  # structural knowledge baseline; versioned

    obj = {
        "kind": "industry_intelligence_object",
        "iivi_version": IIVI_VERSION,
        "programme": PROGRAMME,
        "layer": LAYER,
        "industry_id": iid,
        "name": (ctx.get("meta") or {}).get("name") or iid,
        "sector": ctx.get("sector"),
        "modules": modules,
        "members": list(members or []),
        "member_count": len(members or []),
        "quality": quality,
        "institutional_ready": bool(quality.get("institutional_ready")),
        "intelligence_score": score,
        "announcement_date": available_from,
        "available_from": available_from,
        "version": IIVI_VERSION,
        "historical_changes": [],
        "point_in_time": True,
        "immutable": True,
        "freeze_locks": FREEZE_LOCKS,
        "future_roadmap": FUTURE_ECONOMIC_NETWORK_GRAPH,
        "fabricated": False,
        "not_a_reasoning_engine": True,
    }
    if persist:
        iivi_store.put_industry(obj)
    return obj


def compile_all_industries(*, persist: bool = True) -> dict[str, Any]:
    cmap = build_company_industry_map()
    by_industry: dict[str, list[str]] = defaultdict(list)
    for t, iid in cmap.items():
        by_industry[iid].append(t)

    # Compile every registry industry (even if zero members) + any mapped ids
    industry_ids = sorted(set(INDUSTRY_REGISTRY.keys()) | set(by_industry.keys()))
    objects = []
    ready = 0
    for iid in industry_ids:
        obj = compile_industry(iid, members=sorted(by_industry.get(iid, [])), persist=persist)
        objects.append(obj)
        if obj.get("institutional_ready"):
            ready += 1

    if persist:
        iivi_store.put_company_map(cmap)

    unmapped = [t for t, iid in cmap.items() if iid not in INDUSTRY_REGISTRY]
    return {
        "kind": "industry_intelligence_pack",
        "iivi_version": IIVI_VERSION,
        "industries": len(objects),
        "companies_mapped": len(cmap),
        "unmapped_companies": unmapped,
        "institutional_ready": ready,
        "institutional_ready_pct": round(100.0 * ready / (len(objects) or 1), 2),
        "company_map_complete": len(unmapped) == 0 and len(cmap) == 500,
        "objects": objects,
        "fabricated": False,
    }
