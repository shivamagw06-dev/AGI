"""Entity resolution for historical objects — company / sector / industry / index / period."""

from __future__ import annotations

from typing import Any

from app.contracts.models import EntityRefs, PeriodKind, Source
from app.storage.db import HipStore

# Seed sector map for Sprint 8.1
SECTOR_MAP = {
    "INFY": ("Technology", "information_technology", "IT Services", ["NIFTY50", "NIFTY IT"]),
    "TCS": ("Technology", "information_technology", "IT Services", ["NIFTY50", "NIFTY IT"]),
    "RELIANCE": ("Energy", "energy", "Oil & Gas", ["NIFTY50"]),
    "HDFCBANK": ("Financials", "financials", "Private Sector Bank", ["NIFTY50", "NIFTY BANK"]),
}


class HistoricalEntityResolver:
    def __init__(self, store: HipStore) -> None:
        self.store = store

    def resolve(self, canonical: dict[str, Any], *, source: Source) -> EntityRefs:
        symbol = (canonical.get("company_symbol") or "").upper()
        seed = SECTOR_MAP.get(symbol, ("Unknown", "unknown", "Unknown", ["NIFTY50"]))
        sector = canonical.get("sector") or seed[0]
        sector_key = canonical.get("sector_key") or seed[1]
        industry = canonical.get("industry") or seed[2]
        indices = list(canonical.get("index_membership") or seed[3])
        name = canonical.get("company_name")
        period = canonical.get("time_period") or canonical.get("effective_date")
        period_kind = None
        pk = canonical.get("period_kind")
        if pk:
            try:
                period_kind = PeriodKind(pk)
            except Exception:
                period_kind = PeriodKind.POINT_IN_TIME

        self.store.upsert_entity(
            company_symbol=symbol,
            company_name=name,
            sector=sector,
            sector_key=sector_key,
            industry=industry,
            index_membership=indices,
        )
        _ = source
        return EntityRefs(
            company_symbol=symbol,
            company_name=name,
            sector=sector,
            sector_key=sector_key,
            industry=industry,
            index_membership=indices,
            time_period=period,
            period_kind=period_kind,
        )
