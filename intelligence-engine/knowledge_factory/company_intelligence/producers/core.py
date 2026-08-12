"""Produce all ICI modules from soft context — never fabricate."""

from __future__ import annotations

from typing import Any

from knowledge_factory.company_intelligence.provenance import field, module_block
from knowledge_factory.company_intelligence.schema import UNKNOWN


def _f(value: Any, *, source: str, collector: str, confidence: float = 0.75, derived_from: list[str] | None = None) -> dict[str, Any]:
    return field(value, source=source, collector=collector, confidence=confidence, derived_from=derived_from)


def _seed_fields(seed_mod: dict[str, Any] | None, keys: list[str], *, source: str, collector: str, confidence: float) -> dict[str, Any]:
    seed_mod = seed_mod or {}
    out: dict[str, Any] = {}
    for k in keys:
        out[k] = _f(seed_mod.get(k, UNKNOWN), source=source, collector=collector, confidence=confidence, derived_from=["institutional_seed"])
    return out


def _unknown_fields(keys: list[str], *, collector: str) -> dict[str, Any]:
    return {k: _f(UNKNOWN, source="unavailable", collector=collector, confidence=0.0) for k in keys}


IDENTITY_KEYS = [
    "company_name", "legal_name", "nse_symbol", "bse_symbol", "isin", "cin",
    "exchange", "listing_date", "registered_office", "headquarters", "website",
    "industry", "sector", "sub_industry", "market_cap_category", "index_membership",
    "corporate_status", "lifecycle",
]

BM_KEYS = [
    "business_description", "business_model", "revenue_model", "operating_model",
    "pricing_model", "asset_intensity", "manufacturing_or_services", "export_driven",
    "domestic_driven", "recurring_revenue", "project_revenue", "subscription_revenue",
    "capital_intensity", "operating_leverage", "business_complexity",
]

PRODUCT_KEYS = [
    "products", "brands", "business_lines", "product_categories", "revenue_contribution",
    "lifecycle", "competitive_position", "growth_drivers", "future_opportunities",
]

SEGMENT_KEYS = [
    "operating_segments", "business_segments", "revenue_mix", "ebit_mix",
    "growth", "margins", "historical_changes",
]

CUSTOMER_KEYS = [
    "customer_categories", "government", "retail", "enterprise", "exports",
    "customer_concentration", "distribution", "sales_channels", "geographic_mix",
]

MGMT_KEYS = [
    "ceo", "cfo", "chairperson", "board_members", "independent_directors",
    "management_history", "appointments", "resignations", "executive_tenure", "leadership_timeline",
]

OWN_KEYS = [
    "promoters", "promoter_holding", "fii", "dii", "mutual_funds", "insurance",
    "public", "pledged_shares", "insider_transactions", "historical_ownership",
]

CAP_KEYS = [
    "dividends", "buybacks", "acquisitions", "demergers", "rights", "bonus", "splits",
    "capex", "debt_reduction", "equity_raises", "capital_allocation_history",
]

COMP_KEYS = [
    "primary_competitors", "market_position", "industry_rank",
    "competitive_advantages", "competitive_risks", "industry_leadership",
]

QUALITY_KEYS = [
    "capital_allocation", "growth_quality", "cash_conversion",
    "margin_stability", "roic_trend", "business_durability",
]

RISK_KEYS = [
    "commodity_risk", "fx_risk", "regulatory_risk", "technology_risk",
    "customer_risk", "supplier_risk", "execution_risk", "litigation", "environmental_risk",
]


def produce_identity(ctx: dict[str, Any]) -> dict[str, Any]:
    t = ctx["ticker"]
    seed = (ctx.get("seed") or {}).get("identity")
    dna = ctx.get("dna") or {}
    collector = "ici.collectors.identity"
    if seed:
        fields = _seed_fields(seed, IDENTITY_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("identity", fields, source="institutional_seed", collector=collector, confidence=0.95)

    master = ctx.get("warehouse_company") or {}
    sector = ctx.get("sector") or UNKNOWN
    display = dna.get("display_name") or sector
    fields = {
        "company_name": _f(master.get("company_name") or t, source="institutional_warehouse" if master else "ticker", collector=collector, confidence=0.9 if master else 0.6, derived_from=["company_master"] if master else ["ticker"]),
        "legal_name": _f(master.get("legal_name") or UNKNOWN, source="institutional_warehouse" if master.get("legal_name") else "unavailable", collector=collector, confidence=0.9 if master.get("legal_name") else 0.0),
        "nse_symbol": _f(t, source="institutional_warehouse" if master else "ticker", collector=collector, confidence=0.95, derived_from=["company_master"] if master else ["ticker"]),
        "bse_symbol": _f(master.get("bse_symbol") or UNKNOWN, source="institutional_warehouse" if master.get("bse_symbol") else "unavailable", collector=collector, confidence=0.9 if master.get("bse_symbol") else 0.0),
        "isin": _f(master.get("isin") or UNKNOWN, source="institutional_warehouse" if master.get("isin") else "unavailable", collector=collector, confidence=0.95 if master.get("isin") else 0.0),
        "cin": _f(UNKNOWN, source="unavailable", collector=collector),
        "exchange": _f(master.get("exchange") or "NSE", source="institutional_warehouse" if master else "ticker", collector=collector, confidence=0.9, derived_from=["company_master"] if master else ["ticker"]),
        "listing_date": _f(UNKNOWN, source="unavailable", collector=collector),
        "registered_office": _f(UNKNOWN, source="unavailable", collector=collector),
        "headquarters": _f(UNKNOWN, source="unavailable", collector=collector),
        "website": _f(master.get("website") or UNKNOWN, source="institutional_warehouse" if master.get("website") else "unavailable", collector=collector, confidence=0.85 if master.get("website") else 0.0),
        "industry": _f(master.get("industry") or display, source="institutional_warehouse" if master.get("industry") else "institutional_sector_prior", collector=collector, confidence=0.9 if master.get("industry") else 0.7, derived_from=["company_master"] if master.get("industry") else ["sector_dna"]),
        "sector": _f(sector, source="institutional_warehouse" if master.get("sector") else "nifty500_universe", collector=collector, confidence=0.9, derived_from=["company_master"] if master.get("sector") else ["nifty500_sector"]),
        "sub_industry": _f(master.get("sub_industry") or UNKNOWN, source="institutional_warehouse" if master.get("sub_industry") else "unavailable", collector=collector, confidence=0.85 if master.get("sub_industry") else 0.0),
        "market_cap_category": _f("Nifty 500 constituent", source="nifty500_universe", collector=collector, confidence=0.7, derived_from=["nifty500"]),
        "index_membership": _f(["NIFTY 500"], source="nifty500_universe", collector=collector, confidence=0.9, derived_from=["nifty500"]),
        "corporate_status": _f("Active", source="nifty500_universe", collector=collector, confidence=0.6, derived_from=["nifty500"]),
        "lifecycle": _f(dna.get("industry_maturity") or UNKNOWN, source="institutional_sector_prior", collector=collector, confidence=0.55, derived_from=["sector_dna"]),
    }
    return module_block("identity", fields, source="nifty500_universe+sector_dna", collector=collector, confidence=0.7)


def produce_business_model(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.business_model"
    seed = (ctx.get("seed") or {}).get("business_model")
    if seed:
        fields = _seed_fields(seed, BM_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("business_model", fields, source="institutional_seed", collector=collector, confidence=0.95)

    dna = ctx.get("dna") or {}
    biz = ctx.get("ticker_business") or {}
    bm = biz.get("business_model") or dna.get("business_model") or UNKNOWN
    source = "company_analysis" if biz.get("business_model") else ("institutional_sector_prior" if dna else "unavailable")
    conf = 0.85 if biz.get("business_model") else (0.55 if dna else 0.0)
    asset = dna.get("asset_intensity")
    cap = dna.get("capital_intensity")
    olev = dna.get("operating_leverage")
    # Soft sector priors only — never invent company-specific narrative beyond DNA/ticker_business.
    export_driven = True if ctx.get("sector") == "it_services" else (False if ctx.get("sector") in {"banks", "nbfc", "fmcg", "retail"} else UNKNOWN)
    domestic = True if export_driven is False else (False if export_driven is True else UNKNOWN)
    mfg_svc = "Services" if ctx.get("sector") in {"it_services", "banks", "nbfc", "insurance", "telecom"} else (
        "Manufacturing" if ctx.get("sector") in {"auto", "pharma", "cement", "metals", "fmcg"} else UNKNOWN
    )
    fields = {
        "business_description": _f(bm, source=source, collector=collector, confidence=conf, derived_from=["sector_dna", "ticker_business"]),
        "business_model": _f(bm, source=source, collector=collector, confidence=conf, derived_from=["sector_dna", "ticker_business"]),
        "revenue_model": _f(UNKNOWN if not dna else f"Sector-typical: {dna.get('margin_profile', UNKNOWN)}", source="institutional_sector_prior" if dna else "unavailable", collector=collector, confidence=0.45 if dna else 0.0, derived_from=["sector_dna"]),
        "operating_model": _f(UNKNOWN, source="unavailable", collector=collector),
        "pricing_model": _f(UNKNOWN, source="unavailable", collector=collector),
        "asset_intensity": _f(asset.title().replace("_", " ") if isinstance(asset, str) else UNKNOWN, source="institutional_sector_prior" if asset else "unavailable", collector=collector, confidence=0.55 if asset else 0.0, derived_from=["sector_dna"]),
        "manufacturing_or_services": _f(mfg_svc, source="institutional_sector_prior" if mfg_svc != UNKNOWN else "unavailable", collector=collector, confidence=0.5 if mfg_svc != UNKNOWN else 0.0, derived_from=["sector_map"]),
        "export_driven": _f(export_driven, source="institutional_sector_prior" if export_driven != UNKNOWN else "unavailable", collector=collector, confidence=0.5 if export_driven != UNKNOWN else 0.0, derived_from=["sector_map"]),
        "domestic_driven": _f(domestic, source="institutional_sector_prior" if domestic != UNKNOWN else "unavailable", collector=collector, confidence=0.5 if domestic != UNKNOWN else 0.0, derived_from=["sector_map"]),
        "recurring_revenue": _f(UNKNOWN, source="unavailable", collector=collector),
        "project_revenue": _f(UNKNOWN, source="unavailable", collector=collector),
        "subscription_revenue": _f(UNKNOWN, source="unavailable", collector=collector),
        "capital_intensity": _f(str(cap).replace("_", " ") if cap else UNKNOWN, source="institutional_sector_prior" if cap else "unavailable", collector=collector, confidence=0.55 if cap else 0.0, derived_from=["sector_dna"]),
        "operating_leverage": _f(str(olev).replace("_", " ") if olev else UNKNOWN, source="institutional_sector_prior" if olev else "unavailable", collector=collector, confidence=0.55 if olev else 0.0, derived_from=["sector_dna"]),
        "business_complexity": _f(UNKNOWN, source="unavailable", collector=collector),
    }
    return module_block("business_model", fields, source=source, collector=collector, confidence=conf)


def produce_products(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.products"
    seed = (ctx.get("seed") or {}).get("products")
    if seed:
        fields = _seed_fields(seed, PRODUCT_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("products", fields, source="institutional_seed", collector=collector, confidence=0.95)

    biz = ctx.get("ticker_business") or {}
    dna = ctx.get("dna") or {}
    products = biz.get("products")
    brands = biz.get("brands")
    fields = {
        "products": _f(products.split(", ") if isinstance(products, str) else (products or UNKNOWN), source="company_analysis" if products else "unavailable", collector=collector, confidence=0.8 if products else 0.0, derived_from=["ticker_business"]),
        "brands": _f(brands.split(", ") if isinstance(brands, str) else (brands or UNKNOWN), source="company_analysis" if brands else "unavailable", collector=collector, confidence=0.8 if brands else 0.0, derived_from=["ticker_business"]),
        "business_lines": _f(UNKNOWN, source="unavailable", collector=collector),
        "product_categories": _f(UNKNOWN, source="unavailable", collector=collector),
        "revenue_contribution": _f(UNKNOWN, source="unavailable", collector=collector),
        "lifecycle": _f(dna.get("industry_maturity") or UNKNOWN, source="institutional_sector_prior" if dna else "unavailable", collector=collector, confidence=0.45 if dna else 0.0, derived_from=["sector_dna"]),
        "competitive_position": _f(UNKNOWN, source="unavailable", collector=collector),
        "growth_drivers": _f(list(dna.get("growth_drivers") or []) or UNKNOWN, source="institutional_sector_prior" if dna.get("growth_drivers") else "unavailable", collector=collector, confidence=0.5 if dna.get("growth_drivers") else 0.0, derived_from=["sector_dna"]),
        "future_opportunities": _f(UNKNOWN, source="unavailable", collector=collector),
    }
    return module_block("products", fields, source="company_analysis+sector_dna", collector=collector, confidence=0.55)


def produce_segments(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.segments"
    seed = (ctx.get("seed") or {}).get("segments")
    if seed:
        fields = _seed_fields(seed, SEGMENT_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("segments", fields, source="institutional_seed", collector=collector, confidence=0.95)
    fields = _unknown_fields(SEGMENT_KEYS, collector=collector)
    # Soft: single operating segment prior from sector display name only
    dna = ctx.get("dna") or {}
    if dna.get("display_name"):
        fields["operating_segments"] = _f(
            [dna["display_name"]],
            source="institutional_sector_prior",
            collector=collector,
            confidence=0.4,
            derived_from=["sector_dna"],
        )
        fields["business_segments"] = fields["operating_segments"]
    return module_block("segments", fields, source="institutional_sector_prior", collector=collector, confidence=0.4)


def produce_customers(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.customers"
    seed = (ctx.get("seed") or {}).get("customers")
    if seed:
        fields = _seed_fields(seed, CUSTOMER_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("customers", fields, source="institutional_seed", collector=collector, confidence=0.95)

    biz = ctx.get("ticker_business") or {}
    customers = biz.get("customers")
    geography = biz.get("geography")
    fields = _unknown_fields(CUSTOMER_KEYS, collector=collector)
    if customers:
        fields["customer_categories"] = _f(
            customers.split(", ") if isinstance(customers, str) else customers,
            source="company_analysis",
            collector=collector,
            confidence=0.75,
            derived_from=["ticker_business"],
        )
    if geography:
        fields["geographic_mix"] = _f(
            geography,
            source="company_analysis",
            collector=collector,
            confidence=0.75,
            derived_from=["ticker_business"],
        )
    sector = ctx.get("sector")
    if sector == "it_services":
        fields["exports"] = _f(True, source="institutional_sector_prior", collector=collector, confidence=0.55, derived_from=["sector_map"])
        fields["enterprise"] = _f(True, source="institutional_sector_prior", collector=collector, confidence=0.55, derived_from=["sector_map"])
        fields["retail"] = _f(False, source="institutional_sector_prior", collector=collector, confidence=0.5, derived_from=["sector_map"])
    elif sector in {"banks", "fmcg", "retail"}:
        fields["domestic_note"] = _f("Domestic-oriented sector prior", source="institutional_sector_prior", collector=collector, confidence=0.4, derived_from=["sector_map"])
        fields["exports"] = _f(False, source="institutional_sector_prior", collector=collector, confidence=0.5, derived_from=["sector_map"])
        fields["retail"] = _f(True, source="institutional_sector_prior", collector=collector, confidence=0.5, derived_from=["sector_map"])
    return module_block("customers", fields, source="company_analysis+sector_prior", collector=collector, confidence=0.5)


def produce_management(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.management"
    seed = (ctx.get("seed") or {}).get("management")
    if seed:
        fields = _seed_fields(seed, MGMT_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("management", fields, source="institutional_seed", collector=collector, confidence=0.95)

    pack = ctx.get("management_pack") or {}
    fields = _unknown_fields(MGMT_KEYS, collector=collector)
    execs = pack.get("executives") or []
    role_map = {"CEO": "ceo", "CFO": "cfo", "Chairman": "chairperson", "Chairperson": "chairperson"}
    for ex in execs:
        role = str(ex.get("role") or "")
        name = ex.get("name")
        key = role_map.get(role)
        if key and name:
            fields[key] = _f(name, source="management_intelligence", collector=collector, confidence=0.85, derived_from=["management_profiles"])
    if pack.get("board"):
        fields["independent_directors"] = _f(
            pack["board"].get("independence") or "Present",
            source="management_intelligence",
            collector=collector,
            confidence=0.7,
            derived_from=["management_profiles"],
        )
        fields["management_history"] = _f(
            pack["board"].get("notes") or UNKNOWN,
            source="management_intelligence",
            collector=collector,
            confidence=0.65,
            derived_from=["management_profiles"],
        )
    return module_block("management", fields, source="management_intelligence" if pack else "unavailable", collector=collector, confidence=0.7 if pack else 0.2)


def produce_ownership(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.ownership"
    seed = (ctx.get("seed") or {}).get("ownership")
    if seed:
        fields = _seed_fields(seed, OWN_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("ownership", fields, source="institutional_seed", collector=collector, confidence=0.95)
    # Never fabricate shareholding percentages
    fields = _unknown_fields(OWN_KEYS, collector=collector)
    return module_block("ownership", fields, source="unavailable", collector=collector, confidence=0.1)


def produce_capital_allocation(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.capital_allocation"
    seed = (ctx.get("seed") or {}).get("capital_allocation")
    if seed:
        fields = _seed_fields(seed, CAP_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("capital_allocation", fields, source="institutional_seed", collector=collector, confidence=0.95)
    fields = _unknown_fields(CAP_KEYS, collector=collector)
    return module_block("capital_allocation", fields, source="unavailable", collector=collector, confidence=0.1)


def produce_competition(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.competition"
    seed = (ctx.get("seed") or {}).get("competitive")
    if seed:
        fields = _seed_fields(seed, COMP_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("competition", fields, source="institutional_seed", collector=collector, confidence=0.95)

    peers = ctx.get("warehouse_peers") or ctx.get("ticker_peers") or ctx.get("sector_peers") or []
    dna = ctx.get("dna") or {}
    source = "institutional_warehouse" if ctx.get("warehouse_peers") else ("company_analysis" if ctx.get("ticker_peers") else ("nifty500_sector_peers" if peers else "unavailable"))
    fields = {
        "primary_competitors": _f(peers or UNKNOWN, source=source, collector=collector, confidence=0.7 if peers else 0.0, derived_from=["ticker_peers", "sector_peers"]),
        "market_position": _f(UNKNOWN, source="unavailable", collector=collector),
        "industry_rank": _f(UNKNOWN, source="unavailable", collector=collector),
        "competitive_advantages": _f(UNKNOWN, source="unavailable", collector=collector),
        "competitive_risks": _f(list(dna.get("historical_characteristics") or [])[:2] or UNKNOWN, source="institutional_sector_prior" if dna else "unavailable", collector=collector, confidence=0.4 if dna else 0.0, derived_from=["sector_dna"]),
        "industry_leadership": _f(dna.get("competitive_structure") or UNKNOWN, source="institutional_sector_prior" if dna else "unavailable", collector=collector, confidence=0.45 if dna else 0.0, derived_from=["sector_dna"]),
    }
    return module_block("competition", fields, source=source, collector=collector, confidence=0.55 if peers else 0.3)


def produce_business_quality(ctx: dict[str, Any]) -> dict[str, Any]:
    """Summarise from existing evidence only — DO NOT create new reasoning."""
    collector = "ici.collectors.business_quality"
    kf = ctx.get("kf_company") or {}
    composite = kf.get("composite") or kf.get("metrics") or {}
    # Soft-read only; if absent → UNKNOWN
    def _from_kf(key: str, alts: list[str] | None = None) -> Any:
        for k in [key, *(alts or [])]:
            if k in composite and composite[k] is not None:
                return composite[k]
            if k in kf and kf[k] is not None:
                return kf[k]
        return UNKNOWN

    fields = {
        "capital_allocation": _f(_from_kf("capital_allocation_quality", ["capital_allocation"]), source="knowledge_factory" if kf else "unavailable", collector=collector, confidence=0.5 if kf else 0.0, derived_from=["kf_company"]),
        "growth_quality": _f(_from_kf("growth_quality", ["growth"]), source="knowledge_factory" if kf else "unavailable", collector=collector, confidence=0.5 if kf else 0.0, derived_from=["kf_company"]),
        "cash_conversion": _f(_from_kf("cash_conversion", ["fcf_quality"]), source="knowledge_factory" if kf else "unavailable", collector=collector, confidence=0.5 if kf else 0.0, derived_from=["kf_company"]),
        "margin_stability": _f(_from_kf("margin_stability", ["margins"]), source="knowledge_factory" if kf else "unavailable", collector=collector, confidence=0.5 if kf else 0.0, derived_from=["kf_company"]),
        "roic_trend": _f(_from_kf("roic_trend", ["roic"]), source="knowledge_factory" if kf else "unavailable", collector=collector, confidence=0.5 if kf else 0.0, derived_from=["kf_company"]),
        "business_durability": _f(_from_kf("business_durability", ["quality_score"]), source="knowledge_factory" if kf else "unavailable", collector=collector, confidence=0.5 if kf else 0.0, derived_from=["kf_company"]),
    }
    # Explicit note: no new reasoning engine
    return {
        **module_block("business_quality", fields, source="existing_evidence_soft_read", collector=collector, confidence=0.4 if kf else 0.1),
        "reasoning_created": False,
        "note": "Summary of existing KF evidence only; no new reasoning.",
    }


def produce_business_risk(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.business_risk"
    seed = (ctx.get("seed") or {}).get("risks")
    if seed:
        fields = _seed_fields(seed, RISK_KEYS, source="institutional_seed", collector=collector, confidence=0.95)
        return module_block("business_risk", fields, source="institutional_seed", collector=collector, confidence=0.95)

    dna = ctx.get("dna") or {}
    if not dna:
        return module_block("business_risk", _unknown_fields(RISK_KEYS, collector=collector), source="unavailable", collector=collector, confidence=0.1)

    def _sens(key: str) -> Any:
        v = dna.get(key)
        if v is None:
            return UNKNOWN
        if isinstance(v, (int, float)):
            if abs(v) >= 2:
                return "High"
            if abs(v) == 1:
                return "Moderate"
            return "Low"
        return str(v)

    fields = {
        "commodity_risk": _f(_sens("commodity_sensitivity"), source="institutional_sector_prior", collector=collector, confidence=0.5, derived_from=["sector_dna"]),
        "fx_risk": _f(_sens("fx_sensitivity"), source="institutional_sector_prior", collector=collector, confidence=0.5, derived_from=["sector_dna"]),
        "regulatory_risk": _f(_sens("regulatory_sensitivity"), source="institutional_sector_prior", collector=collector, confidence=0.5, derived_from=["sector_dna"]),
        "technology_risk": _f(dna.get("technology_disruption_risk") or UNKNOWN, source="institutional_sector_prior", collector=collector, confidence=0.5, derived_from=["sector_dna"]),
        "customer_risk": _f(UNKNOWN, source="unavailable", collector=collector),
        "supplier_risk": _f(UNKNOWN, source="unavailable", collector=collector),
        "execution_risk": _f(UNKNOWN, source="unavailable", collector=collector),
        "litigation": _f(UNKNOWN, source="unavailable", collector=collector),
        "environmental_risk": _f(UNKNOWN, source="unavailable", collector=collector),
    }
    return module_block("business_risk", fields, source="institutional_sector_prior", collector=collector, confidence=0.45)


def produce_timeline(ctx: dict[str, Any]) -> dict[str, Any]:
    collector = "ici.collectors.timeline"
    seed_events = (ctx.get("seed") or {}).get("timeline") or []
    kf = ctx.get("kf_company") or {}
    kf_events = list((kf.get("timeline") or kf.get("events") or []))
    events = []
    for e in seed_events:
        events.append({
            **e,
            "provenance": {
                "source": e.get("source") or "institutional_seed",
                "collector": collector,
                "confidence": 0.9,
                "fabricated": False,
            },
        })
    for e in kf_events:
        if isinstance(e, dict):
            events.append({
                "date": e.get("date") or e.get("as_of") or UNKNOWN,
                "event_type": e.get("event_type") or e.get("type") or "event",
                "title": e.get("title") or e.get("name") or UNKNOWN,
                "source": "knowledge_factory",
                "provenance": {
                    "source": "knowledge_factory",
                    "collector": collector,
                    "confidence": 0.6,
                    "fabricated": False,
                },
            })
    # Always include a discovered event so timeline module exists (Level 6 path)
    if not events:
        events = [{
            "date": UNKNOWN,
            "event_type": "discovered",
            "title": f"{ctx['ticker']} present in Nifty 500 universe registry",
            "source": "nifty500_universe",
            "provenance": {
                "source": "nifty500_universe",
                "collector": collector,
                "confidence": 0.5,
                "fabricated": False,
            },
        }]
    return {
        "module": "timeline",
        "events": events,
        "fields": {
            "event_count": field(len(events), source="compiled", collector=collector, confidence=1.0, derived_from=["timeline"]),
            "ipo": field(
                next((e for e in events if str(e.get("event_type")) == "ipo"), UNKNOWN),
                source="timeline",
                collector=collector,
                confidence=0.8,
            ),
            "corporate_actions": field(
                [e for e in events if str(e.get("event_type")) in {"acquisition", "demerger", "bonus", "split", "rights", "corporate_action"}],
                source="timeline",
                collector=collector,
                confidence=0.7,
            ),
            "leadership_changes": field(
                [e for e in events if str(e.get("event_type")) in {"leadership", "appointment", "resignation"}],
                source="timeline",
                collector=collector,
                confidence=0.7,
            ),
        },
        "provenance": {
            "source": "institutional_seed+knowledge_factory" if seed_events else "nifty500_universe",
            "collector": collector,
            "confidence": 0.85 if seed_events else 0.4,
            "fabricated": False,
        },
        "fabricated": False,
    }


def produce_knowledge_links(ctx: dict[str, Any]) -> dict[str, Any]:
    """Reference existing knowledge — do NOT duplicate."""
    collector = "ici.collectors.knowledge_links"
    t = ctx["ticker"]
    sector = ctx.get("sector") or UNKNOWN
    links = {
        "company": t,
        "sector_dna": f"knowledge_factory.sector_intelligence.dna:{sector}" if sector != UNKNOWN else UNKNOWN,
        "industry_intelligence": f"knowledge_factory.sector_intelligence.object:{sector}" if sector != UNKNOWN else UNKNOWN,
        "macro_intelligence": "knowledge_factory.macro_intelligence",
        "historical_depth": f"knowledge_factory.historical_depth.company:{t}",
        "evidence_packs": f"knowledge_factory.company:{t}",
        "portfolio_intelligence": "institutional_reasoning.ipi",
        "decision_quality": "decision_quality",
        "universe_intelligence": f"universe_intelligence.company:{t}",
        "management_intelligence": f"management_intelligence.profiles:{t}",
        "corporate_events": f"knowledge_factory.corporate_events.timeline:{t}",
    }
    fields = {
        k: _f(v, source="knowledge_reference", collector=collector, confidence=0.9 if v != UNKNOWN else 0.0, derived_from=["soft_link"])
        for k, v in links.items()
    }
    return {
        **module_block("knowledge_links", fields, source="knowledge_reference", collector=collector, confidence=0.9),
        "duplicated_data": False,
        "note": "References only — no data duplication.",
    }


def produce_all_modules(ctx: dict[str, Any]) -> dict[str, Any]:
    return {
        "identity": produce_identity(ctx),
        "business_model": produce_business_model(ctx),
        "products": produce_products(ctx),
        "segments": produce_segments(ctx),
        "customers": produce_customers(ctx),
        "management": produce_management(ctx),
        "ownership": produce_ownership(ctx),
        "capital_allocation": produce_capital_allocation(ctx),
        "competition": produce_competition(ctx),
        "business_quality": produce_business_quality(ctx),
        "business_risk": produce_business_risk(ctx),
        "timeline": produce_timeline(ctx),
        "knowledge_links": produce_knowledge_links(ctx),
    }
