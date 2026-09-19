"""Module 6 — Unified Company Intelligence Object (one canonical company)."""

from __future__ import annotations

from typing import Any

from knowledge_unification.schema import ProviderResult, QueryPlan


_EMPTY_COMPANY = {
    "identity": {},
    "business": {},
    "products": {},
    "market": {},
    "financial_snapshot": {},
    "ownership": {},
    "industry": {},
    "competitors": {},
    "memory": {},
    "filings": {},
    "research": {},
    "coverage": {},
    "guidance": {},
    "valuation": {},
    "capital_allocation": {},
    "risk": {},
    "investment": {},
    "portfolio": {},
}


def build_company_intelligence(
    query: QueryPlan,
    results: list[ProviderResult],
) -> dict[str, Any]:
    obj = {k: dict(v) if isinstance(v, dict) else v for k, v in _EMPTY_COMPANY.items()}
    ticker = query.ticker_hint
    name = query.company_hint
    sources: list[str] = []

    for r in results:
        if r.empty or not r.ok:
            continue
        sources.append(r.provider_id)
        raw = r.raw or {}

        if r.provider_id == "capiq_ikt":
            ident = raw.get("identity") or {}
            ticker = ticker or ident.get("ticker")
            name = name or ident.get("name")
            obj["identity"].update({k: v for k, v in ident.items() if v is not None})
            if raw.get("market"):
                obj["market"].update(raw["market"])
            if raw.get("financials"):
                obj["financial_snapshot"].update(raw["financials"])
            if raw.get("products"):
                obj["products"]["catalog"] = raw["products"]
            if raw.get("competitors"):
                obj["competitors"]["peers"] = raw["competitors"]
            if r.summary:
                obj["business"]["description"] = r.summary
            for f in r.facts:
                field = f.get("field")
                if field == "parent_company":
                    obj["ownership"]["parent_company"] = f.get("value")
                if field and str(field).startswith("returns_"):
                    obj["market"][str(field)] = f.get("value")
                if field and "earnings_date" in str(field):
                    obj["coverage"][str(field)] = f.get("value")
                if field == "investors":
                    obj["ownership"]["investors"] = f.get("value")

        elif r.provider_id == "company_memory":
            obj["memory"] = raw.get("memory") or {"present": True}
            obj["memory"]["confidence"] = raw.get("confidence")

        elif r.provider_id == "ikl":
            obj["memory"]["ikl_layers"] = (raw.get("layers_hit") or raw.get("layers") or [])
            if r.why:
                obj["memory"]["ikl_hints"] = r.why[:5]

        elif r.provider_id == "knowledge_factory":
            obj["research"]["knowledge_factory"] = {
                "summary": r.summary,
                "keys": list(raw.keys())[:20],
            }
            sector = raw.get("sector") or (raw.get("identity") or {}).get("sector")
            if sector:
                obj["industry"]["sector"] = sector

        elif r.provider_id == "business_intelligence":
            ticker = ticker or raw.get("ticker")
            name = name or raw.get("company")
            if raw.get("industry"):
                obj["industry"]["key"] = raw.get("industry")
            bm = raw.get("business_model") or {}
            if isinstance(bm, dict):
                if bm.get("business_type"):
                    obj["business"]["business_type"] = bm.get("business_type")
                if bm.get("how_it_makes_money"):
                    obj["business"]["how_it_makes_money"] = bm.get("how_it_makes_money")
            if raw.get("moat"):
                obj["business"]["moat"] = raw.get("moat")
            if raw.get("unit_economics"):
                obj["business"]["unit_economics"] = raw.get("unit_economics")
            if raw.get("risks"):
                obj["risk"]["business_risks"] = raw.get("risks")
            if r.summary and not obj["business"].get("description"):
                obj["business"]["description"] = r.summary

        elif r.provider_id == "industry_intelligence":
            if raw.get("industry"):
                obj["industry"]["key"] = raw.get("industry")
                obj["industry"]["name"] = raw.get("industry_name")
                obj["industry"]["from_industry_dna"] = True
                dna = raw.get("dna") if isinstance(raw.get("dna"), dict) else {}
                if dna:
                    obj["industry"]["dna"] = {
                        "valuation_methods": dna.get("valuation_methods"),
                        "competitive_structure": dna.get("competitive_structure"),
                        "primary_cycle": dna.get("primary_cycle"),
                    }

        elif r.provider_id == "investment_intelligence":
            obj["investment"]["from_investment_intelligence"] = True
            obj["investment"]["entity"] = raw.get("entity")
            obj["investment"]["modules_used"] = raw.get("modules_used") or []
            obj["investment"]["recommendation_policy"] = raw.get("recommendation_policy")
            obj["investment"]["recommendation"] = None
            if raw.get("quality"):
                obj["investment"]["quality"] = raw.get("quality")
            if raw.get("thesis"):
                obj["investment"]["thesis"] = raw.get("thesis")
            if raw.get("unknowns"):
                obj["investment"]["unknowns"] = raw.get("unknowns")
            if raw.get("monitoring_points"):
                obj["investment"]["monitoring_points"] = raw.get("monitoring_points")
            if r.summary:
                obj["investment"]["summary"] = r.summary

        elif r.provider_id == "research_intelligence":
            obj["research"]["from_research_intelligence"] = True
            obj["research"]["entity"] = raw.get("entity")
            obj["research"]["modules_used"] = raw.get("modules_used") or []
            obj["research"]["recommendation_policy"] = raw.get("recommendation_policy")
            obj["research"]["knowledge_authority"] = raw.get("knowledge_authority")
            if raw.get("memory"):
                obj["research"]["memory"] = raw.get("memory")
            if raw.get("timeline"):
                obj["research"]["timeline"] = raw.get("timeline")
            if raw.get("unknowns"):
                obj["research"]["unknowns"] = raw.get("unknowns")
            if r.summary:
                obj["research"]["summary"] = r.summary

        elif r.provider_id == "portfolio_intelligence":
            obj["portfolio"]["from_portfolio_intelligence"] = True
            obj["portfolio"]["portfolio_id"] = raw.get("portfolio_id")
            obj["portfolio"]["modules_used"] = raw.get("modules_used") or []
            obj["portfolio"]["recommendation_policy"] = raw.get("recommendation_policy")
            if r.summary:
                obj["portfolio"]["summary"] = r.summary

        elif r.provider_id == "cgl":
            obj["research"]["cgl_extracts"] = (raw.get("extracts") or [])[:5]

        elif r.provider_id == "legacy_kip":
            obj["filings"]["legacy_kip_hits"] = raw.get("hits") or []

    obj["identity"]["ticker"] = ticker
    obj["identity"]["name"] = name
    obj["coverage"]["sources"] = sources
    obj["coverage"]["populated_sections"] = sorted(
        k for k, v in obj.items() if isinstance(v, dict) and v and k != "coverage"
    )
    return obj
