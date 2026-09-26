"""Sector History — sector-specific KPI panels from peer living packs."""

from __future__ import annotations

from typing import Any

from company_memory.schema import SECTOR_KPI_KEYS


def sector_key_for(entity: str) -> str:
    try:
        from valuation_intelligence.peers import resolve_peers

        meta = resolve_peers(entity)
        blob = " ".join(
            str(meta.get(k) or "").lower() for k in ("industry", "sub_industry", "sector")
        )
        if "bank" in blob:
            return "banks"
        if "information technology" in blob or "it services" in blob:
            return "it_services"
        if "pharma" in blob or "health" in blob:
            return "pharma"
        if "cement" in blob:
            return "cement"
        if "power" in blob or "utilit" in blob:
            return "power"
        if "auto" in blob:
            return "auto"
        if "paint" in blob:
            return "paints"
        if "defence" in blob or "defense" in blob or "aerospace" in blob:
            return "defence"
        if "internet" in blob or "catalogue" in blob:
            return "consumer_internet"
        if "energy" in blob or "oil" in blob:
            return "energy_conglomerate"
        return "unknown"
    except Exception:
        return "unknown"


def derive_sector_history(entity: str) -> dict[str, Any]:
    key = entity.upper()
    sector_key = sector_key_for(key)
    wanted = set(SECTOR_KPI_KEYS.get(sector_key, ()))
    bank_core = {"CASA", "NIM", "GNPA", "NNPA", "PCR", "CET1", "ROE", "Deposit_Growth"}
    series_out: dict[str, Any] = {}
    pack_id = None
    try:
        from peer_intelligence.peer_database.store import find_pack_for_ticker

        pack = find_pack_for_ticker(key)
        if not pack:
            return {
                "available": sector_key != "unknown",
                "entity": key,
                "sector_key": sector_key,
                "pack_id": None,
                "kpi_keys": sorted(wanted),
                "series": {},
                "lineage": [],
            }
        pack_id = pack.get("pack_id")
        for s in pack.get("series") or []:
            metric = s.get("metric")
            ent = str(s.get("entity") or "").upper()
            pts = s.get("points") or {}
            if not metric or not pts:
                continue
            keep = (not wanted and sector_key == "banks" and metric in bank_core) or (
                metric in wanted or (sector_key == "banks" and metric in bank_core)
            )
            if not keep:
                continue
            if ent == key:
                series_out[metric] = {
                    "points": pts,
                    "unit": s.get("unit"),
                    "source": s.get("source"),
                    "data_class": s.get("data_class"),
                    "entity": ent,
                }
            else:
                # Peer panel retained for sector context
                series_out.setdefault(
                    f"peer:{ent}:{metric}",
                    {
                        "points": pts,
                        "source": s.get("source"),
                        "entity": ent,
                        "metric": metric,
                        "note": "peer_panel",
                    },
                )
    except Exception:
        pass

    return {
        "available": bool(series_out) or sector_key != "unknown",
        "entity": key,
        "sector_key": sector_key,
        "pack_id": pack_id,
        "kpi_keys": sorted(wanted),
        "series": series_out,
        "lineage": [{"source": "peer_intelligence.living_pack", "pack_id": pack_id}],
    }
