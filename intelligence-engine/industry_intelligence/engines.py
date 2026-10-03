"""Deterministic Industry Intelligence engines — all read Industry DNA."""

from __future__ import annotations

from typing import Any, Optional

from industry_intelligence.dna_catalog import INDUSTRY_DNA, get_dna
from industry_intelligence.registry import resolve_industry


def dna_view(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    out = d.to_dict()
    out["found"] = True
    return out


def economics(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    return {
        "found": True,
        "industry": key,
        "name": d.name,
        "revenue_drivers": list(d.revenue_drivers),
        "margin_drivers": list(d.margin_drivers),
        "cost_drivers": list(d.cost_drivers),
        "value_drivers": list(d.value_drivers),
        "capital_intensity": d.capital_intensity,
        "working_capital": d.working_capital,
        "cash_conversion": d.cash_conversion,
        "operating_leverage": d.operating_leverage,
        "pricing_power": d.pricing_power,
        "why_margins": d.why_margins,
        "why_roic": d.why_roic,
        "why_leverage": d.why_leverage,
        "why_working_capital": d.why_working_capital,
        "summary": (
            f"{d.name} economics: revenue from {', '.join(d.revenue_drivers[:3])}; "
            f"margins shaped by {', '.join(d.margin_drivers[:3])}. {d.why_margins} "
            f"Capital intensity: {d.capital_intensity}. "
            f"Cash conversion: {d.cash_conversion}. "
            f"Working capital: {d.working_capital}."
        ),
        "fabricated": False,
    }


def kpis(key: str, kpi_key: Optional[str] = None) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    cards = [k.to_dict() for k in d.kpis]
    if kpi_key:
        hit = next((c for c in cards if c["key"] == kpi_key or c["name"].lower() == kpi_key.lower()), None)
        if not hit:
            # fuzzy name contains
            low = kpi_key.lower().replace("_", " ")
            hit = next((c for c in cards if low in c["name"].lower() or low in c["key"]), None)
        return {
            "found": bool(hit),
            "industry": key,
            "kpi": hit,
            "summary": (
                f"{hit['name']}: {hit['definition']} Importance: {hit['importance']}. "
                f"Good range: {hit['good_range']}. Poor range: {hit['poor_range']}."
                if hit else f"No KPI matching '{kpi_key}' for {d.name}."
            ),
            "fabricated": False,
        }
    return {
        "found": True,
        "industry": key,
        "kpis": cards,
        "summary": f"{d.name} KPIs: " + ", ".join(k.name for k in d.kpis) + ".",
        "fabricated": False,
    }


def valuation(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    return {
        "found": True,
        "industry": key,
        "name": d.name,
        "valuation_methods": list(d.valuation_methods),
        "why": d.valuation_why,
        "why_valuation": d.why_valuation,
        "summary": (
            f"{d.name} is typically valued using {', '.join(d.valuation_methods)} — {d.valuation_why}"
        ),
        "fabricated": False,
        "policy": "never_universal_valuation",
    }


def regulation(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    return {
        "found": True,
        "industry": key,
        "regulators": list(d.regulators),
        "regulatory_risks": list(d.regulatory_risks),
        "summary": (
            f"{d.name} is primarily regulated by {', '.join(d.regulators)}. "
            f"Key regulatory risks: {', '.join(d.regulatory_risks)}."
        ),
        "fabricated": False,
    }


def competition(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    return {
        "found": True,
        "industry": key,
        "competitive_structure": d.competitive_structure,
        "concentration": d.concentration,
        "porter": d.porter.to_dict(),
        "summary": (
            f"{d.name} structure is {d.competitive_structure} ({d.concentration}). "
            f"Rivalry: {d.porter.rivalry}. Entry barriers: {d.porter.entry_barriers}."
        ),
        "fabricated": False,
    }


def cycle(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    return {
        "found": True,
        "industry": key,
        "primary_cycle": d.primary_cycle,
        "lifecycle": d.lifecycle,
        "typical_growth": d.typical_growth,
        "macro_sensitivity": list(d.macro_sensitivity),
        "summary": (
            f"{d.name} maps primarily to the {d.primary_cycle.replace('_', ' ')} "
            f"(lifecycle: {d.lifecycle}). Macro sensitivity: {', '.join(d.macro_sensitivity)}."
        ),
        "fabricated": False,
    }


def risks(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    return {
        "found": True,
        "industry": key,
        "typical_risks": list(d.typical_risks),
        "risk_weightings": dict(d.risk_weightings),
        "summary": (
            f"Primary {d.name} risks: {', '.join(d.typical_risks)}. "
            f"Weightings differ by industry — "
            + ", ".join(f"{k}={v}" for k, v in list(d.risk_weightings.items())[:5])
            + "."
        ),
        "fabricated": False,
    }


def graph(key: str) -> dict[str, Any]:
    d = get_dna(key)
    if not d:
        return {"found": False, "key": key, "fabricated": False}
    return {
        "found": True,
        "industry": key,
        "customers": list(d.customers),
        "suppliers": list(d.suppliers),
        "regulators": list(d.regulators),
        "adjacent_industries": list(d.adjacent_industries),
        "substitutes": list(d.substitutes),
        "macroeconomic_drivers": list(d.macro_sensitivity),
        "capital_allocation_typical": d.capital_allocation_typical,
        "summary": (
            f"{d.name} graph — customers: {', '.join(d.customers[:3])}; "
            f"suppliers: {', '.join(d.suppliers[:3])}; "
            f"adjacent: {', '.join(d.adjacent_industries[:3])}."
        ),
        "fabricated": False,
    }


# Cross-industry pedagogy answers (deterministic)
_CROSS_INDUSTRY_ANSWERS: list[tuple[str, str, str]] = [
    (
        r"why do banks (use |trade on )?p/?b|why .*banks.*price.to.book|why .*p/?b.*banks",
        "banks",
        "Banks use P/B because book equity is the scarce regulatory capital that earns the net interest spread — "
        "P/B embeds ROE versus cost of equity. EV/EBITDA is not meaningful for deposit-funded lenders.",
    ),
    (
        r"why do (saas|software).*ev/?sales|why .*ev/?sales.*saas|why .*software.*trade on ev",
        "software",
        "SaaS/software often trades on EV/Sales (or EV/ARR) because growth-stage businesses invest heavily in S&M/R&D "
        "before mature free cash flow — revenue scale and retention quality are the interim value anchors. "
        "As FCF margins mature, valuation typically migrates toward FCF-based methods.",
    ),
    (
        r"why do airlines.*(low|poor) roic|why .*airlines.*low returns|why airlines earn low",
        "airlines",
        "Airlines earn structurally low ROIC because extreme capital intensity (fleet/leases), fierce price competition, "
        "and high operating leverage on load factor compress mid-cycle returns — good years rarely compensate for "
        "cycle troughs and reinvestment needs.",
    ),
    (
        r"why do fmcg.*(high|strong) fcf|why .*fmcg.*free cash|why fmcg companies produce high fcf",
        "fmcg",
        "FMCG generates high free cash flow because brand-driven pricing power, relatively modest growth capex, "
        "and often favorable working-capital (distributor advances / fast inventory turns) convert earnings to cash.",
    ),
    (
        r"why do utilities.*(more|higher|carry).*debt|why .*utilities.*leverage|why utilities carry more debt",
        "utilities",
        "Utilities carry more debt because regulated cash flows and asset bases (RAB) support higher financial leverage "
        "at investment-grade costs — regulators often allow a geared capital structure in the allowed return framework.",
    ),
    (
        r"why do hospitals.*(higher|high).*working capital|why .*hospitals.*receivable|why hospitals have higher working capital",
        "hospitals",
        "Hospitals tie working capital in insurer/government receivables and medical consumable inventory — "
        "payer mix and collection cycles keep cash conversion slower than cash-retail models despite occupancy leverage.",
    ),
    (
        r"why .*telecom.*ev/?ebitda|why do telecoms? use ev/?ebitda",
        "telecom",
        "Telecom uses EV/EBITDA because spectrum and network assets create large depreciation/amortization and leverage "
        "differences — EBITDA normalizes capital structure and non-cash charges better than P/E.",
    ),
    (
        r"why .*real estate.*nav|why (is |do )?(realty|real estate).*nav|why is nav used for real estate",
        "real_estate",
        "Real estate is valued on NAV because value resides in the property portfolio's appraised/market asset value "
        "minus liabilities — earnings multiples miss inventory and development-stage asset value.",
    ),
    (
        r"why .*insur\w*.*embedded value|why (use |do )?embedded value.*insur|why do insur",
        "insurance",
        "Insurance uses Embedded Value because economic value sits in the in-force book and new-business franchise "
        "(VNB), which period GAAP profit alone does not capture for long-duration contracts.",
    ),
    (
        r"why .*commodity.*replacement|why .*metals.*ev/?ebitda|why do commodity",
        "metals",
        "Commodity industries use EV/EBITDA and replacement cost because earnings are cycle-volatile — "
        "replacement cost anchors the capital required to recreate capacity when mid-cycle earnings mislead.",
    ),
    (
        r"saas.*(scale|differ).*(it services|its)|it services.*(scale|differ).*saas|"
        r"why do saas companies scale differently",
        "software",
        "SaaS scales differently from IT services because incremental seats drop through at high gross margin "
        "with negative working capital (deferred revenue), while IT services remain utilization- and "
        "headcount-linked — growth consumes hiring and wage inflation rather than pure software leverage.",
    ),
    (
        r"airline.*(rail|railway)|railway.*(airline)|compare airlines? and railways?",
        "airlines",
        "Airlines are price-competitive, fuel- and fleet-capital intensive with thin mid-cycle ROIC; "
        "railways (where private comps exist) are denser network/infrastructure plays with different "
        "regulation and lower discretionary yield volatility — capital intensity stays high but pricing "
        "and cycle mapping diverge.",
    ),
    (
        r"banks? vs\.? nbfcs?|nbfcs? vs\.? banks?|funding models differ",
        "banks",
        "Banks fund primarily via deposits/CASA (sticky, regulated franchise) while NBFCs rely more on "
        "wholesale borrowings — so banks defend NIM through CASA and NBFCs live on spread over funding cost "
        "with higher refinancing sensitivity.",
    ),
]


def cross_industry(question: str) -> dict[str, Any]:
    import re

    q = (question or "").strip().lower()
    for pattern, industry, answer in _CROSS_INDUSTRY_ANSWERS:
        if re.search(pattern, q, re.I):
            return {
                "found": True,
                "industry": industry,
                "summary": answer,
                "why": [f"Cross-industry pedagogy anchored to {industry} Industry DNA."],
                "fabricated": False,
            }
    # Generic compare two industries if "vs" present
    from industry_intelligence.registry import resolve_industry as resolve

    # Try extract two industry mentions
    keys = []
    for key in sorted(INDUSTRY_DNA.keys(), key=len, reverse=True):
        name = INDUSTRY_DNA[key].name.lower()
        if key.replace("_", " ") in q or name.lower() in q or any(a in q for a in INDUSTRY_DNA[key].aliases):
            if key not in keys:
                keys.append(key)
        if len(keys) >= 2:
            break
    if len(keys) >= 2:
        a, b = get_dna(keys[0]), get_dna(keys[1])
        assert a and b
        summary = (
            f"{a.name} vs {b.name}: valuation ({', '.join(a.valuation_methods[:2])} vs "
            f"{', '.join(b.valuation_methods[:2])}); capital intensity differs — "
            f"{a.capital_intensity[:80]} vs {b.capital_intensity[:80]}; "
            f"primary cycle {a.primary_cycle.replace('_', ' ')} vs {b.primary_cycle.replace('_', ' ')}."
        )
        return {
            "found": True,
            "industry": keys[0],
            "compare": keys[:2],
            "summary": summary,
            "why": [a.why_valuation, b.why_valuation],
            "fabricated": False,
        }
    return {"found": False, "summary": "", "fabricated": False}
