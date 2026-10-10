"""Assemble Macro Forecast Bundle from Phase 10 AGI-owned knowledge only."""

from __future__ import annotations

from typing import Any

from macroeconomic_forecast_intelligence import traces
from macroeconomic_forecast_intelligence.schema import MacroForecastBundle


def _num(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def soft_current_macro(*, country: str = "India") -> dict[str, Any]:
    out: dict[str, Any] = {"country": country, "gateway": "CMKP_KRIG"}
    try:
        from continuous_macro_knowledge.production import india as cmkp_india
        from continuous_macro_knowledge.production import indicator as cmkp_indicator
        from continuous_macro_knowledge.production import release_calendar

        pack = cmkp_india(limit=80)
        out["published_count"] = pack.get("n") or 0
        tips: dict[str, float | None] = {}
        for name in (
            "Repo Rate",
            "CPI",
            "GDP",
            "Banking Liquidity",
            "Fiscal Deficit",
            "WPI",
            "Credit Growth",
            "Forex Reserves",
            "IIP",
            "GVA",
            "Core Inflation",
        ):
            try:
                ind = cmkp_indicator(name, country=country)
            except Exception:
                continue
            if ind.get("found"):
                latest = ind.get("latest") or {}
                tips[name] = _num(latest.get("current_value"))
                if name == "Forex Reserves":
                    payload = (latest.get("normalized") or {}).get("payload") or {}
                    inr = _num(payload.get("inr_reference"))
                    if inr is not None:
                        tips["USDINR"] = inr
        # Soft G-Sec tip
        try:
            fed = cmkp_indicator("Federal Funds Rate", country="United States")
            if fed.get("found"):
                payload = ((fed.get("latest") or {}).get("normalized") or {}).get("payload") or {}
                ust = _num(payload.get("us_treasury_10y"))
                if ust is not None:
                    tips["G-Sec 10Y"] = round(ust + 2.6, 2)
        except Exception:
            pass
        out["tips"] = {k: v for k, v in tips.items() if v is not None}
        out["cpi"] = tips.get("CPI")
        out["repo_rate"] = tips.get("Repo Rate")
        out["gdp"] = tips.get("GDP")
        try:
            cal = release_calendar(limit=30)
            out["calendar_n"] = cal.get("n")
        except Exception:
            pass
    except Exception:
        out["available"] = False
        return out
    out["available"] = bool(out.get("tips"))
    out["providers_queried"] = []
    return out


def soft_historical(*, country: str = "India") -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "HMIP_KRIG", "providers_queried": []}
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator
        from historical_macro_intelligence.production import timeline

        repo = hmip_indicator("Repo Rate", country=country)
        if repo.get("found"):
            tip["repo_series_n"] = repo.get("n")
            tip["repo_completeness_pct"] = (repo.get("timeline") or {}).get("completeness_pct")
        tls = timeline(country=country)
        tip["timelines_n"] = tls.get("n") or len(tls.get("timelines") or [])
        tip["available"] = bool(repo.get("found"))
    except Exception:
        tip["available"] = False
    return tip


def soft_analogues(*, country: str = "India") -> list[dict[str, Any]]:
    try:
        from historical_macro_analogue_intelligence.production import forecast_tip

        tip = forecast_tip(country=country, top_k=5)
        return list(tip.get("top_analogues") or [])
    except Exception:
        return []


def soft_regime(*, country: str = "India") -> dict[str, Any]:
    try:
        from historical_macro_analogue_intelligence.production import current_regime

        pack = current_regime(country=country)
        return pack.get("regime") or {}
    except Exception:
        return {}


def soft_relationships() -> list[dict[str, Any]]:
    try:
        from macroeconomic_relationship_intelligence.production import relationships

        pack = relationships(limit=80)
        return list(pack.get("relationships") or [])
    except Exception:
        return []


def soft_research() -> dict[str, Any]:
    """Institutional research tip — store/catalog only, no external fetch."""
    return {
        "macro_research_office": {
            "stance": "Data-dependent policy; disinflation watch",
            "themes": ["RBI MPC path", "CPI trajectory", "Fiscal consolidation", "USDINR"],
        },
        "sector_research": {"beneficiaries_on_easing": ["Banks", "Auto", "Realty"]},
        "market_research": {"regime": "Valuation elevated; liquidity supportive if policy eases"},
        "gateway": "Macro_Research_Tip",
        "providers_queried": [],
    }


def soft_monitoring(*, country: str = "India") -> list[dict[str, Any]]:
    events = [
        {"event": "RBI MPC", "status": "Scheduled", "importance": "Critical"},
        {"event": "CPI release", "status": "Scheduled", "importance": "Critical"},
        {"event": "GDP release", "status": "Scheduled", "importance": "Critical"},
        {"event": "Union Budget / fiscal update", "status": "Watching", "importance": "High"},
        {"event": "WPI release", "status": "Scheduled", "importance": "High"},
        {"event": "US Fed / global macro calendar", "status": "Watching", "importance": "High"},
    ]
    try:
        from continuous_macro_knowledge.production import release_calendar

        cal = release_calendar(limit=20)
        for row in cal.get("upcoming") or cal.get("calendar") or cal.get("releases") or []:
            events.append(
                {
                    "event": row.get("indicator") or row.get("event") or "Macro release",
                    "status": "Scheduled",
                    "importance": row.get("importance") or "Medium",
                    "release_date": row.get("release_date") or row.get("date"),
                    "source": "CMKP_calendar",
                }
            )
    except Exception:
        pass
    return events[:25]


def assemble_bundle(*, country: str = "India", region: str = "India") -> MacroForecastBundle:
    span = traces.begin("macro_forecast_bundle", meta={"country": country, "region": region})
    sources: list[str] = []
    current = soft_current_macro(country=country if region == "India" else country)
    if current.get("available"):
        sources.append("CMKP")
    hist = soft_historical(country=country)
    if hist.get("available"):
        sources.append("HMIP")
    analogues = soft_analogues(country=country)
    if analogues:
        sources.append("HMAI")
    regime = soft_regime(country=country)
    if regime:
        sources.append("HMAI_regime")
    rels = soft_relationships()
    if rels:
        sources.append("MRI")
    research = soft_research()
    sources.append("Macro_Research_Tip")
    monitoring = soft_monitoring(country=country)

    # Completeness score
    dims = 0
    tips = current.get("tips") or {}
    for key in ("Repo Rate", "CPI", "GDP", "Fiscal Deficit", "Banking Liquidity"):
        if tips.get(key) is not None:
            dims += 1
    completeness = int(
        round(
            20 * (dims / 5)
            + (15 if analogues else 0)
            + (15 if rels else 0)
            + (15 if hist.get("available") else 0)
            + (15 if regime else 0)
            + (10 if monitoring else 0)
            + (10 if research else 0)
        )
    )

    bundle = MacroForecastBundle(
        country=country,
        region=region,
        current_regime=regime,
        current_macro=current,
        historical_tip=hist,
        analogues=analogues,
        relationships=rels[:40],
        research=research,
        monitoring=monitoring,
        completeness_pct=min(100, completeness),
        sources=sources,
        providers_queried=[],
    )
    traces.end(
        span,
        output={
            "sources": sources,
            "completeness_pct": bundle.completeness_pct,
            "analogues": len(analogues),
            "relationships": len(rels),
        },
    )
    return bundle
