"""Configurable peer registry — not hard-coded into valuation math.

Primary source of truth for P2.2 peer universes. Also soft-resolves via
existing peer_intelligence living packs when present.
"""

from __future__ import annotations

from typing import Any

# Configurable registry: sector / industry / sub_industry + primary/secondary peers.
PEER_REGISTRY: dict[str, dict[str, Any]] = {
    "HDFCBANK": {
        "sector": "Financials",
        "industry": "Banks",
        "sub_industry": "Private Sector Bank",
        "primary": ["ICICIBANK", "AXISBANK", "KOTAKBANK", "INDUSINDBK"],
        "secondary": ["AUBANK", "FEDERALBNK", "IDFCFIRSTB", "BANDHANBNK", "SBIN"],
    },
    "ICICIBANK": {
        "sector": "Financials",
        "industry": "Banks",
        "sub_industry": "Private Sector Bank",
        "primary": ["HDFCBANK", "AXISBANK", "KOTAKBANK", "INDUSINDBK"],
        "secondary": ["SBIN", "AUBANK", "FEDERALBNK"],
    },
    "TCS": {
        "sector": "Information Technology",
        "industry": "IT Services",
        "sub_industry": "Tier-1 IT Services",
        "primary": ["INFY", "HCLTECH", "WIPRO", "TECHM", "LTIM"],
        "secondary": ["PERSISTENT", "COFORGE", "MPHASIS"],
    },
    "INFY": {
        "sector": "Information Technology",
        "industry": "IT Services",
        "sub_industry": "Tier-1 IT Services",
        "primary": ["TCS", "HCLTECH", "WIPRO", "TECHM", "LTIM"],
        "secondary": ["PERSISTENT", "COFORGE"],
    },
    "ETERNAL": {
        "sector": "Consumer Discretionary",
        "industry": "Internet & Catalogue Retail",
        "sub_industry": "Consumer Internet",
        "primary": ["SWIGGY", "NYKAA", "PAYTM"],
        "secondary": ["ZOMATO"],  # alias handling elsewhere
    },
    "ULTRACEMCO": {
        "sector": "Materials",
        "industry": "Cement",
        "sub_industry": "Cement & Aggregates",
        "primary": ["SHREECEM", "AMBUJACEM", "ACC", "DALBHARAT", "RAMCOCEM"],
        "secondary": ["JKCEMENT", "NUVOCO"],
    },
    "ASIANPAINT": {
        "sector": "Materials",
        "industry": "Specialty Chemicals / Paints",
        "sub_industry": "Decorative Paints",
        "primary": ["BERGEPAINT", "INDIGOPNTS", "KANSAINER"],
        "secondary": ["AKZOINDIA"],
    },
    "SUNPHARMA": {
        "sector": "Health Care",
        "industry": "Pharmaceuticals",
        "sub_industry": "Diversified Pharma",
        "primary": ["DRREDDY", "CIPLA", "AUROPHARMA", "LUPIN"],
        "secondary": ["TORNTPHARM", "ALKEM", "BIOCON"],
    },
    "NTPC": {
        "sector": "Utilities",
        "industry": "Electric Utilities",
        "sub_industry": "Power Generation",
        "primary": ["POWERGRID", "TATAPOWER", "ADANIPOWER", "NHPC"],
        "secondary": ["SJVN", "TORNTPOWER"],
    },
    "HAL": {
        "sector": "Industrials",
        "industry": "Aerospace & Defence",
        "sub_industry": "Defence OEM",
        "primary": ["BEL", "BHEL", "MAZDOCK", "GRSE"],
        "secondary": ["COCHINSHIP", "BEML"],
    },
    "TMPV": {
        "sector": "Consumer Discretionary",
        "industry": "Automobiles",
        "sub_industry": "Passenger Vehicles",
        "primary": ["M&M", "MARUTI", "TATAMOTORS", "BAJAJ-AUTO"],
        "secondary": ["EICHERMOT", "HEROMOTOCO"],
    },
    "RELIANCE": {
        "sector": "Energy / Conglomerate",
        "industry": "Oil Gas & Consumable Fuels / Diversified",
        "sub_industry": "Integrated Energy & Retail",
        "primary": ["ONGC", "IOC", "BPCL", "GAIL"],
        "secondary": ["HINDPETRO", "PETRONET"],
    },
}


def resolve_peers(ticker: str) -> dict[str, Any]:
    """Resolve peer universe: registry first, then peer_intelligence packs."""
    key = (ticker or "").upper().replace(".NS", "").replace(".BO", "")
    if key == "ZOMATO":
        key = "ETERNAL"
    if key == "TATAMOTORS":
        # NSE/Yahoo quote symbol for the passenger-vehicles franchise is TMPV
        key = "TMPV"
    row = PEER_REGISTRY.get(key)
    source = "valuation_peer_registry"
    if row:
        primary = list(row.get("primary") or [])
        secondary = list(row.get("secondary") or [])
        meta = {
            "sector": row.get("sector"),
            "industry": row.get("industry"),
            "sub_industry": row.get("sub_industry"),
        }
    else:
        primary, secondary, meta = [], [], {}
        source = "unresolved"

    # Soft overlay from living PIL packs
    pil_pack = None
    try:
        from peer_intelligence.peer_database.store import find_pack_for_ticker

        pil_pack = find_pack_for_ticker(key)
    except Exception:
        pil_pack = None
    if pil_pack:
        direct = [t for t in (pil_pack.get("direct_universe") or []) if t != key]
        if not primary:
            primary = direct
            source = "peer_intelligence_pack"
        else:
            # Fill gaps only
            for t in direct:
                if t not in primary and t not in secondary:
                    secondary.append(t)
        meta.setdefault("sector", pil_pack.get("sector"))
        meta["pil_pack_id"] = pil_pack.get("pack_id")

    # Deduplicate preserving order
    def _uniq(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out = []
        for x in xs:
            u = x.upper()
            if u == key or u in seen:
                continue
            seen.add(u)
            out.append(u)
        return out

    primary = _uniq(primary)
    secondary = _uniq([t for t in secondary if t not in primary])
    return {
        "ticker": key,
        "resolved": bool(primary),
        "source": source,
        "sector": meta.get("sector"),
        "industry": meta.get("industry"),
        "sub_industry": meta.get("sub_industry"),
        "primary_peers": primary,
        "secondary_peers": secondary,
        "peer_universe": primary + secondary,
        "pil_pack_id": meta.get("pil_pack_id"),
    }
