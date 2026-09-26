"""Company ↔ macro knowledge links (knowledge only)."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.producers.impacts import relationship, shock_impact, usd_strength_it_impact
from knowledge_factory.macro_intelligence.producers.regime import classify_current
from knowledge_factory.macro_intelligence.schema import IMI_VERSION

def _company_sector_map() -> dict[str, str]:
    """Compatibility map: symbol → macro affinity sector (never fabricate)."""
    out: dict[str, str] = {}
    try:
        from knowledge_factory.nifty500_universe import NIFTY_500

        for sym in NIFTY_500:
            aff = _resolve_sector(sym)
            if aff:
                out[sym.upper()] = aff
    except Exception:
        pass
    if not out:
        try:
            from knowledge_factory.fixtures.seed import sector_map

            for sym, sector in sector_map().items():
                aff = _SECTOR_MACRO_AFFINITY.get(str(sector).lower(), str(sector).lower())
                out[str(sym).upper()] = aff
        except Exception:
            pass
    return out


# Backward-compatible export used by portfolio macro exposure.
COMPANY_SECTOR: dict[str, str] = {}


def _refresh_company_sector() -> dict[str, str]:
    global COMPANY_SECTOR
    COMPANY_SECTOR = _company_sector_map()
    return COMPANY_SECTOR


# Macro drivers every company should surface (Track 1 institutional depth).
_COMPANY_MACRO_DRIVERS = (
    "interest_rates",  # rate sensitivity
    "usd",             # FX sensitivity
    "oil",             # commodity sensitivity
    "inflation",       # inflation sensitivity
    "gdp",             # GDP sensitivity (via ISI soft-read / industrials proxy)
)

# Map KF / seed sector labels → macro relationship keys used by impacts._REL / ISI.
_SECTOR_MACRO_AFFINITY: dict[str, str] = {
    "it_services": "it_services",
    "banks": "banks",
    "bank": "banks",
    "nbfc": "nbfc",
    "insurance": "insurance",
    "capital_markets": "nbfc",
    "auto": "auto",
    "fmcg": "fmcg",
    "pharma": "pharma",
    "metals": "metals",
    "utilities": "utilities",
    "power": "utilities",
    "real_estate": "real_estate",
    "oil_gas": "oil_gas",
    "energy": "oil_gas",
    "energy_conglomerate": "oil_gas",
    "chemicals": "chemicals",
    "specialty_chem": "chemicals",
    "consumer": "consumer",
    "consumer_durables": "consumer",
    "consumer_internet": "consumer",
    "retail": "consumer",
    "healthcare": "consumer",
    "industrials": "industrials",
    "infrastructure": "utilities",
    "telecom": "utilities",
    "aviation": "logistics",
    "logistics": "logistics",
    "cement": "real_estate",
    "diversified": "industrials",
    "conglomerate": "oil_gas",
}


def _resolve_sector(symbol: str) -> str | None:
    try:
        from knowledge_factory.fixtures.seed import sector_map

        raw = sector_map().get(symbol.upper())
    except Exception:
        raw = None
    if not raw:
        try:
            from knowledge_factory.nifty500_universe import NIFTY_500_SECTOR

            raw = NIFTY_500_SECTOR.get(symbol.upper())
        except Exception:
            raw = None
    if not raw:
        return None
    key = str(raw).strip().lower()
    # Prefer canonical ISI alias when available.
    try:
        from knowledge_factory.sector_intelligence.schema import canonicalize

        canon = canonicalize(key)
        if canon:
            # Remap ISI keys onto impact relationship vocabulary.
            return _SECTOR_MACRO_AFFINITY.get(canon, _SECTOR_MACRO_AFFINITY.get(key, canon))
    except Exception:
        pass
    return _SECTOR_MACRO_AFFINITY.get(key, key)


def company_macro_link(symbol: str) -> dict[str, Any]:
    if not COMPANY_SECTOR:
        _refresh_company_sector()
    sector = _resolve_sector(symbol) or COMPANY_SECTOR.get(symbol.upper())
    classified = classify_current()
    regimes = list(classified.get("active_regimes") or [])
    drivers: list[str] = []
    sensitivity: list[dict[str, Any]] = []
    risks: list[str] = []
    rate_sensitivity = None
    fx_sensitivity = None
    commodity_sensitivity = None
    gdp_sensitivity = None
    inflation_sensitivity = None

    if sector:
        for macro in _COMPANY_MACRO_DRIVERS:
            # GDP is not in impacts._REL — soft-read via industrials/ISI proxy key.
            rel_macro = "interest_rates" if macro == "gdp" else macro
            # For GDP, prefer ISI gdp_growth via industrials-style relationship soft path.
            if macro == "gdp":
                try:
                    from knowledge_factory.sector_intelligence.macro_map import macro_relationships

                    isi = macro_relationships(sector)
                    score = int((isi.get("relationships") or {}).get("gdp_growth") or 0)
                    if score != 0:
                        rel = {
                            "found": True,
                            "direction": 1 if score > 0 else -1,
                            "strength": abs(score),
                            "confidence": 0.7,
                            "historical_validation": "isi_macro_map",
                        }
                    else:
                        rel = relationship("interest_rates", sector)  # weak proxy only if missing
                        if rel.get("found"):
                            rel = {**rel, "historical_validation": "rate_proxy_for_gdp", "strength": 1}
                except Exception:
                    rel = {"found": False}
            else:
                rel = relationship(rel_macro, sector)
            if not rel.get("found"):
                continue
            drivers.append(macro)
            entry = {
                "macro": macro,
                "sector": sector,
                "direction": rel.get("direction"),
                "strength": rel.get("strength"),
                "confidence": rel.get("confidence"),
                "historical_validation": rel.get("historical_validation"),
            }
            sensitivity.append(entry)
            if macro == "interest_rates":
                rate_sensitivity = entry
            elif macro == "usd":
                fx_sensitivity = entry
            elif macro == "oil":
                commodity_sensitivity = entry
            elif macro == "gdp":
                gdp_sensitivity = entry
            elif macro == "inflation":
                inflation_sensitivity = entry
            if rel.get("direction", 0) < 0 and float(rel.get("strength") or 0) >= 1:
                risks.append(f"{macro}_adverse_for_{sector}")

    oil = shock_impact("oil", 0.30)
    usd = usd_strength_it_impact()
    link = {
        "link_type": "company_macro",
        "symbol": symbol.upper(),
        "sector_affinity": sector,
        "macro_sensitivity": sensitivity,
        # Explicit Track-1 institutional depth fields
        "rate_sensitivity": rate_sensitivity,
        "fx_sensitivity": fx_sensitivity,
        "commodity_sensitivity": commodity_sensitivity,
        "gdp_sensitivity": gdp_sensitivity,
        "inflation_sensitivity": inflation_sensitivity,
        "macro_drivers": drivers,
        "macro_risk": risks,
        "historical_macro_behaviour": {
            "oil_shock_proxy": oil.get("company_impacts"),
            "usd_strength_proxy": usd if sector == "it_services" else None,
        },
        "historical_regime_performance": {
            "active_regimes": regimes,
            "primary_regime": classified.get("primary_regime"),
            "note": "Knowledge overlay only; no portfolio reasoning changes.",
        },
        "imi_version": IMI_VERSION,
        "knowledge_only": True,
        "insufficient": sector is None or len(sensitivity) == 0,
        "reason": None
        if sector and sensitivity
        else ("no_sector_affinity_mapping" if sector is None else "macro_history_unavailable"),
        "fabricated": False,
    }
    return link


def compile_company_links(symbols: list[str] | None = None) -> dict[str, Any]:
    if symbols is None:
        try:
            from knowledge_factory.nifty500_universe import NIFTY_500

            symbols = list(NIFTY_500)
        except Exception:
            from knowledge_factory.fixtures.seed import sector_map

            symbols = list(sector_map().keys())
    links = {s.upper(): company_macro_link(s) for s in symbols}
    payload = {
        "kind": "company_macro",
        "n": len(links),
        "links": links,
        "imi_version": IMI_VERSION,
        "knowledge_only": True,
    }
    imi_store.put_links("company", payload)
    return payload
