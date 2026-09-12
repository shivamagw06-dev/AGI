"""Derive market drafts via soft-consume — never live Groww/Yahoo on Ask path."""

from __future__ import annotations

from typing import Any

from continuous_market_knowledge.catalog import catalog_for
from continuous_market_knowledge.schema import MARKET_UNIVERSE, RawMarketDraft, canonicalize


def _soft_fpi_tip() -> dict[str, Any]:
    """Soft-read Forecast Provider Integration status — never triggers live refresh."""
    tip: dict[str, Any] = {"gateway": "FPI_KRIG", "providers_queried": []}
    try:
        from forecast_provider_integration.production import health as fpi_health

        h = fpi_health()
        tip["available"] = True
        tip["primary_live_market"] = h.get("primary_live_market") or "groww"
        tip["primary_research"] = h.get("primary_research") or "yahoo"
        tip["status"] = h.get("status")
    except Exception:
        tip["available"] = False
    return tip


def _soft_macro_tip() -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "CMKP_KRIG", "providers_queried": []}
    try:
        from continuous_macro_knowledge.production import indicator as cmkp_indicator

        for name in ("Repo Rate", "CPI", "Banking Liquidity"):
            try:
                ind = cmkp_indicator(name, country="India")
            except Exception:
                continue
            if ind.get("found"):
                tip[name] = (ind.get("latest") or {}).get("current_value")
        tip["available"] = any(k in tip for k in ("Repo Rate", "CPI", "Banking Liquidity"))
    except Exception:
        tip["available"] = False
    return tip


def _soft_sector_tip() -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "CSKP_KRIG", "providers_queried": []}
    try:
        from continuous_sector_knowledge.production import leaders

        pack = leaders(limit=10)
        tip["available"] = bool(pack.get("n"))
        tip["leaders"] = [
            {"sector": r.get("label"), "outlook": r.get("outlook")}
            for r in (pack.get("leaders") or [])[:8]
        ]
    except Exception:
        tip["available"] = False
    return tip


def _soft_sector_forecast_tip() -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "SFI_KRIG", "providers_queried": []}
    try:
        from sector_forecast_intelligence.production import forecast_all

        pack = forecast_all()
        tip["available"] = bool(pack.get("n"))
        tip["forecasts"] = pack.get("forecasts") or []
    except Exception:
        tip["available"] = False
    return tip


def _soft_lidi_tip() -> dict[str, Any]:
    tip: dict[str, Any] = {"gateway": "LIDI_KRIG", "providers_queried": []}
    try:
        from live_data.production import status as lidi_status

        st = lidi_status()
        tip["available"] = True
        tip["status"] = st.get("status") or st.get("summary")
    except Exception:
        tip["available"] = False
    return tip


def _compute_domain(domain_key: str, catalog: dict[str, Any], tips: dict[str, Any]) -> dict[str, Any]:
    """Internal higher-order computations — not fetched from external providers."""
    computed: dict[str, Any] = {
        "method": "institutional_derived",
        "deterministic": True,
    }
    if domain_key == "breadth":
        metrics = dict(catalog.get("metrics") or {})
        # Soft nudge from sector leadership concentration
        leaders = (tips.get("sector") or {}).get("leaders") or []
        pos = sum(1 for l in leaders if str(l.get("outlook") or "").lower() in {"positive", "bull"})
        if leaders:
            metrics["participation_pct"] = round(
                min(85.0, max(40.0, float(metrics.get("participation_pct") or 55) + (pos - 2) * 2.5)),
                1,
            )
            metrics["advance_decline_ratio"] = round(
                max(0.6, min(2.2, float(metrics.get("advance_decline_ratio") or 1.1) + (pos - 2) * 0.08)),
                2,
            )
        computed["metrics"] = metrics
        computed["internal"] = ["advance_decline", "new_highs", "new_lows", "participation", "sector_breadth"]
    elif domain_key == "market_health":
        # Composite = average of component base scores (catalog) with soft overlays
        components = [
            catalog_for("breadth").get("health_base", 50),
            catalog_for("liquidity").get("health_base", 50),
            catalog_for("leadership").get("health_base", 50),
            catalog_for("volatility").get("health_base", 50),
            catalog_for("institutional_flows").get("health_base", 50),
            catalog_for("risk_sentiment").get("health_base", 50),
        ]
        score = round(sum(float(c) for c in components) / len(components), 1)
        if (tips.get("macro") or {}).get("Banking Liquidity") is not None:
            try:
                liq = float(tips["macro"]["Banking Liquidity"])
                score = round(min(90.0, max(35.0, score + (0.5 if liq >= 0 else -1.5))), 1)
            except (TypeError, ValueError):
                pass
        computed["health_score"] = score
        computed["formula"] = "breadth+liquidity+leadership+volatility+flows+risk_sentiment"
        computed["components"] = catalog.get("components") or []
    elif domain_key == "leadership":
        sector_leaders = (tips.get("sector") or {}).get("leaders") or []
        leading = [l["sector"] for l in sector_leaders if str(l.get("outlook")).lower() == "positive"][:5]
        weak = [l["sector"] for l in sector_leaders if str(l.get("outlook")).lower() == "negative"][:5]
        computed["leading_sectors"] = leading or list(catalog.get("leading_sectors") or [])
        computed["weak_sectors"] = weak or list(catalog.get("weak_sectors") or [])
        computed["rotation"] = catalog.get("rotation")
        # Soft SFI tilt
        forecasts = (tips.get("sfi") or {}).get("forecasts") or []
        bullish = [
            f.get("sector")
            for f in forecasts
            if int((f.get("probability_distribution") or {}).get("Bull") or 0) >= 28
        ]
        if bullish:
            computed["forecast_supported_leaders"] = bullish[:5]
    elif domain_key == "volatility":
        computed["metrics"] = dict(catalog.get("metrics") or {})
        computed["internal"] = ["realized_volatility", "atr", "index_volatility", "sector_volatility"]
    elif domain_key == "liquidity":
        computed["metrics"] = dict(catalog.get("metrics") or {})
        if (tips.get("macro") or {}).get("Banking Liquidity") is not None:
            computed["macro_liquidity_tip"] = tips["macro"]["Banking Liquidity"]
    elif domain_key == "institutional_flows":
        computed["metrics"] = dict(catalog.get("metrics") or {})
    elif domain_key == "cross_asset":
        computed["metrics"] = dict(catalog.get("metrics") or {})
        if (tips.get("macro") or {}).get("Repo Rate") is not None:
            computed["repo_rate_tip"] = tips["macro"]["Repo Rate"]
    elif domain_key in {"india_equity", "global_equity", "risk_sentiment"}:
        computed["regime"] = catalog.get("regime")
        computed["indices"] = catalog.get("indices")
    return computed


def collect_domain(domain_key: str, *, tips: dict[str, Any] | None = None) -> RawMarketDraft:
    key = canonicalize(domain_key) or domain_key
    cat = catalog_for(key)
    tips = tips or {}
    computed = _compute_domain(key, cat, tips)
    return RawMarketDraft(
        domain_key=key,
        label=str(cat.get("label") or key.replace("_", " ").title()),
        trigger="ops_refresh",
        importance="Medium",
        catalog=cat,
        groww_tip={"note": "Ops Groww live feed reserved; Ask never queries", "gateway": "Groww_Ops"},
        yahoo_tip={"note": "Ops Yahoo global feed reserved; Ask never queries", "gateway": "Yahoo_Ops"},
        macro_tip=tips.get("macro") or {},
        sector_tip=tips.get("sector") or {},
        company_tip={},
        fpi_tip=tips.get("fpi") or {},
        computed=computed,
        providers_queried=[],
        ask_triggered=False,
    )


def collect_all(*, domains: list[str] | None = None) -> dict[str, Any]:
    tips = {
        "fpi": _soft_fpi_tip(),
        "macro": _soft_macro_tip(),
        "sector": _soft_sector_tip(),
        "sfi": _soft_sector_forecast_tip(),
        "lidi": _soft_lidi_tip(),
    }
    keys = list(MARKET_UNIVERSE)
    if domains:
        resolved = [canonicalize(d) or d for d in domains]
        keys = [k for k in resolved if k in MARKET_UNIVERSE]
    drafts = [collect_domain(k, tips=tips) for k in keys]
    return {
        "ok": True,
        "n": len(drafts),
        "drafts": drafts,
        "providers_queried": [],
        "ask_triggered": False,
        "mode": "derived_soft_consume",
    }


def collect_domain_one(domain: str) -> dict[str, Any]:
    return collect_all(domains=[domain])
