"""Entity resolution — ticker → Company + Sector + Industry + Index + Peers."""

from __future__ import annotations

from typing import Any

from app.contracts.models import EntityRefs, new_id
from app.storage.db import KaipStore

# Seed institutional map for Sprint 6.1 — expands via normalizer updates.
SEED_ENTITIES: dict[str, dict[str, Any]] = {
    "INFY": {
        "company_name": "Infosys Ltd",
        "sector": "Technology",
        "industry": "IT Services",
        "indexes": ["NIFTY50", "NIFTYIT"],
        "peers": ["TCS", "WIPRO", "HCLTECH", "TECHM"],
        "aliases": ["INFY.NS", "INFY.BO", "Infosys"],
    },
    "TCS": {
        "company_name": "Tata Consultancy Services Ltd",
        "sector": "Technology",
        "industry": "IT Services",
        "indexes": ["NIFTY50", "NIFTYIT"],
        "peers": ["INFY", "WIPRO", "HCLTECH", "TECHM"],
        "aliases": ["TCS.NS", "TCS.BO"],
    },
    "RELIANCE": {
        "company_name": "Reliance Industries Ltd",
        "sector": "Energy",
        "industry": "Oil Gas Refining Marketing",
        "indexes": ["NIFTY50"],
        "peers": ["ONGC", "BPCL", "IOC"],
        "aliases": ["RELIANCE.NS", "RELIANCE.BO"],
    },
    "HDFCBANK": {
        "company_name": "HDFC Bank Ltd",
        "sector": "Financials",
        "industry": "Private Sector Bank",
        "indexes": ["NIFTY50", "NIFTYBANK"],
        "peers": ["ICICIBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
        "aliases": ["HDFCBANK.NS", "HDFCBANK.BO"],
    },
    "ICICIBANK": {
        "company_name": "ICICI Bank Ltd",
        "sector": "Financials",
        "industry": "Private Sector Bank",
        "indexes": ["NIFTY50", "NIFTYBANK"],
        "peers": ["HDFCBANK", "KOTAKBANK", "AXISBANK", "SBIN"],
        "aliases": ["ICICIBANK.NS", "ICICIBANK.BO", "ICICI"],
    },
}


class EntityResolver:
    def __init__(self, store: KaipStore) -> None:
        self.store = store
        self._seed()

    def _seed(self) -> None:
        for symbol, meta in SEED_ENTITIES.items():
            existing = self.store.get_entity(symbol)
            if existing:
                continue
            self.store.upsert_entity(
                company_symbol=symbol,
                company_id=f"co_{symbol.lower()}",
                company_name=meta["company_name"],
                sector=meta.get("sector"),
                industry=meta.get("industry"),
                indexes=list(meta.get("indexes") or []),
                peers=list(meta.get("peers") or []),
                aliases=list(meta.get("aliases") or []),
            )

    def resolve(self, company_symbol: str, hints: dict[str, Any] | None = None) -> EntityRefs:
        symbol = self._canonicalize_symbol(company_symbol)
        hints = hints or {}
        existing = self.store.get_entity(symbol)
        if existing:
            # Enrich from canonical hints without wiping seed relationships
            return self.store.upsert_entity(
                company_symbol=symbol,
                company_id=existing.company_id or f"co_{symbol.lower()}",
                company_name=hints.get("company_name") or existing.company_name or symbol,
                sector=hints.get("sector") or existing.sector,
                industry=hints.get("industry") or existing.industry,
                indexes=existing.indexes,
                peers=existing.peers,
                clients=existing.clients,
            )

        seed = SEED_ENTITIES.get(symbol, {})
        return self.store.upsert_entity(
            company_symbol=symbol,
            company_id=f"co_{symbol.lower()}_{new_id()[:8]}",
            company_name=hints.get("company_name") or seed.get("company_name") or symbol,
            sector=hints.get("sector") or seed.get("sector"),
            industry=hints.get("industry") or seed.get("industry"),
            indexes=list(seed.get("indexes") or []),
            peers=list(seed.get("peers") or []),
            aliases=list(seed.get("aliases") or []),
        )

    def _canonicalize_symbol(self, value: str) -> str:
        symbol = (value or "").upper().strip()
        for suffix in (".NS", ".BO", ".NSE", ".BSE"):
            if symbol.endswith(suffix):
                symbol = symbol[: -len(suffix)]
        # alias reverse lookup
        for canonical, meta in SEED_ENTITIES.items():
            aliases = {a.upper() for a in meta.get("aliases") or []}
            if symbol == canonical or symbol in aliases:
                return canonical
        return symbol
