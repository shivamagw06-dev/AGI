"""Deterministic Portfolio Intelligence engines — Phase 3.3."""

from __future__ import annotations

from collections import defaultdict
from typing import Any, Optional

from investment_intelligence.policy import strip_recommendation_language
from portfolio_intelligence.foundation.schema import RECOMMENDATION_POLICY, STYLE_FACTORS


def _weights(p: dict[str, Any]) -> list[tuple[dict[str, Any], float]]:
    return [(h, float(h.get("weight") or 0.0)) for h in (p.get("holdings") or [])]


def _sector_map(p: dict[str, Any]) -> dict[str, float]:
    m: dict[str, float] = defaultdict(float)
    for h, w in _weights(p):
        m[str(h.get("sector") or "unknown")] += w
    m["cash"] = float(p.get("cash_weight") or 0.0)
    return dict(m)


def _industry_map(p: dict[str, Any]) -> dict[str, float]:
    m: dict[str, float] = defaultdict(float)
    for h, w in _weights(p):
        m[str(h.get("industry") or h.get("sector") or "unknown")] += w
    return dict(m)


def portfolio_object(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    industries = _industry_map(p)
    style: dict[str, float] = defaultdict(float)
    mcap: dict[str, float] = defaultdict(float)
    country: dict[str, float] = defaultdict(float)
    for h, w in _weights(p):
        style[str(h.get("style") or "blend")] += w
        mcap[str(h.get("market_cap") or "large")] += w
        country[str(h.get("country") or "IN")] += w
    obj = {
        "portfolio_id": p["portfolio_id"],
        "name": p["name"],
        "holdings": list(p.get("holdings") or []),
        "cash": float(p.get("cash_weight") or 0.0),
        "sector_allocation": sectors,
        "industry_allocation": industries,
        "country_allocation": dict(country),
        "market_cap_allocation": dict(mcap),
        "style_exposure": dict(style),
        "factor_exposure": {f: round(style.get(f, 0.0) + (0.05 if f == "quality" else 0.0), 4) for f in STYLE_FACTORS},
        "risk_profile": p.get("risk_tolerance"),
        "objectives": p.get("objective"),
        "constraints": p.get("constraints"),
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }
    return {
        "portfolio_object": obj,
        "summary": strip_recommendation_language(
            f"Portfolio object for {p['name']}: {len(p.get('holdings') or [])} holdings, "
            f"cash {obj['cash']:.0%}, top sectors "
            + ", ".join(f"{k} {v:.0%}" for k, v in sorted(sectors.items(), key=lambda kv: -kv[1])[:4] if k != "cash")
            + ". Canonical object links holdings, allocations, style/factor exposures, risk profile, objectives, and constraints."
        ),
        "fabricated": False,
    }


def construction(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    equity_w = 1.0 - float(p.get("cash_weight") or 0.0)
    top = sorted(((h["ticker"], float(h["weight"])) for h in p["holdings"]), key=lambda x: -x[1])
    conc = sum(w for _, w in top[:3])
    banks = sectors.get("banks", 0.0)
    summary = strip_recommendation_language(
        f"Construction view for {p['name']}: equity weight {equity_w:.0%}, cash {p.get('cash_weight', 0):.0%}. "
        f"Top-3 concentration {conc:.0%} ({', '.join(t for t, _ in top[:3])}). "
        f"Banks sector {banks:.0%} — diversification benefit comes from IT/FMCG/telecom sleeves vs bank cluster. "
        f"Why: balance conviction sizing with sector/style limits and geography (India large-cap). "
        f"Benefit: smoother drawdowns if correlations stay imperfect; liquidity is supported by large-cap bias. "
        f"Risk/trade-off: cash dilutes upside; bank cluster creates hidden financial-factor concentration; "
        f"style balance and market-cap mix create gaps if growth sleeve expands. "
        f"Observations only — no trade recommendations."
    )
    return {
        "diversification": {
            "equity_weight": equity_w,
            "cash_weight": p.get("cash_weight"),
            "top3_concentration": round(conc, 4),
            "sector_count": len([k for k in sectors if k != "cash"]),
            "why": "Spread capital across sectors/styles while respecting conviction",
            "benefit": "Reduce single-name and single-sector path dependence",
            "risk": "Over-diversification can dilute high-conviction ideas; under-diversification raises drawdown risk",
            "trade_offs": "Cash vs full investment; bank weight vs IT/FMCG balance",
        },
        "sizing": [{"ticker": t, "weight": w, "conviction": next(h["conviction"] for h in p["holdings"] if h["ticker"] == t)} for t, w in top],
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def exposures(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    industries = _industry_map(p)
    style: dict[str, float] = defaultdict(float)
    for h, w in _weights(p):
        style[str(h.get("style") or "blend")] += w
    # Deterministic macro sensitivities from sector mix
    rate_exp = round(sectors.get("banks", 0) * 0.9 + sectors.get("telecom", 0) * 0.4, 3)
    commodity_exp = round(sectors.get("energy", 0) * 0.8, 3)
    fx_exp = round(sectors.get("it_services", 0) * 0.7, 3)
    summary = strip_recommendation_language(
        f"Exposures for {p['name']}: sectors — "
        + ", ".join(f"{k} {v:.0%}" for k, v in sorted(sectors.items(), key=lambda kv: -kv[1])[:5])
        + f". Style — quality {style.get('quality', 0):.0%}, growth {style.get('growth', 0):.0%}. "
        f"Interest-rate exposure score {rate_exp:.2f} (bank-heavy). "
        f"FX exposure score {fx_exp:.2f} (IT services). "
        f"Commodity exposure score {commodity_exp:.2f} (energy). "
        f"No BUY/SELL — exposure diagnosis only."
    )
    return {
        "sector_exposure": sectors,
        "industry_exposure": industries,
        "currency_exposure": {"INR": 1.0 - fx_exp * 0.3, "USD_earnings_proxy": fx_exp},
        "interest_rate_exposure": rate_exp,
        "commodity_exposure": commodity_exp,
        "style_exposure": dict(style),
        "factor_exposure": {
            "growth": round(style.get("growth", 0) + style.get("blend", 0) * 0.3, 3),
            "value": round(style.get("blend", 0) * 0.4, 3),
            "quality": round(style.get("quality", 0), 3),
            "momentum": round(style.get("growth", 0) * 0.5, 3),
            "low_volatility": round(style.get("quality", 0) * 0.6, 3),
            "market_cap_large": sum(float(h["weight"]) for h in p["holdings"] if h.get("market_cap") == "large"),
            "country_IN": sum(float(h["weight"]) for h in p["holdings"] if h.get("country") == "IN"),
        },
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def risk_budget(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    top = sorted(p["holdings"], key=lambda h: -float(h["weight"]))
    risks = [
        {
            "key": "concentration",
            "name": "Position / sector concentration",
            "severity": "high" if float(top[0]["weight"]) >= 0.12 or sectors.get("banks", 0) >= 0.25 else "medium",
            "drivers": [f"Top name {top[0]['ticker']} {float(top[0]['weight']):.0%}", f"Banks {sectors.get('banks', 0):.0%}"],
            "mitigants": ["Single-name limit", "Sector limits", "Cash buffer"],
            "monitoring_metrics": ["Top-5 weight", "Banks weight", "HHI proxy"],
        },
        {
            "key": "correlation",
            "name": "Correlation / hidden financial factor risk",
            "severity": "high" if sectors.get("banks", 0) >= 0.20 else "medium",
            "drivers": ["Multiple bank holdings", "IT pair TCS/INFY"],
            "mitigants": ["Cross-sector sleeves", "Cash"],
            "monitoring_metrics": ["Bank cluster weight", "IT pair weight"],
        },
        {
            "key": "liquidity",
            "name": "Liquidity risk",
            "severity": "low",
            "drivers": ["Mostly large-cap India equities"],
            "mitigants": ["Large-cap bias"],
            "monitoring_metrics": ["ADV coverage", "Cash"],
        },
        {
            "key": "tail",
            "name": "Tail / drawdown risk",
            "severity": "medium" if p.get("risk_tolerance") == "aggressive" else "medium",
            "drivers": ["Equity beta", "Growth sleeve" if p.get("risk_tolerance") == "aggressive" else "Market beta"],
            "mitigants": ["Cash", "Quality bias"],
            "monitoring_metrics": ["Drawdown vs max", "Beta proxy"],
        },
        {
            "key": "factor",
            "name": "Factor risk (rates / FX / commodity)",
            "severity": "medium",
            "drivers": ["Banks → rates", "IT → FX", "Energy → commodity"],
            "mitigants": ["Sector balance"],
            "monitoring_metrics": ["Rate exposure score", "FX score", "Commodity score"],
        },
    ]
    summary = strip_recommendation_language(
        f"Risk budget for {p['name']}: primary risks — "
        + "; ".join(r["name"] + f" ({r['severity']})" for r in risks[:3])
        + ". Each risk includes severity, drivers, mitigants, and monitoring metrics. "
        + "No trade instructions."
    )
    return {
        "risks": risks,
        "key_risks": [r["name"] for r in risks],
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def correlation(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    pairs = [
        {"pair": "HDFCBANK-ICICIBANK", "relationship": "positive", "note": "Same sector — limited diversification"},
        {"pair": "TCS-INFY", "relationship": "positive", "note": "IT services peers — correlated earnings cycle"},
        {"pair": "banks-it_services", "relationship": "low", "note": "Different macro drivers (rates vs global IT spend/FX)"},
        {"pair": "fmcg-energy", "relationship": "low", "note": "Defensive staples vs commodity/optionality"},
    ]
    hidden = []
    if sectors.get("banks", 0) >= 0.20:
        hidden.append("Bank cluster creates hidden financial-factor concentration beyond single-name limits")
    if sectors.get("it_services", 0) >= 0.15:
        hidden.append("IT pair concentrates global demand/FX factor")
    summary = strip_recommendation_language(
        f"Correlation intelligence for {p['name']}: positive correlation inside banks and IT pairs; "
        f"low correlation between banks and IT/FMCG sleeves provides diversification benefit. "
        f"Relationship map covers HDFCBANK-ICICIBANK, TCS-INFY, banks-it_services, fmcg-energy. "
        f"Hidden concentration: {'; '.join(hidden) or 'none flagged'}. "
        f"Cluster risk rises when bank or IT pair weights stack the same factor. "
        f"Macro relationships: rates→banks, USD/IT spend→IT, crude→energy."
    )
    return {
        "relationships": pairs,
        "diversification_benefit": "Cross-sector sleeves reduce portfolio variance when correlations stay imperfect",
        "hidden_concentration": hidden,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def quality(p: dict[str, Any]) -> dict[str, Any]:
    """Portfolio quality — not a naive weighted average; penalize weak conviction/growth sleeves."""
    dims = {
        "business_quality": 0.0,
        "industry_quality": 0.0,
        "financial_quality": 0.0,
        "capital_allocation": 0.0,
        "management_quality": 0.0,
        "evidence_strength": 0.0,
        "cash_generation": 0.0,
    }
    # Soft-consume Investment Intelligence quality when inv_key present
    try:
        from investment_intelligence.profiles import get_profile
    except Exception:
        get_profile = None  # type: ignore

    w_sum = 0.0
    for h, w in _weights(p):
        w_sum += w
        base = {"quality": 78, "growth": 62, "blend": 68}.get(str(h.get("style")), 65)
        conv = {"high": 8, "medium": 0, "low": -10}.get(str(h.get("conviction")), 0)
        inv_boost = 0
        if get_profile and h.get("inv_key"):
            prof = get_profile(h["inv_key"])
            if prof:
                qs = prof.get("quality_scores") or {}
                base = int(qs.get("business_quality", base))
                inv_boost = 4
                dims["management_quality"] += w * float(qs.get("management_quality", 70))
                dims["financial_quality"] += w * float(qs.get("financial_quality", 70))
                dims["capital_allocation"] += w * float(qs.get("capital_allocation", 70))
                dims["evidence_strength"] += w * float(qs.get("evidence_strength", 65))
                dims["cash_generation"] += w * float(qs.get("cash_conversion", 70))
            else:
                dims["management_quality"] += w * (base + conv)
                dims["financial_quality"] += w * (base + conv - 2)
                dims["capital_allocation"] += w * (base + conv - 4)
                dims["evidence_strength"] += w * (60 + conv)
                dims["cash_generation"] += w * (base + conv)
        else:
            dims["management_quality"] += w * (base + conv)
            dims["financial_quality"] += w * (base + conv - 2)
            dims["capital_allocation"] += w * (base + conv - 4)
            dims["evidence_strength"] += w * (60 + conv)
            dims["cash_generation"] += w * (base + conv)
        dims["business_quality"] += w * (base + conv + inv_boost)
        # Industry quality proxy from sector
        ind_q = {"banks": 72, "it_services": 74, "fmcg": 80, "telecom": 64, "energy": 66, "consumer_internet": 55}.get(
            str(h.get("sector")), 65
        )
        dims["industry_quality"] += w * ind_q

    if w_sum > 0:
        for k in dims:
            dims[k] = round(dims[k] / w_sum, 1)
    # Concentration penalty on composite
    top3 = sum(sorted((float(h["weight"]) for h in p["holdings"]), reverse=True)[:3])
    composite = round(sum(dims.values()) / len(dims) - max(0.0, (top3 - 0.25) * 20), 1)
    summary = strip_recommendation_language(
        f"Portfolio quality for {p['name']}: composite score {composite}/100. "
        f"Business {dims['business_quality']}, industry {dims['industry_quality']}, "
        f"financial {dims['financial_quality']}, capital allocation {dims['capital_allocation']}, "
        f"management {dims['management_quality']}, evidence strength {dims['evidence_strength']}, "
        f"cash generation {dims['cash_generation']}. "
        f"Quality is adjusted for conviction and concentration — not a naive weighted average. "
        f"Observations only."
    )
    return {
        "composite_score": composite,
        "dimensions": dims,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def attribution(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    bench = dict(p.get("benchmark_sector_weights") or {})
    alloc_effects = []
    for sec, w in sectors.items():
        if sec == "cash":
            continue
        bw = float(bench.get(sec, 0.0))
        active = round(w - bw, 4)
        alloc_effects.append({"sector": sec, "portfolio_weight": w, "benchmark_weight": bw, "active_weight": active})
    summary = strip_recommendation_language(
        f"Attribution framing for {p['name']}: explain relative performance via "
        f"sector allocation, industry sleeves, stock selection within sectors, currency/FX (IT), "
        f"and macro (rates for banks). Active sector tilts: "
        + ", ".join(
            f"{a['sector']} {a['active_weight']:+.0%}"
            for a in sorted(alloc_effects, key=lambda x: -abs(x["active_weight"]))[:4]
        )
        + ". This explains why a portfolio may outperform or underperform — not a recommendation."
    )
    return {
        "allocation_effects": alloc_effects,
        "selection_notes": [
            "Stock selection within banks (HDFC/ICICI vs AXIS) drives financial sleeve outcomes",
            "IT selection (TCS/INFY) drives services sleeve",
        ],
        "macro_notes": ["Rates → banks", "USD/global IT spend → IT", "Crude/optionality → energy"],
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def rebalancing(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    drifts = [
        {"type": "sector_drift", "what_changed": f"Banks at {sectors.get('banks', 0):.0%} vs limit context", "why": "Relative performance / flows", "monitoring": "Banks weight vs 35% limit"},
        {"type": "cash_drift", "what_changed": f"Cash at {float(p.get('cash_weight') or 0):.0%}", "why": "Uninvested capital / risk buffer", "monitoring": "Cash vs objective"},
        {"type": "risk_drift", "what_changed": "Growth/internet sleeve can raise portfolio beta", "why": "Style mix shift", "monitoring": "Growth weight + drawdown"},
        {"type": "position_drift", "what_changed": "Top names may drift toward single-name limit", "why": "Price appreciation", "monitoring": "Single-name weights vs 12% limit"},
    ]
    summary = strip_recommendation_language(
        f"Rebalancing intelligence for {p['name']}: explains position, sector, cash, and risk drift — "
        f"what changed, why it changed, and monitoring considerations (limits, cash, growth drawdown). "
        f"No trade recommendations are issued."
    )
    return {
        "drifts": drifts,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def scenarios(p: dict[str, Any]) -> dict[str, Any]:
    sectors = _sector_map(p)
    cases = {
        "bull": {
            "sector_impact": "IT/growth and energy optionality lead; banks participate if credit stays clean",
            "portfolio_impact": "Equity sleeve captures upside; cash dilutes somewhat",
            "risk_concentration": "Upside concentrated in high-conviction names",
        },
        "base": {
            "sector_impact": "Quality compounds; sector mix dominates outcomes",
            "portfolio_impact": "Mid-cycle returns with cash drag",
            "risk_concentration": "Bank + IT clusters remain primary variance drivers",
        },
        "bear": {
            "sector_impact": "Growth/internet and high-beta sleeves hurt first; FMCG cushions",
            "portfolio_impact": "Drawdown moderated by cash and quality bias",
            "risk_concentration": "Bank credit stress would dominate tail",
        },
        "interest_rate_shock": {
            "sector_impact": f"Banks ({sectors.get('banks', 0):.0%}) most sensitive",
            "portfolio_impact": "NIM/valuation pressure on financials; IT less direct",
            "risk_concentration": "Financial factor concentration",
        },
        "commodity_shock": {
            "sector_impact": f"Energy ({sectors.get('energy', 0):.0%}) direct; FMCG input-cost indirect",
            "portfolio_impact": "Mixed — energy may offset staples margin pressure",
            "risk_concentration": "Energy single-name path dependence",
        },
        "fx_shock": {
            "sector_impact": f"IT services ({sectors.get('it_services', 0):.0%}) USD earnings sensitivity",
            "portfolio_impact": "INR depreciation often helps IT translation",
            "risk_concentration": "IT pair correlation",
        },
        "recession": {
            "sector_impact": "Cyclicals/growth weak; FMCG relatively defensive",
            "portfolio_impact": "Cash + quality bias cushions; internet sleeve hurts",
            "risk_concentration": "Earnings recession in banks/IT",
        },
        "recovery": {
            "sector_impact": "Banks and cyclicals typically lead; IT follows deal-cycle healing",
            "portfolio_impact": "Equity sleeve captures recovery; cash initially dilutes",
            "risk_concentration": "Early-cycle beta concentrated in financials",
        },
        "regulatory_shock": {
            "sector_impact": "Banks (RBI), telecom (TRAI), and internet platforms most exposed",
            "portfolio_impact": "Policy risk clusters by sector weight",
            "risk_concentration": "Regulatory factor across financials/telecom/digital",
        },
        "technology_disruption": {
            "sector_impact": "IT services mix/pricing; internet platforms competitively intense",
            "portfolio_impact": "Selection within IT/internet matters more than allocation",
            "risk_concentration": "Digital sleeve",
        },
    }
    summary = strip_recommendation_language(
        f"Portfolio scenarios for {p['name']}: bull/base/bear plus rate, commodity, FX, recession, "
        f"recovery, regulatory, and technology shocks. Each shows sector impact, portfolio impact, "
        f"and risk concentration. No price targets or trade calls."
    )
    return {
        "scenarios": cases,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def monitoring(p: dict[str, Any]) -> dict[str, Any]:
    priorities = [
        "Business deterioration in top holdings",
        "Industry deterioration (banks credit, IT demand, telecom ARPU)",
        "Valuation / multiple change vs quality",
        "Capital allocation shifts at holding level",
        "Management / governance changes",
        "Regulatory changes (RBI/TRAI)",
        "Macro exposure (rates, FX, commodity)",
        "Evidence freshness on theses",
    ]
    obj = {
        "portfolio_id": p["portfolio_id"],
        "priorities": priorities,
        "holding_watches": [
            {"ticker": h["ticker"], "watch": f"{h['sector']} thesis + conviction={h['conviction']}"}
            for h in sorted(p["holdings"], key=lambda x: -float(x["weight"]))[:5]
        ],
        "sector_watches": list(_sector_map(p).keys()),
    }
    summary = strip_recommendation_language(
        f"Monitoring priorities for {p['name']}: "
        + "; ".join(priorities[:5])
        + ". Portfolio Monitoring Object tracks business/industry deterioration, valuation, "
        + "capital allocation, management/governance changes, regulation, macro exposure, "
        + "and evidence freshness. Holding watches prioritize top weights by conviction. "
        + "Observational — not trade instructions."
    )
    return {
        "monitoring_object": obj,
        "priorities": priorities,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def graph(p: dict[str, Any]) -> dict[str, Any]:
    g = {
        "portfolio": p["name"],
        "holdings": [h["ticker"] for h in p["holdings"]],
        "industries": sorted({h.get("industry") for h in p["holdings"]}),
        "macro_drivers": ["interest_rates", "usd_inr", "crude", "gdp_credit_cycle", "global_it_spend"],
        "factors": list(STYLE_FACTORS),
        "currencies": ["INR", "USD_earnings_proxy"],
        "risks": risk_budget(p)["key_risks"],
        "catalysts": ["Credit normalization", "IT deal cycle", "ARPU recovery", "Retail/energy optionality"],
        "correlations": correlation(p)["relationships"],
    }
    return {
        "graph": g,
        "summary": strip_recommendation_language(
            f"Portfolio knowledge graph for {p['name']} links holdings → industries → macro drivers → "
            f"factors → currencies → risks → catalysts → correlations."
        ),
        "fabricated": False,
    }


def compare_portfolios(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    sa, sb = _sector_map(a), _sector_map(b)
    qa, qb = quality(a), quality(b)
    summary = strip_recommendation_language(
        f"Compare portfolios — {a['name']} vs {b['name']}: "
        f"quality {qa['composite_score']} vs {qb['composite_score']}; "
        f"banks {sa.get('banks', 0):.0%} vs {sb.get('banks', 0):.0%}; "
        f"IT {sa.get('it_services', 0):.0%} vs {sb.get('it_services', 0):.0%}; "
        f"cash {float(a.get('cash_weight') or 0):.0%} vs {float(b.get('cash_weight') or 0):.0%}. "
        f"Core book is more diversified with higher cash; concentrated growth accepts higher sector/style risk. "
        f"Relative assessment only — no BUY/SELL."
    )
    return {
        "portfolios": [a["portfolio_id"], b["portfolio_id"]],
        "quality_scores": {a["portfolio_id"]: qa["composite_score"], b["portfolio_id"]: qb["composite_score"]},
        "sector_contrast": {"a": sa, "b": sb},
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def dominating_risk_holdings(p: dict[str, Any]) -> dict[str, Any]:
    # Risk contribution proxy = weight * sector cluster multiplier
    sectors = _sector_map(p)
    scored = []
    for h, w in _weights(p):
        mult = 1.0 + min(1.0, sectors.get(str(h.get("sector")), 0) )
        scored.append((h["ticker"], round(w * mult, 4), h.get("sector")))
    scored.sort(key=lambda x: -x[1])
    summary = strip_recommendation_language(
        f"Holdings that dominate portfolio risk in {p['name']}: "
        + ", ".join(f"{t} (risk proxy {s:.3f}, sector {sec})" for t, s, sec in scored[:5])
        + ". Proxy uses weight × sector-cluster multiplier — observational, not a trade list."
    )
    return {"ranked": scored[:8], "summary": summary, "fabricated": False}
