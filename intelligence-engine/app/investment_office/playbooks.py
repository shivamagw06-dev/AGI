"""Reusable investment playbooks — structural industry templates, not market forecasts."""

from __future__ import annotations

from typing import Any

# Identity knowledge templates. Not live valuations or trade calls.
PLAYBOOKS: dict[str, dict[str, Any]] = {
    "indian_banking": {
        "id": "indian_banking",
        "title": "Indian Banking",
        "industry_overview": (
            "Deposit-funded lenders and capital-markets adjacent banks serving retail, "
            "SME and wholesale credit in India."
        ),
        "business_model": "Net interest margin + fees − credit costs; deposit franchise and capital adequacy.",
        "kpis": ["NIM", "NPA / slippages", "CASA", "PCR", "CET1", "loan growth"],
        "valuation_methods": ["P/B vs RoE", "P/E", "embedded value for bancassurance where disclosed"],
        "risks": ["Credit cycle", "rate/liquidity shocks", "regulatory capital", "governance"],
        "catalysts": ["Credit upcycle", "NIMs stabilizing", "fee income", "capital raises / M&A"],
        "historical_cycles": "Credit boom → asset-quality stress → repair → re-rating.",
        "leading_companies": ["HDFCBANK", "ICICIBANK", "SBIN", "KOTAKBANK", "AXISBANK"],
        "themes": ["rates", "credit", "financials"],
    },
    "indian_it": {
        "id": "indian_it",
        "title": "Indian IT",
        "industry_overview": "Global capability centers and IT services exporters (USD revenue, INR cost base).",
        "business_model": "Time & materials / fixed-price digital + cloud + engineering services.",
        "kpis": ["Revenue growth", "EBIT margin", "deal TCV", "attrition", "utilization", "USD/INR"],
        "valuation_methods": ["P/E", "EV/EBITDA", "PEG vs growth"],
        "risks": ["Client discretionary spend", "visa/wage inflation", "currency", "AI disruption narrative"],
        "catalysts": ["Large deal wins", "vertical recovery", "GenAI offerings", "margin expansion"],
        "historical_cycles": "Global IT spend cycles; India IT often lags US enterprise budgets.",
        "leading_companies": ["TCS", "INFY", "HCLTECH", "WIPRO", "TECHM"],
        "themes": ["exports", "usd_inr", "technology"],
    },
    "power": {
        "id": "power",
        "title": "Power",
        "industry_overview": "Generation, transmission, distribution and renewables across India.",
        "business_model": "Regulated returns / PPAs / merchant power; renewables with capacity additions.",
        "kpis": ["PLF", "PPA tenor", "receivables", "capacity additions", "leverage"],
        "valuation_methods": ["P/B", "EV/EBITDA", "DCF on contracted cash flows"],
        "risks": ["Fuel cost", "DISCOM receivables", "policy/tariff", "execution delays"],
        "catalysts": ["RE bidding", "transmission awards", "tariff orders"],
        "historical_cycles": "Capex waves tied to policy and fuel cycles.",
        "leading_companies": ["NTPC", "POWERGRID", "TATAPOWER", "ADANIGREEN"],
        "themes": ["energy", "policy", "capex"],
    },
    "defence": {
        "id": "defence",
        "title": "Defence",
        "industry_overview": "Indian defence manufacturing and platforms under indigenisation push.",
        "business_model": "Order-book driven OEM / components with multi-year execution.",
        "kpis": ["Order book", "execution", "margins", "working capital", "export orders"],
        "valuation_methods": ["P/E on execution", "EV/order book", "peer multiples"],
        "risks": ["Order timing", "execution", "geopolitics", "offset / policy"],
        "catalysts": ["Budget allocations", "export wins", "platform clearances"],
        "historical_cycles": "Long gestation; sentiment swings with budget and geopolitics.",
        "leading_companies": ["HAL", "BEL", "BDL", "MAZDOCK"],
        "themes": ["policy", "capex", "geopolitics"],
    },
    "capital_goods": {
        "id": "capital_goods",
        "title": "Capital Goods",
        "industry_overview": "Industrial equipment, engineering and project companies tied to capex cycles.",
        "business_model": "Order inflows → execution → margin on projects / products.",
        "kpis": ["Order inflow", "order book / sales", "execution", "working capital", "margins"],
        "valuation_methods": ["P/E", "EV/EBITDA", "order-book coverage"],
        "risks": ["Capex delay", "commodity costs", "project overruns"],
        "catalysts": ["Private/public capex", "PLI adjacent demand", "exports"],
        "historical_cycles": "Strongly cyclical with domestic investment.",
        "leading_companies": ["LT", "SIEMENS", "ABB", "CUMMINSIND"],
        "themes": ["capex", "industrials"],
    },
    "fmcg": {
        "id": "fmcg",
        "title": "FMCG",
        "industry_overview": "Packaged consumer goods — staples and discretionary brands.",
        "business_model": "Brand + distribution; volume × realisation − RM / opex.",
        "kpis": ["Volume growth", "realisations", "GM", "A&P", "rural/urban mix"],
        "valuation_methods": ["P/E", "EV/EBITDA", "premium to staples peers"],
        "risks": ["RM inflation", "rural slowdown", "competition / private label"],
        "catalysts": ["Volume recovery", "premiumisation", "distribution reach"],
        "historical_cycles": "Defensive volumes with RM margin cycles.",
        "leading_companies": ["HINDUNILVR", "ITC", "NESTLEIND", "BRITANNIA"],
        "themes": ["consumption", "rural", "inflation"],
    },
    "healthcare": {
        "id": "healthcare",
        "title": "Healthcare",
        "industry_overview": "Pharma, hospitals and diagnostics serving domestic and export markets.",
        "business_model": "Formulations / API / hospital ARPOB / diagnostic volumes.",
        "kpis": ["Revenue growth", "margins", "USFDA / regulatory", "occupancy", "ARPOB"],
        "valuation_methods": ["P/E", "EV/EBITDA", "pipeline-adjusted where disclosed"],
        "risks": ["Regulatory", "pricing", "concentration", "input costs"],
        "catalysts": ["Approvals", "hospital expansion", "export recovery"],
        "historical_cycles": "Regulatory and US generics pricing cycles for pharma.",
        "leading_companies": ["SUNPHARMA", "DRREDDY", "APOLLOHOSP", "DIVISLAB"],
        "themes": ["healthcare", "regulation", "exports"],
    },
}


def list_playbooks(ids: list[str] | None = None) -> list[dict[str, Any]]:
    if not ids:
        return [dict(p) for p in PLAYBOOKS.values()]
    out: list[dict[str, Any]] = []
    for pid in ids:
        key = pid.strip().lower().replace(" ", "_")
        if key in PLAYBOOKS:
            out.append(dict(PLAYBOOKS[key]))
    return out or [dict(p) for p in PLAYBOOKS.values()]


def playbook_for_sector(sector: str | None) -> dict[str, Any] | None:
    if not sector:
        return None
    s = sector.lower()
    mapping = [
        (("bank", "financial"), "indian_banking"),
        (("it", "tech", "software"), "indian_it"),
        (("power", "utilit", "renew"), "power"),
        (("defence", "defense", "aero"), "defence"),
        (("capital", "industrial", "engineer"), "capital_goods"),
        (("fmcg", "consumer staples", "staples"), "fmcg"),
        (("health", "pharma", "hospital"), "healthcare"),
    ]
    for keys, pid in mapping:
        if any(k in s for k in keys):
            return dict(PLAYBOOKS[pid])
    return None
