"""Assemble Sector Forecast Bundle from Phase 11 AGI-owned knowledge only."""

from __future__ import annotations

from typing import Any

from sector_forecast_intelligence import traces
from sector_forecast_intelligence.schema import SUPPORTED_SECTORS, SectorForecastBundle

SECTOR_KEY_MAP: dict[str, str] = {
    "Banking": "banking",
    "IT Services": "it_services",
    "FMCG": "fmcg",
    "Auto": "auto",
    "Capital Goods": "capital_goods",
    "Pharma": "pharma",
}


def normalize_sector(name: str | None) -> str | None:
    if not name:
        return None
    raw = str(name).strip()
    for s in SUPPORTED_SECTORS:
        if raw.lower() == s.lower():
            return s
    aliases = {
        "banks": "Banking",
        "banking": "Banking",
        "financials": "Banking",
        "it": "IT Services",
        "it_services": "IT Services",
        "information_technology": "IT Services",
        "fmcg": "FMCG",
        "auto": "Auto",
        "automobiles": "Auto",
        "capital_goods": "Capital Goods",
        "capital goods": "Capital Goods",
        "pharma": "Pharma",
        "pharmaceuticals": "Pharma",
    }
    key = raw.lower().replace("-", "_").replace(" ", "_")
    return aliases.get(key)


def soft_current_sector(sector: str) -> dict[str, Any]:
    out: dict[str, Any] = {"sector": sector, "gateway": "CSKP_KRIG", "providers_queried": []}
    try:
        from continuous_sector_knowledge.production import sector as cskp_sector

        key = SECTOR_KEY_MAP.get(sector) or sector.lower().replace(" ", "_")
        pack = cskp_sector(key)
        if pack.get("found") and pack.get("latest"):
            latest = dict(pack["latest"])
            out["available"] = True
            out["outlook"] = latest.get("current_outlook") or latest.get("outlook")
            out["latest"] = {
                "outlook": out["outlook"],
                "revenue_trend": latest.get("revenue_trend") or latest.get("growth_drivers"),
                "margin_trend": latest.get("margin_trend"),
                "valuation": latest.get("valuation"),
                "leading_companies": latest.get("leading_companies"),
                "macro_sensitivity": latest.get("macro_sensitivity"),
                "version": latest.get("version"),
            }
            out["tips"] = {
                "Revenue Growth": None,
                "outlook": out["outlook"],
            }
            return out
    except Exception:
        pass
    out["available"] = False
    return out


def soft_historical(sector: str) -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "HSIP_KRIG", "providers_queried": []}
    try:
        from historical_sector_intelligence.production import sector as hsip_sector

        key = SECTOR_KEY_MAP.get(sector) or sector.lower().replace(" ", "_")
        pack = hsip_sector(key, limit=40)
        if pack.get("found"):
            tip["available"] = True
            tip["n"] = pack.get("n")
            tip["timeline"] = pack.get("timeline")
            tip["completeness_pct"] = (pack.get("timeline") or {}).get("completeness_pct")
            return tip
    except Exception:
        pass
    tip["available"] = False
    return tip


def soft_analogues(sector: str) -> list[dict[str, Any]]:
    try:
        from historical_sector_analogue_intelligence.production import forecast_tip

        tip = forecast_tip(sector=sector, top_k=5)
        return list(tip.get("top_analogues") or [])
    except Exception:
        return []


def soft_regime(sector: str) -> dict[str, Any]:
    try:
        from historical_sector_analogue_intelligence.production import current_regime

        pack = current_regime(sector=sector)
        return pack.get("regime") or {}
    except Exception:
        return {}


def soft_relationships(sector: str) -> list[dict[str, Any]]:
    try:
        from sector_relationship_intelligence.production import for_sector

        pack = for_sector(sector, limit=40)
        return list(pack.get("relationships") or [])
    except Exception:
        return []


def soft_macro_forecast() -> dict[str, Any]:
    """Inherit macro assumptions from MFI — never invent a parallel macro view."""
    tip: dict[str, Any] = {"gateway": "MFI_KRIG", "providers_queried": [], "inherited": False}
    try:
        from macroeconomic_forecast_intelligence.production import forecast as mfi_forecast
        from macroeconomic_forecast_intelligence.production import probability as mfi_probability

        pack = mfi_forecast(country="India", region="India")
        prob = mfi_probability(country="India")
        tip["inherited"] = True
        tip["probability_distribution"] = pack.get("probability_distribution") or prob.get(
            "distribution"
        )
        tip["confidence"] = pack.get("confidence") or prob.get("confidence")
        tip["current_regime"] = pack.get("current_regime")
        # Sample scenario indicator paths for inheritance
        scenarios = []
        for s in pack.get("scenarios") or []:
            scenarios.append(
                {
                    "scenario": s.get("scenario"),
                    "probability_pct": s.get("probability_pct"),
                    "repo_rate": s.get("repo_rate"),
                    "inflation": s.get("inflation"),
                    "gdp": s.get("gdp"),
                    "usdinr": s.get("usdinr"),
                }
            )
        tip["scenarios"] = scenarios
        tip["available"] = bool(tip["probability_distribution"] or scenarios)
    except Exception:
        tip["available"] = False
    return tip


def soft_research(sector: str) -> dict[str, Any]:
    return {
        "sector_research_office": {
            "sector": sector,
            "stance": f"Evidence-linked {sector} outlook from AGI sector stack",
            "themes": ["Growth", "Margins", "Valuation", "Policy", "Competitive position"],
        },
        "industry_reports": [f"{sector} institutional cycle notes"],
        "policy_analysis": ["Fiscal / monetary / sector reform watch"],
        "gateway": "Sector_Research_Tip",
        "providers_queried": [],
    }


def soft_monitoring(sector: str) -> list[dict[str, Any]]:
    events = [
        {"event": f"{sector} earnings season", "status": "Watching", "importance": "High"},
        {"event": "RBI MPC / policy transmission", "status": "Scheduled", "importance": "Critical"},
        {"event": "Sector valuation digest", "status": "Watching", "importance": "Medium"},
    ]
    try:
        from continuous_sector_knowledge.production import calendar

        cal = calendar(limit=20)
        for row in cal.get("events") or cal.get("calendar") or []:
            events.append(
                {
                    "event": row.get("event") or row.get("title") or "Sector calendar",
                    "status": row.get("status") or "Scheduled",
                    "importance": row.get("importance") or "Medium",
                    "source": "CSKP_calendar",
                }
            )
    except Exception:
        pass
    return events[:20]


def _completeness(
    *,
    current: dict[str, Any],
    hist: dict[str, Any],
    analogues: list[dict[str, Any]],
    relationships: list[dict[str, Any]],
    macro: dict[str, Any],
    research: dict[str, Any],
    monitoring: list[dict[str, Any]],
) -> int:
    score = 0
    if current.get("available"):
        score += 20
    if hist.get("available"):
        score += 15
    if analogues:
        score += 15
    if relationships:
        score += 15
    if macro.get("available") or macro.get("inherited"):
        score += 15
    if research:
        score += 10
    if monitoring:
        score += 10
    return min(100, score)


def assemble_bundle(*, sector: str, country: str = "India") -> SectorForecastBundle:
    sec = normalize_sector(sector) or sector
    span = traces.begin("sector_forecast_bundle", meta={"sector": sec, "country": country})
    sources: list[str] = []

    current = soft_current_sector(sec)
    if current.get("available"):
        sources.append("CSKP")
    hist = soft_historical(sec)
    if hist.get("available"):
        sources.append("HSIP")
    analogues = soft_analogues(sec)
    if analogues:
        sources.append("HSAI")
    regime = soft_regime(sec)
    relationships = soft_relationships(sec)
    if relationships:
        sources.append("SRI")
    macro = soft_macro_forecast()
    if macro.get("available") or macro.get("inherited"):
        sources.append("MFI")
    research = soft_research(sec)
    sources.append("Sector_Research_Tip")
    monitoring = soft_monitoring(sec)

    completeness = _completeness(
        current=current,
        hist=hist,
        analogues=analogues,
        relationships=relationships,
        macro=macro,
        research=research,
        monitoring=monitoring,
    )
    bundle = SectorForecastBundle(
        sector=sec,
        country=country,
        current_sector=current,
        current_regime=regime,
        historical_tip=hist,
        analogues=analogues,
        relationships=relationships,
        macro_forecast_tip=macro,
        research=research,
        monitoring=monitoring,
        completeness_pct=completeness,
        sources=sources,
        providers_queried=[],
    )
    traces.end(
        span,
        output={
            "sector": sec,
            "completeness_pct": completeness,
            "sources": sources,
            "analogue_n": len(analogues),
            "relationship_n": len(relationships),
        },
    )
    return bundle
