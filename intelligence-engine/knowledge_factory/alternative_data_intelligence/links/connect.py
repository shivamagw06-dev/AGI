"""Company / industry / relationship links — supported registry links only.

Never invent relationships. Soft-read IERI when present.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.alternative_data_intelligence import store as iadi_store
from knowledge_factory.alternative_data_intelligence.registry.catalog import DATASET_REGISTRY
from knowledge_factory.alternative_data_intelligence.schema import IADI_VERSION


def company_dataset_view(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").upper()
    hits = []
    for did, meta in DATASET_REGISTRY.items():
        if t in [str(x).upper() for x in (meta.get("company_links") or [])]:
            ds = iadi_store.get_dataset(did)
            hits.append(
                {
                    "dataset_id": did,
                    "name": meta.get("name"),
                    "domain": meta.get("domain"),
                    "provider": meta.get("provider"),
                    "latest_available": (ds or {}).get("latest_available"),
                    "trends": (ds or {}).get("trends") or {},
                    "confidence": meta.get("confidence"),
                    "link_basis": "registry_supported_company_link",
                }
            )
    return {
        "ticker": t,
        "n": len(hits),
        "datasets": hits,
        "version": IADI_VERSION,
        "fabricated": False,
        "note": "Links from Phase-1 registry only — no invented company mapping.",
    }


def industry_dataset_view(industry: str) -> dict[str, Any]:
    iid = str(industry or "").lower().replace(" ", "_").replace("-", "_")
    hits = []
    for did, meta in DATASET_REGISTRY.items():
        inds = [str(x).lower() for x in (meta.get("industry_links") or [])]
        secs = [str(x).lower() for x in (meta.get("sector_links") or [])]
        if iid in inds or iid in secs:
            ds = iadi_store.get_dataset(did)
            hits.append(
                {
                    "dataset_id": did,
                    "name": meta.get("name"),
                    "domain": meta.get("domain"),
                    "provider": meta.get("provider"),
                    "trends": (ds or {}).get("trends") or {},
                    "company_links": meta.get("company_links") or [],
                    "link_basis": "registry_supported_industry_link",
                }
            )
    return {
        "industry_id": iid,
        "n": len(hits),
        "datasets": hits,
        "version": IADI_VERSION,
        "fabricated": False,
    }


def soft_relationship_links(dataset_id: str) -> dict[str, Any]:
    """Soft-read IERI edges that mention relationship_hints — never invent."""
    meta = DATASET_REGISTRY.get(str(dataset_id).lower()) or {}
    hints = [str(h).lower() for h in (meta.get("relationship_hints") or [])]
    ieri_hits: list[dict[str, Any]] = []
    try:
        from knowledge_factory.economic_relationship_intelligence import store as ieri_store

        if ieri_store.relationship_count() == 0:
            from knowledge_factory.economic_relationship_intelligence.pipeline import (
                run_economic_relationship_pipeline,
            )

            run_economic_relationship_pipeline()
        for r in ieri_store.list_relationships():
            blob = " ".join(
                [
                    str(r.get("source_entity") or ""),
                    str(r.get("target_entity") or ""),
                    str(r.get("relationship_type") or ""),
                    str(r.get("shock_direction") or ""),
                ]
            ).lower()
            if any(h in blob for h in hints):
                ieri_hits.append(
                    {
                        "relationship_id": r.get("relationship_id"),
                        "source": r.get("source_entity"),
                        "target": r.get("target_entity"),
                        "relationship_type": r.get("relationship_type"),
                        "semantics": r.get("semantics"),
                        "confidence": r.get("confidence"),
                    }
                )
            if len(ieri_hits) >= 25:
                break
    except Exception:
        ieri_hits = []

    gov = list(meta.get("government_links") or [])
    return {
        "dataset_id": dataset_id,
        "government_links": gov,
        "macro_links": list(meta.get("macro_links") or []),
        "economic_relationship_links": ieri_hits,
        "n_ieri": len(ieri_hits),
        "version": IADI_VERSION,
        "fabricated": False,
        "inferred": False,
    }
