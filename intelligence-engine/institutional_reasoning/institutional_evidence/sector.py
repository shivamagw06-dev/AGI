"""Module 3 — Sector Intelligence.

Produce sector PE / EV / ROIC / growth / margins / valuation percentiles.
Example: Nifty IT → Sector PE → Historical PE → Premium → Position.
"""

from __future__ import annotations

from typing import Any

from institutional_reasoning.institutional_evidence.analytics import analyse_series
from institutional_reasoning.institutional_evidence.historical import produce_metric_history
from institutional_reasoning.institutional_evidence.peer import produce_peer_intelligence
from institutional_reasoning.institutional_evidence.provenance import metric_provenance, now_iso
from institutional_reasoning.institutional_evidence.quality import score_metric
from institutional_reasoning.institutional_evidence.seeds import sector_meta

SECTOR_VERSION = "sector-intelligence-v1.0.0"


def produce_sector_intelligence(entity_id: str) -> dict[str, Any]:
    eid = str(entity_id or "").upper()
    meta = sector_meta(eid)
    as_of = now_iso()
    company_pack: dict[str, Any] | None = None

    # Company → resolve via peer pack sector
    if not meta:
        try:
            from peer_intelligence.peer_database.store import find_pack_for_ticker, normalize_ticker

            pack = find_pack_for_ticker(normalize_ticker(eid))
            if pack:
                company_pack = pack
                meta = {
                    "sector": pack.get("sector"),
                    "pack_id": pack.get("pack_id"),
                    "peer_universe": pack.get("direct_universe") or [],
                    "pe_series": None,
                    "entity_type": "Company",
                    "display_name": eid,
                }
        except Exception:
            meta = None

    if not meta:
        return {
            "entity": eid,
            "found": False,
            "validated": False,
            "sector_pe": None,
            "sector_version": SECTOR_VERSION,
            "reason": "sector_unmapped",
        }

    # Sector PE series: prefer index seed for the sector, never the company's own PE.
    series = meta.get("pe_series")
    if not series:
        sector_key = str(meta.get("sector") or "")
        # Map sector → index seed
        from institutional_reasoning.institutional_evidence.seeds import (
            NIFTYIT_PE_SERIES,
            SECTOR_ENTITY_MAP,
        )

        if sector_key == "it_services" or meta.get("pack_id") == "it_services_v1":
            series = dict(NIFTYIT_PE_SERIES)
        else:
            for _idx, sm in SECTOR_ENTITY_MAP.items():
                if sm.get("sector") == sector_key and sm.get("pe_series"):
                    series = dict(sm["pe_series"])
                    break

    analytics = analyse_series(series)
    peer = produce_peer_intelligence(eid)
    hist = produce_metric_history(eid, "PE")

    sector_pe = None
    if analytics.get("found"):
        sector_pe = analytics.get("latest")
    elif peer.get("found"):
        sector_pe = peer.get("peer_pe")

    premium = None
    if analytics.get("found") and analytics.get("average") and sector_pe:
        premium = round((sector_pe / analytics["average"] - 1.0) * 100.0, 2)

    quality = score_metric(
        value=sector_pe,
        entity_id=eid,
        metric_entity=eid,
        provider="sector_engine",
        as_of=as_of,
        series_n=int(analytics.get("n") or 0),
        expected_n=10,
        data_class="institutional_seed" if series else "missing",
        validated=bool(analytics.get("found") or peer.get("found")),
        consistency_ok=True,
    )
    validated = bool(quality.get("accept_for_framework") and sector_pe is not None)
    provenance = metric_provenance(
        field="sector_pe",
        value=sector_pe,
        entity_id=eid,
        provider="sector_engine",
        method="index_series_or_peer_median",
        validated=validated,
        quality=quality.get("score"),
        as_of=as_of,
        data_class="institutional_seed",
        extra={"sector": meta.get("sector"), "pack_id": meta.get("pack_id")},
    )

    # Constituent quality metrics from peer pack when available
    sector_roic = None
    sector_growth = None
    sector_margins = None
    try:
        from peer_intelligence.percentile.engine import percentiles_for
        from peer_intelligence.peer_database.store import normalize_ticker

        if meta.get("entity_type") == "Index":
            subject = normalize_ticker((meta.get("peer_universe") or ["INFY"])[0])
        else:
            subject = normalize_ticker(eid)
        pct = percentiles_for(subject, universe="direct")
        by_m = {r["metric"]: r for r in pct.get("percentiles") or []}
        if "ROIC" in by_m:
            sector_roic = by_m["ROIC"].get("median")
        if "Revenue_Growth" in by_m:
            sector_growth = by_m["Revenue_Growth"].get("median")
        for mk in ("EBIT_Margin", "Operating_Margin"):
            if mk in by_m:
                sector_margins = by_m[mk].get("median")
                break
    except Exception:
        pass

    _ = company_pack  # reserved for future pack-native sector aggregates
    return {
        "entity": eid,
        "found": True,
        "sector": meta.get("sector"),
        "display_name": meta.get("display_name") or eid,
        "entity_type": meta.get("entity_type") or "Company",
        "sector_pe": sector_pe,
        "sector_ev": None,  # transparent until EV series seeded
        "sector_roic": sector_roic,
        "sector_growth": sector_growth,
        "sector_margins": sector_margins,
        "historical_pe": hist.get("historical_average"),
        "historical_percentile": hist.get("historical_percentile"),
        "premium_vs_history_pct": premium
        if premium is not None
        else (
            (hist.get("analytics") or {}).get("premium_vs_average_pct")
            if isinstance(hist.get("analytics"), dict)
            else None
        ),
        "position": {
            "historical_percentile": hist.get("historical_percentile"),
            "peer_percentile": peer.get("peer_percentile"),
            "sector_rank": peer.get("sector_rank"),
        },
        "valuation_percentiles": {
            "historical": hist.get("historical_percentile"),
            "peer": peer.get("peer_percentile"),
        },
        "series": series or {},
        "analytics": analytics,
        "validated": validated,
        "quality": quality,
        "provenance": provenance,
        "as_of": as_of,
        "sector_version": SECTOR_VERSION,
    }
