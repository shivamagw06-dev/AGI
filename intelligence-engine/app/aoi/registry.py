"""Canonical company registry — one identity per company, alias-aware."""

from __future__ import annotations

import re
from typing import Iterable

from app.aoi.models import CompanyRegistryEntry
from app.kc.universes import NIFTY_50, NIFTY_NEXT_50, NIFTY_500_EXTENSION


_ALIAS_EXTRA: dict[str, list[str]] = {
    "RELIANCE": ["RIL", "Reliance", "Reliance Industries Ltd", "Reliance Industries Limited"],
    "TCS": ["Tata Consultancy", "Tata Consultancy Services Ltd"],
    "INFY": ["Infosys Ltd", "Infosys Limited", "Infosys Technologies"],
    "HDFCBANK": ["HDFC Bank Ltd", "HDFC"],
    "ICICIBANK": ["ICICI Bank Ltd", "ICICI"],
    "HINDUNILVR": ["HUL", "Hindustan Unilever Ltd", "Hindustan Unilever Limited"],
    "SBIN": ["SBI", "State Bank"],
    "BHARTIARTL": ["Airtel", "Bharti", "Bharti Airtel Ltd"],
    "LT": ["L&T", "Larsen and Toubro", "Larsen & Toubro Ltd"],
    "M&M": ["Mahindra", "M and M", "Mahindra and Mahindra"],
}


def _slug(name: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (name or "").lower()).strip("_")
    return s or "company"


class CompanyRegistry:
    """Permanent canonical company registry. Connectors reference this only."""

    def __init__(self) -> None:
        self._by_id: dict[str, CompanyRegistryEntry] = {}
        self._by_symbol: dict[str, str] = {}
        self._by_alias: dict[str, str] = {}

    def seed_default_universes(self) -> dict[str, int]:
        n = 0
        for row in NIFTY_50:
            self.upsert_from_universe(row, universe="nifty_50")
            n += 1
        for row in NIFTY_NEXT_50:
            self.upsert_from_universe(row, universe="nifty_next_50")
            n += 1
        for row in NIFTY_500_EXTENSION:
            self.upsert_from_universe(row, universe="nifty_500")
            n += 1
        return {
            "entries": len(self._by_id),
            "seeded_rows": n,
            "nifty_50": sum(1 for e in self._by_id.values() if e.universe == "nifty_50"),
            "nifty_next_50": sum(1 for e in self._by_id.values() if e.universe == "nifty_next_50"),
            "nifty_500": sum(1 for e in self._by_id.values() if e.universe == "nifty_500"),
        }

    def upsert_from_universe(self, row: dict[str, str], *, universe: str) -> CompanyRegistryEntry:
        symbol = (row.get("ticker") or "").upper()
        name = row.get("name") or symbol
        company_id = f"co_{symbol.lower().replace('&', 'and').replace('-', '_')}"
        aliases = list(dict.fromkeys([name, symbol, *(_ALIAS_EXTRA.get(symbol) or [])]))
        sector = row.get("sector") or ""
        ir = f"https://www.example-ir.invalid/{symbol.lower()}/investors"
        entry = CompanyRegistryEntry(
            company_id=company_id,
            company_name=name,
            nse_symbol=symbol,
            sector=sector,
            industry=sector,
            website=f"https://www.example-ir.invalid/{symbol.lower()}",
            investor_relations_url=ir,
            exchange_urls=[
                f"https://www.nseindia.com/get-quotes/equity?symbol={symbol}",
                f"https://www.bseindia.com/stock-share-price/symbol/{symbol}",
            ],
            annual_report_urls=[f"{ir}/annual-reports"],
            quarterly_result_urls=[f"{ir}/financial-results"],
            presentation_urls=[f"{ir}/presentations"],
            earnings_call_urls=[f"{ir}/earnings-calls"],
            sustainability_report_urls=[f"{ir}/esg"],
            aliases=aliases,
            universe=universe,
            metadata={"source": "aoi_universe_seed"},
        )
        return self.upsert(entry)

    def upsert(self, entry: CompanyRegistryEntry) -> CompanyRegistryEntry:
        existing = self._by_id.get(entry.company_id)
        if existing and existing.nse_symbol == entry.nse_symbol:
            # Merge aliases; never duplicate companies
            merged_aliases = list(dict.fromkeys([*(existing.aliases or []), *(entry.aliases or [])]))
            data = existing.model_dump()
            for k, v in entry.model_dump().items():
                if k == "aliases":
                    continue
                if v not in ("", None, [], {}):
                    data[k] = v
            data["aliases"] = merged_aliases
            entry = CompanyRegistryEntry.model_validate(data)
        self._by_id[entry.company_id] = entry
        if entry.nse_symbol:
            self._by_symbol[entry.nse_symbol.upper()] = entry.company_id
        for alias in entry.aliases:
            self._by_alias[_norm(alias)] = entry.company_id
        self._by_alias[_norm(entry.company_name)] = entry.company_id
        return entry

    def get(self, company_id: str) -> CompanyRegistryEntry | None:
        return self._by_id.get(company_id)

    def by_symbol(self, symbol: str) -> CompanyRegistryEntry | None:
        cid = self._by_symbol.get((symbol or "").upper())
        return self._by_id.get(cid) if cid else None

    def resolve(self, query: str) -> CompanyRegistryEntry | None:
        q = (query or "").strip()
        if not q:
            return None
        if q in self._by_id:
            return self._by_id[q]
        by_sym = self.by_symbol(q)
        if by_sym:
            return by_sym
        cid = self._by_alias.get(_norm(q))
        return self._by_id.get(cid) if cid else None

    def list(self, *, universe: str | None = None) -> list[CompanyRegistryEntry]:
        rows = list(self._by_id.values())
        if universe:
            rows = [r for r in rows if r.universe == universe]
        return sorted(rows, key=lambda r: r.nse_symbol or r.company_name)

    def nifty50(self) -> list[CompanyRegistryEntry]:
        return self.list(universe="nifty_50")

    def all(self) -> Iterable[CompanyRegistryEntry]:
        return self._by_id.values()


def _norm(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())
