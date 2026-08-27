"""Catalyst Intelligence — identify company / sector / macro / market catalysts."""

from __future__ import annotations

from typing import Any

from catalyst_trigger_intelligence.catalog import (
    MACRO_CATALYSTS,
    MARKET_CATALYSTS,
    company_catalyst_templates,
    sector_catalyst_templates,
    sector_for_ticker,
)
from catalyst_trigger_intelligence.schema import CTI_VERSION
from catalyst_trigger_intelligence import traces


def _fie_profile(ticker: str) -> dict[str, Any] | None:
    try:
        from forecast_intelligence.profiles.packs import profile_for

        return profile_for(ticker)
    except Exception:
        return None


def _merge_fie_catalysts(
    templates: list[dict[str, Any]],
    fie_profile: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not fie_profile:
        return templates
    by_id = {t["id"]: t for t in templates}
    for c in fie_profile.get("catalysts") or []:
        cid = str(c.get("id") or "")
        if not cid:
            continue
        if cid in by_id:
            by_id[cid]["fie_kind"] = c.get("kind")
            by_id[cid]["fie_polarity"] = c.get("polarity")
            by_id[cid]["horizon"] = c.get("horizon") or by_id[cid].get("horizon")
            by_id[cid]["label"] = c.get("label") or by_id[cid].get("label")
            by_id[cid]["from_fie"] = True
        else:
            polarity = c.get("polarity") or "mixed"
            impact = "strengthens_bull" if polarity == "positive" else (
                "strengthens_bear" if polarity == "negative" else "neutral"
            )
            by_id[cid] = {
                "id": cid,
                "label": c.get("label") or cid,
                "category": "company",
                "event": c.get("label") or cid,
                "condition": f"Observable outcome for {c.get('label')}",
                "impact": impact,
                "impact_label": f"FIE-linked catalyst ({polarity})",
                "priority": "High" if c.get("kind") == "expected" else "Medium",
                "probability": 0.5,
                "monitoring_source": "forecast_intelligence",
                "entity": fie_profile.get("ticker"),
                "entity_name": fie_profile.get("name"),
                "expected_date": c.get("horizon") or "uncertain",
                "fie_kind": c.get("kind"),
                "fie_polarity": polarity,
                "from_fie": True,
            }
    return list(by_id.values())


def _enrich(catalyst: dict[str, Any], *, current_scenario: str = "base") -> dict[str, Any]:
    return {
        **catalyst,
        "current_institutional_view": current_scenario,
        "rule": "We are Base Case unless this catalyst's trigger condition fires",
        "evidence": [
            {
                "kind": "catalyst_template",
                "source": "catalyst_trigger_intelligence.catalog",
                "note": catalyst.get("impact_label"),
            }
        ],
        "confidence": round(float(catalyst.get("probability") or 0.5), 2),
        "cti_version": CTI_VERSION,
    }


def company_catalysts(ticker: str, *, current_scenario: str = "base") -> dict[str, Any]:
    span = traces.begin("catalyst_generation", meta={"scope": "company", "ticker": ticker})
    t = (ticker or "").upper()
    fie = _fie_profile(t)
    sector = sector_for_ticker(t, fie)
    templates = company_catalyst_templates(t, sector)
    merged = _merge_fie_catalysts(templates, fie)
    items = [_enrich(c, current_scenario=current_scenario) for c in merged]
    # Attach sector + relevant macro catalysts that affect this name
    sector_items = [
        _enrich({**c, "entity": t, "linked_sector": sector}, current_scenario=current_scenario)
        for c in sector_catalyst_templates(sector)
    ]
    macro_items = []
    for c in MACRO_CATALYSTS:
        affected = c.get("affected_sectors") or []
        if not affected or sector in affected or c["id"] in {"union_budget", "inflation", "gdp"}:
            macro_items.append(
                _enrich({**c, "linked_entity": t, "linked_sector": sector}, current_scenario=current_scenario)
            )
    out = {
        "ticker": t,
        "sector": sector,
        "name": (fie or {}).get("name") or t,
        "current_scenario": current_scenario,
        "company": items,
        "sector_catalysts": sector_items,
        "macro_catalysts": macro_items[:6],
        "count": len(items) + len(sector_items) + min(6, len(macro_items)),
        "primary_question": "What events would make us change our view?",
        "does_not_forecast": True,
    }
    traces.end(span, output={"count": out["count"]})
    return out


def sector_catalysts(sector: str, *, current_scenario: str = "base") -> dict[str, Any]:
    span = traces.begin("catalyst_generation", meta={"scope": "sector", "sector": sector})
    s = (sector or "").strip().lower().replace(" ", "_")
    items = [_enrich(c, current_scenario=current_scenario) for c in sector_catalyst_templates(s)]
    macros = [
        _enrich(c, current_scenario=current_scenario)
        for c in MACRO_CATALYSTS
        if not c.get("affected_sectors") or s in (c.get("affected_sectors") or [])
    ]
    out = {
        "sector": s,
        "current_scenario": current_scenario,
        "items": items,
        "macro_linked": macros,
        "count": len(items) + len(macros),
        "does_not_forecast": True,
    }
    traces.end(span, output={"count": out["count"]})
    return out


def market_catalysts(*, current_scenario: str = "base") -> dict[str, Any]:
    span = traces.begin("catalyst_generation", meta={"scope": "market"})
    market = [_enrich(c, current_scenario=current_scenario) for c in MARKET_CATALYSTS]
    macro = [_enrich(c, current_scenario=current_scenario) for c in MACRO_CATALYSTS]
    out = {
        "market": market,
        "macro": macro,
        "count": len(market) + len(macro),
        "current_scenario": current_scenario,
        "does_not_forecast": True,
        "calendar_focus": ["Upcoming earnings", "Budget", "RBI", "Corporate actions"],
    }
    traces.end(span, output={"count": out["count"]})
    return out
