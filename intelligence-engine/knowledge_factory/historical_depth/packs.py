"""Historical Evidence Packs — soft feed for existing evidence producers."""

from __future__ import annotations

from typing import Any

from knowledge_factory.historical_depth import store as hd_store
from knowledge_factory.historical_depth.producers.derived import produce_derived, produce_risk_momentum
from knowledge_factory.historical_depth.schema import HD_VERSION


def build_historical_pack(entity: str, *, as_of: str | None = None) -> dict[str, Any]:
    e = entity.upper()
    derived = produce_derived(e, as_of=as_of)
    risk = produce_risk_momentum(e, as_of=as_of)
    company = hd_store.get_object("company", e if not as_of else f"{e}@{as_of}")
    if not company:
        from knowledge_factory.historical_depth.objects.company import compile_historical_company

        company = compile_historical_company(e, as_of=as_of)

    pe_pts = ((derived.get("metrics") or {}).get("PE") or {}).get("points") or {}
    pe_vals = list(pe_pts.values())
    quality = 92.0 if (derived.get("n_periods") or 0) >= 10 else 70.0
    if (derived.get("n_periods") or 0) >= 15:
        quality = 95.0
    if (derived.get("n_periods") or 0) >= 20:
        quality = 97.0

    pack = {
        "kind": "historical_evidence_pack",
        "hd_version": HD_VERSION,
        "entity": e,
        "as_of": as_of,
        "valuation": derived.get("metrics") or {},
        "accounting": (company or {}).get("historical_accounting") or {},
        "business_quality": (company or {}).get("historical_business_quality") or {},
        "risk": risk,
        "macro": {"as_of": as_of},
        "sector": (company or {}).get("sector"),
        "timeline": (company or {}).get("timeline") or [],
        "current_pe": pe_vals[-1] if pe_vals else None,
        "historical_pe": round(sum(pe_vals) / len(pe_vals), 4) if pe_vals else None,
        "pe_percentiles": derived.get("pe_percentiles") or {},
        "evidence_quality": quality,
        "coverage": (company or {}).get("coverage") or {},
        "historical_provenance": {
            "source": "knowledge_factory.historical_depth",
            "raw_api": False,
            "reproducible": True,
            "point_in_time_integrity": True,
        },
        "provenance": "knowledge_factory_historical_depth",
        "insufficient": not pe_vals,
    }
    hd_store.put_pack(e if not as_of else f"{e}@{as_of}", pack)
    if as_of is None:
        hd_store.put_pack(e, pack)
    return pack
