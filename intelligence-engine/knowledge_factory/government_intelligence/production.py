"""IGRI production facade — soft surface for routes / Mission Control."""

from __future__ import annotations

from typing import Any

from knowledge_factory.government_intelligence import store as igri_store
from knowledge_factory.government_intelligence.dashboard import government_dashboard
from knowledge_factory.government_intelligence.objects.compile import compile_government_intelligence
from knowledge_factory.government_intelligence.pipeline import run_government_intelligence_pipeline
from knowledge_factory.government_intelligence.schema import (
    DELIVERY_PHASE,
    FREEZE_LOCKS,
    IGRI_VERSION,
    LAYER,
    PHASE_1_DOMAINS,
    PHASE_2_EXTENSIBLE_DOMAINS,
    PROGRAMME,
)
from knowledge_factory.government_intelligence.timeline.build import replay_as_of


def _ensure() -> None:
    if igri_store.policy_count() == 0:
        run_government_intelligence_pipeline()


def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "programme": PROGRAMME,
        "layer": LAYER,
        "version": IGRI_VERSION,
        "delivery_phase": DELIVERY_PHASE,
        "architecture_status": "SOFT_GOVERNMENT_REGULATORY_INTELLIGENCE",
        "not_a_reasoning_engine": True,
        "not_a_planner": True,
        "not_governance": True,
        "never_political_opinion": True,
        "never_forecast_policy": True,
        "point_in_time_integrity": True,
        "freeze_locks": FREEZE_LOCKS,
        "api_prefix": "/v1/government",
        "phase_1_modules": [
            "RBI (monetary policy + banking regulation)",
            "Union Budget / Finance Ministry",
            "SEBI",
            "GST Council",
            "PLI schemes",
            "Import / export duties",
        ],
        "phase_1_domains": list(PHASE_1_DOMAINS),
        "phase_2_extensible": list(PHASE_2_EXTENSIBLE_DOMAINS),
        "modules": [
            "Phase-1 Government Registry",
            "RBI Intelligence",
            "Union Budget",
            "SEBI Intelligence",
            "GST Intelligence",
            "PLI Intelligence",
            "Trade / Import-Export Duties",
        ],
    }


def dashboard(**kwargs: Any) -> dict[str, Any]:
    return government_dashboard(**kwargs)


def run_pipeline(**kwargs: Any) -> dict[str, Any]:
    return run_government_intelligence_pipeline()


def list_policies(domain: str | None = None) -> dict[str, Any]:
    _ensure()
    rows = igri_store.list_policies(domain=domain)
    return {"n": len(rows), "domain": domain, "policies": rows, "version": IGRI_VERSION}


def get_policy(policy_id: str) -> dict[str, Any]:
    _ensure()
    row = igri_store.get_policy(policy_id)
    if not row:
        return {"policy_id": policy_id, "found": False, "version": IGRI_VERSION}
    return {**row, "found": True}


def search(q: str, *, limit: int = 25) -> dict[str, Any]:
    _ensure()
    query = str(q or "").strip().upper()
    hits = []
    for p in igri_store.list_policies():
        blob = f"{p.get('policy_id')} {p.get('name')} {p.get('domain')} {p.get('government_body')}".upper()
        if not query or query in blob:
            hits.append(
                {
                    "policy_id": p.get("policy_id"),
                    "name": p.get("name"),
                    "domain": p.get("domain"),
                    "government_body": p.get("government_body"),
                    "announcement_date": p.get("announcement_date"),
                    "impact_level": p.get("impact_level"),
                }
            )
        if len(hits) >= limit:
            break
    return {"q": q, "n": len(hits), "results": hits, "version": IGRI_VERSION}


def domain_view(domain: str) -> dict[str, Any]:
    return list_policies(domain=domain)


def timeline(*, as_of: str | None = None) -> dict[str, Any]:
    _ensure()
    tl = igri_store.get_timeline()
    if not tl:
        pack = compile_government_intelligence(persist=True)
        tl = pack["timeline"]
    if as_of:
        return replay_as_of(tl, as_of)
    return tl
