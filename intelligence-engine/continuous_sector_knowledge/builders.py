"""Derive sector drafts from AGI-owned company / macro / market / event / research tips.

Never calls external providers. Soft-consumes published knowledge only.
"""

from __future__ import annotations

from typing import Any

from continuous_sector_knowledge.catalog import SECTOR_CATALOG, all_sector_keys, get_catalog
from continuous_sector_knowledge.schema import RawSectorDraft


def _soft_cmkp_macro() -> dict[str, Any]:
    tip: dict[str, Any] = {}
    try:
        from continuous_macro_knowledge.production import indicator as cmkp_indicator

        for name, country in (
            ("Repo Rate", "India"),
            ("CPI", "India"),
            ("GDP", "India"),
            ("Banking Liquidity", "India"),
            ("Fiscal Deficit", "India"),
        ):
            pack = cmkp_indicator(name, country=country)
            if pack.get("found"):
                tip[name] = (pack.get("latest") or {}).get("current_value")
    except Exception:
        pass
    tip["providers_queried"] = []
    tip["gateway"] = "CMKP_KRIG"
    return tip


def _soft_mri_for_sector(label: str) -> list[dict[str, Any]]:
    try:
        from macroeconomic_relationship_intelligence.production import for_sector

        pack = for_sector(label, limit=20)
        return list(pack.get("relationships") or [])
    except Exception:
        return []


def _soft_company_tips(leaders: list[str]) -> list[dict[str, Any]]:
    tips: list[dict[str, Any]] = []
    try:
        from institutional_forecast_intelligence.knowledge_catalog import COMPANY_KNOWLEDGE
    except Exception:
        COMPANY_KNOWLEDGE = {}
    for ticker in leaders:
        row = COMPANY_KNOWLEDGE.get(ticker) or {"ticker": ticker, "tip": "catalog_leader"}
        tips.append(
            {
                "ticker": ticker,
                "label": row.get("label") or ticker,
                "sector_key": row.get("sector_key"),
                "has_catalog": ticker in COMPANY_KNOWLEDGE,
                "source": "company_knowledge_catalog",
            }
        )
    return tips


def _soft_market_tip(sector_key: str, label: str) -> dict[str, Any]:
    """Soft-read CMKTP when published; fallback catalog tip — never collects live."""
    tip: dict[str, Any] = {
        "sector_index": f"NIFTY {label.upper()}"
        if sector_key in {"banking", "it_services", "auto", "pharma", "fmcg", "metals"}
        else None,
        "relative_performance": "Watching",
        "valuation_spread": "vs NIFTY",
        "breadth": "Mixed",
        "liquidity": "Adequate",
        "gateway": "Market_Knowledge_Tip",
        "providers_queried": [],
    }
    try:
        from continuous_market_knowledge.production import market as cmktp_market

        pack = cmktp_market()
        if pack.get("found") and pack.get("market"):
            m = pack["market"]
            tip.update(
                {
                    "market_regime": m.get("market_regime"),
                    "breadth": m.get("breadth") or tip["breadth"],
                    "liquidity": (m.get("liquidity") or {}).get("trading_volume")
                    or tip["liquidity"],
                    "risk_sentiment": m.get("risk_sentiment"),
                    "health_score": m.get("health_score"),
                    "leadership": m.get("leadership"),
                    "gateway": "CMKTP_KRIG",
                    "collected_on_request": False,
                }
            )
    except Exception:
        pass
    return tip


def _soft_events(sector_key: str, label: str) -> list[dict[str, Any]]:
    events = [
        {"event": f"{label} earnings season updates", "kind": "earnings", "importance": "High"},
        {"event": f"{label} competitive / M&A watch", "kind": "ma", "importance": "Medium"},
    ]
    if sector_key in {"banking", "nbfc", "financial_services"}:
        events.append({"event": "RBI policy transmission to credit", "kind": "macro_policy", "importance": "Critical"})
    if sector_key in {"fmcg", "auto", "consumer_durables"}:
        events.append({"event": "CPI / rural demand impulse", "kind": "macro", "importance": "High"})
    return events


def _soft_research(sector_key: str, cat: dict[str, Any]) -> dict[str, Any]:
    return {
        "sector_research_office": {
            "outlook": cat.get("default_outlook"),
            "themes": list(cat.get("growth_drivers") or [])[:3],
        },
        "industry_reports": ["Institutional sector note tip"],
        "gateway": "Sector_Research_Tip",
        "providers_queried": [],
    }


def detect_trigger(macro: dict[str, Any], events: list[dict[str, Any]]) -> str:
    if any(e.get("kind") == "macro_policy" for e in events):
        repo = macro.get("Repo Rate")
        if repo is not None:
            return "macro_change"
    if any(e.get("kind") == "earnings" for e in events):
        return "earnings"
    if any(e.get("kind") == "ma" for e in events):
        return "ma"
    return "ops_refresh"


def build_draft(sector_key: str, *, force_trigger: str | None = None) -> RawSectorDraft | None:
    cat = get_catalog(sector_key)
    if not cat:
        return None
    label = str(cat["label"])
    leaders = list(cat.get("leaders") or [])
    macro = _soft_cmkp_macro()
    company_tips = _soft_company_tips(leaders)
    market = _soft_market_tip(sector_key, label)
    events = _soft_events(sector_key, label)
    research = _soft_research(sector_key, cat)
    mri = _soft_mri_for_sector(label)
    # Also try common MRI aliases
    if not mri and sector_key == "banking":
        mri = _soft_mri_for_sector("Banks") or _soft_mri_for_sector("Private Banks")
    if not mri and sector_key == "it_services":
        mri = _soft_mri_for_sector("IT Services")
    if not mri and sector_key == "real_estate":
        mri = _soft_mri_for_sector("Real Estate") or _soft_mri_for_sector("Realty")

    layers = ["sector_catalog", "company_knowledge", "macro_knowledge", "market_knowledge", "events", "research"]
    if mri:
        layers.append("MRI")
        research = {**research, "mri_relationships_n": len(mri), "mri_sample": mri[:3]}

    trigger = force_trigger or detect_trigger(macro, events)
    importance = "Critical" if trigger == "macro_change" and sector_key in {"banking", "nbfc"} else "High"
    if trigger == "ops_refresh":
        importance = "Medium"

    return RawSectorDraft(
        sector_key=sector_key,
        label=label,
        source_layers=layers,
        company_tips=company_tips,
        macro_tips=macro,
        market_tips=market,
        event_tips=events,
        research_tips=research,
        catalog=cat,
        trigger=trigger,
        importance=importance,  # type: ignore[arg-type]
    )


def collect_all(*, sectors: list[str] | None = None) -> dict[str, Any]:
    keys = sectors or all_sector_keys()
    drafts: list[RawSectorDraft] = []
    for key in keys:
        if key not in SECTOR_CATALOG:
            continue
        d = build_draft(key)
        if d:
            drafts.append(d)
    return {
        "ok": True,
        "n": len(drafts),
        "drafts": drafts,
        "mode": "derived_soft_consume",
        "ask_triggered": False,
        "providers_queried": [],
        "fabricated": False,
    }


def collect_sector(sector_key: str) -> dict[str, Any]:
    d = build_draft(sector_key)
    return {
        "ok": d is not None,
        "n": 1 if d else 0,
        "drafts": [d] if d else [],
        "ask_triggered": False,
        "providers_queried": [],
    }
