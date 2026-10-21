"""Module 2 — Peer Intelligence.

Peer Engine computes universe, median, mean, percentiles, premium,
discount, ranking, sector rank. Frameworks never calculate peers.
"""

from __future__ import annotations

from statistics import mean, median
from typing import Any

from institutional_reasoning.institutional_evidence.provenance import metric_provenance, now_iso
from institutional_reasoning.institutional_evidence.quality import score_metric
from institutional_reasoning.institutional_evidence.seeds import IT_PE_SERIES, BANK_PE_SERIES, sector_meta

PEER_VERSION = "peer-intelligence-producer-v1.0.0"


def _universe_for(entity_id: str) -> tuple[list[str], str, str]:
    """Return (tickers, sector, pack_id)."""
    eid = str(entity_id or "").upper()
    meta = sector_meta(eid)
    if meta:
        return list(meta.get("peer_universe") or []), str(meta.get("sector") or ""), str(
            meta.get("pack_id") or ""
        )
    try:
        from peer_intelligence.peer_selector.select import select_universe
        from peer_intelligence.peer_database.store import normalize_ticker

        t = normalize_ticker(eid)
        uni = select_universe(t, include_global=False)
        members = list(
            uni.get("analysis_universe")
            or uni.get("direct_universe")
            or uni.get("direct")
            or uni.get("universe")
            or []
        )
        if not members and isinstance(uni.get("tickers"), list):
            members = list(uni["tickers"])
        # Fallback: pack direct_universe
        if not members:
            from peer_intelligence.peer_database.store import find_pack_for_ticker

            pack = find_pack_for_ticker(t)
            if pack:
                members = list(pack.get("direct_universe") or [])
                return members, str(pack.get("sector") or ""), str(pack.get("pack_id") or "")
        return members, str(uni.get("sector") or ""), str(uni.get("pack_id") or "")
    except Exception:
        return [], "", ""


def _latest_pe(ticker: str) -> float | None:
    # Prefer institutional PE seeds (IT / banks), else PIL PE series
    if ticker in IT_PE_SERIES:
        pts = IT_PE_SERIES[ticker]
        return float(list(pts.values())[-1]) if pts else None
    if ticker in BANK_PE_SERIES:
        pts = BANK_PE_SERIES[ticker]
        return float(list(pts.values())[-1]) if pts else None
    try:
        from peer_intelligence.historical.series import history_for

        hist = history_for(ticker, "PE")
        for row in hist.get("series") or []:
            pts = row.get("points") or {}
            if pts:
                return float(list(pts.values())[-1])
    except Exception:
        pass
    return None


def produce_peer_intelligence(
    entity_id: str,
    *,
    current_pe: float | None = None,
) -> dict[str, Any]:
    eid = str(entity_id or "").upper()
    members, sector, pack_id = _universe_for(eid)
    as_of = now_iso()

    values: dict[str, float] = {}
    for t in members:
        v = _latest_pe(t)
        if v is not None and v > 0:
            values[t] = v

    if not values:
        return {
            "entity": eid,
            "found": False,
            "peer_universe": members,
            "sector": sector,
            "pack_id": pack_id,
            "validated": False,
            "peer_pe": None,
            "peer_version": PEER_VERSION,
            "reason": "no_peer_pe_series",
        }

    nums = list(values.values())
    peer_median = float(median(nums))
    peer_mean = float(mean(nums))
    ordered = sorted(values.items(), key=lambda kv: kv[1])
    # Ranking: 1 = cheapest (lowest PE)
    rank_map = {t: i + 1 for i, (t, _) in enumerate(ordered)}
    subject_pe = current_pe
    if subject_pe is None and eid in values:
        subject_pe = values[eid]
    # For indices, subject may not be in peer values — use current_pe arg
    premium = None
    discount = None
    percentile = None
    sector_rank = None
    if subject_pe is not None and peer_median:
        premium = round((subject_pe / peer_median - 1.0) * 100.0, 2)
        discount = round((peer_median / subject_pe - 1.0) * 100.0, 2)
        below = sum(1 for v in nums if v < subject_pe)
        percentile = round(100.0 * below / len(nums), 2)
    if eid in rank_map:
        sector_rank = rank_map[eid]
    elif subject_pe is not None:
        # Index rank among constituents by PE
        inserted = sorted(nums + [subject_pe])
        sector_rank = inserted.index(subject_pe) + 1

    quality = score_metric(
        value=peer_median,
        entity_id=eid,
        metric_entity=eid,
        provider="peer_engine",
        as_of=as_of,
        series_n=len(values),
        expected_n=max(4, len(members) or 4),
        data_class="institutional_seed",
        validated=len(values) >= 3,
        consistency_ok=True,
    )
    validated = bool(quality.get("accept_for_framework"))
    provenance = metric_provenance(
        field="peer_pe",
        value=round(peer_median, 4),
        entity_id=eid,
        provider="peer_engine",
        method="universe_median",
        validated=validated,
        quality=quality.get("score"),
        as_of=as_of,
        data_class="institutional_seed",
        extra={
            "universe": sorted(values.keys()),
            "n": len(values),
            "excluded": [t for t in members if t not in values],
        },
    )

    return {
        "entity": eid,
        "found": True,
        "peer_universe": members,
        "universe_values": values,
        "sector": sector,
        "pack_id": pack_id,
        "median": round(peer_median, 4),
        "mean": round(peer_mean, 4),
        "percentiles": {
            "p25": round(sorted(nums)[max(0, len(nums) // 4)], 4),
            "p50": round(peer_median, 4),
            "p75": round(sorted(nums)[min(len(nums) - 1, (3 * len(nums)) // 4)], 4),
        },
        "premium_vs_peers_pct": premium,
        "discount_vs_peers_pct": discount,
        "peer_percentile": percentile,
        "ranking": rank_map,
        "sector_rank": sector_rank,
        "peer_pe": round(peer_median, 4),
        "peer_median_pe": round(peer_median, 4),
        "validated": validated,
        "quality": quality,
        "provenance": provenance,
        "as_of": as_of,
        "peer_version": PEER_VERSION,
    }
