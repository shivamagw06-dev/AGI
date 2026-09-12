"""Produce IIVI modules from soft context — never fabricate."""

from __future__ import annotations

from typing import Any

from knowledge_factory.industry_intelligence.provenance import field, provenance
from knowledge_factory.industry_intelligence.schema import UNKNOWN


def _block(name: str, payload: Any, *, source: str, collector: str, confidence: float) -> dict[str, Any]:
    return {
        "module": name,
        "data": payload,
        "provenance": provenance(source=source, collector=collector, confidence=confidence, derived_from=[name]),
        "fabricated": False,
    }


def produce_industry_modules(ctx: dict[str, Any]) -> dict[str, Any]:
    iid = ctx["industry_id"]
    meta = ctx.get("meta") or {}
    dna = ctx.get("dna") or {}
    pb = ctx.get("playbook") or {}
    members = ctx.get("members") or []
    collector = "iivi.collectors.soft"

    has_pb = bool(pb)
    src = "institutional_industry_playbook" if has_pb else "institutional_sector_prior"
    conf = 0.9 if has_pb else 0.55

    identity = {
        "industry_name": field(meta.get("name") or iid, source="industry_registry", collector=collector, confidence=0.95),
        "description": field(pb.get("description") or dna.get("business_model") or UNKNOWN, source=src, collector=collector, confidence=conf),
        "sector": field(meta.get("sector") or dna.get("sector") or UNKNOWN, source="industry_registry", collector=collector, confidence=0.9),
        "sub_industry": field(meta.get("sub_industry") or UNKNOWN, source="industry_registry", collector=collector, confidence=0.85),
        "lifecycle": field(meta.get("lifecycle") or dna.get("industry_maturity") or UNKNOWN, source=src, collector=collector, confidence=conf),
        "historical_evolution": field(UNKNOWN if not pb else (pb.get("cycles") or {}).get("drivers"), source=src, collector=collector, confidence=0.5 if pb else 0.0),
        "industry_size": field(UNKNOWN, source="unavailable", collector=collector),
        "growth_drivers": field(dna.get("growth_drivers") or (pb.get("economics") or {}).get("demand_drivers") or UNKNOWN, source=src, collector=collector, confidence=conf),
        "maturity": field(dna.get("industry_maturity") or meta.get("lifecycle") or UNKNOWN, source=src, collector=collector, confidence=conf),
        "fragmentation": field((pb.get("competition") or {}).get("porters") or dna.get("competitive_structure") or UNKNOWN, source=src, collector=collector, confidence=0.5),
        "market_structure": field(dna.get("competitive_structure") or UNKNOWN, source="institutional_sector_prior", collector=collector, confidence=0.55),
        "institutional_coverage": field(len(members), source="nifty500_mapping", collector=collector, confidence=0.9, derived_from=["company_map"]),
        "members": field(members, source="nifty500_mapping", collector=collector, confidence=0.9),
    }

    bm = pb.get("business_model") or {
        "how_money_earned": dna.get("business_model") or UNKNOWN,
        "capital_intensity": dna.get("capital_intensity") or UNKNOWN,
        "operating_leverage": dna.get("operating_leverage") or UNKNOWN,
        "pricing": UNKNOWN,
        "revenue_sources": UNKNOWN,
        "cost_structure": UNKNOWN,
        "fixed_costs": UNKNOWN,
        "variable_costs": UNKNOWN,
        "working_capital": UNKNOWN,
        "margins": dna.get("margin_profile") or UNKNOWN,
        "customer_model": UNKNOWN,
        "supplier_model": UNKNOWN,
    }

    vc = pb.get("value_chain") or [
        {"stage": "upstream", "participants": [UNKNOWN]},
        {"stage": "core", "participants": [meta.get("name") or iid]},
        {"stage": "downstream", "participants": [UNKNOWN]},
    ]
    # Attach listed members to core stage when known
    if members and isinstance(vc, list) and vc:
        vc = list(vc)
        vc.append({"stage": "listed_companies", "participants": members[:25]})

    sc = pb.get("supply_chain") or {
        "critical_inputs": [UNKNOWN],
        "commodities": [],
        "imports": UNKNOWN,
        "exports": UNKNOWN,
        "dependencies": [],
        "bottlenecks": [UNKNOWN],
    }

    econ = pb.get("economics") or {
        "growth": UNKNOWN,
        "margins": dna.get("margin_profile") or UNKNOWN,
        "roic": UNKNOWN,
        "capital_cycle": UNKNOWN,
        "demand_drivers": dna.get("growth_drivers") or UNKNOWN,
        "pricing_power": UNKNOWN,
        "typical_multiples": dna.get("preferred_frameworks") or UNKNOWN,
        "cash_conversion": UNKNOWN,
    }

    acct = pb.get("accounting") or {
        "core_metrics": [UNKNOWN],
        "playbook": "Sector-typical metrics pending industry-specific playbook",
    }
    val = pb.get("valuation") or {
        "preferred_framework": (dna.get("preferred_frameworks") or [UNKNOWN])[0] if dna.get("preferred_frameworks") else UNKNOWN,
        "preferred_multiple": UNKNOWN,
        "dcf_applicability": UNKNOWN,
        "apply": dna.get("preferred_frameworks") or [],
        "not_apply": dna.get("forbidden_frameworks") or [],
    }
    kpis = pb.get("kpis") or {
        "core": dna.get("valuation_drivers") or [UNKNOWN],
        "leading": [UNKNOWN],
        "lagging": [UNKNOWN],
        "quality": [UNKNOWN],
        "risk": dna.get("common_accounting_risks") or [UNKNOWN],
        "growth": dna.get("growth_drivers") or [UNKNOWN],
        "efficiency": [UNKNOWN],
        "capital_allocation": [UNKNOWN],
    }
    comp = pb.get("competition") or {
        "porters": {},
        "entry_barriers": UNKNOWN,
        "switching_costs": UNKNOWN,
        "moat": UNKNOWN,
        "market_share": UNKNOWN,
        "fragmentation": dna.get("competitive_structure") or UNKNOWN,
    }
    macro = pb.get("macro") or [
        {
            "factor": "interest_rates",
            "direction": str(dna.get("interest_rate_sensitivity", UNKNOWN)),
            "strength": "from_sector_dna",
            "confidence": 0.5,
        },
        {
            "factor": "inflation",
            "direction": str(dna.get("inflation_sensitivity", UNKNOWN)),
            "strength": "from_sector_dna",
            "confidence": 0.5,
        },
        {
            "factor": "fx",
            "direction": str(dna.get("fx_sensitivity", UNKNOWN)),
            "strength": "from_sector_dna",
            "confidence": 0.5,
        },
    ]
    gov = pb.get("government") or ctx.get("government_domains") or [UNKNOWN]
    # Soft-link references — no duplication
    gov_links = {
        "domains": gov if isinstance(gov, list) else [gov],
        "references": [
            "knowledge_factory.government_intelligence",
            *[f"government.domain:{d}" for d in (ctx.get("government_domains") or [])],
        ],
        "duplicated_data": False,
    }
    cycles = pb.get("cycles") or {
        "phases": ["expansion", "peak", "slowdown", "recovery"],
        "drivers": dna.get("historical_characteristics") or [UNKNOWN],
        "typical_duration": UNKNOWN,
        "typical_valuation": UNKNOWN,
    }
    playbook = pb.get("playbook") or {
        "how_to_study": ["Sector DNA priors", "Company filings"],
        "warning_signs": [UNKNOWN],
        "best_metrics": kpis.get("core") if isinstance(kpis, dict) else [UNKNOWN],
        "best_frameworks": val.get("apply") if isinstance(val, dict) else [],
        "common_mistakes": [UNKNOWN],
        "historical_lessons": dna.get("historical_characteristics") or [UNKNOWN],
        "institutional_best_practices": ["Use industry accounting language", "Respect forbidden frameworks"],
    }

    graph = {
        "industry": iid,
        "companies": [f"company:{t}" for t in members],
        "suppliers": "value_chain.upstream",
        "customers": "value_chain.downstream",
        "commodities": sc.get("commodities") if isinstance(sc, dict) else [],
        "government": "knowledge_factory.government_intelligence",
        "macro": "knowledge_factory.macro_intelligence",
        "corporate_events": "knowledge_factory.corporate_events",
        "historical_replay": "knowledge_factory.historical_depth",
        "evidence_packs": "knowledge_factory",
        "portfolio": "institutional_reasoning.ipi",
        "decision_quality": "decision_quality",
        "sector_intelligence": f"knowledge_factory.sector_intelligence:{meta.get('sector')}",
        "duplicated_data": False,
        "future_economic_network_graph": "declared_later_sprint",
    }

    return {
        "identity": _block("identity", identity, source="industry_registry", collector=collector, confidence=0.9),
        "business_model": _block("business_model", bm, source=src, collector=collector, confidence=conf),
        "value_chain": _block("value_chain", vc, source=src, collector=collector, confidence=conf if has_pb else 0.4),
        "supply_chain": _block("supply_chain", sc, source=src, collector=collector, confidence=conf if has_pb else 0.4),
        "economics": _block("economics", econ, source=src, collector=collector, confidence=conf),
        "accounting": _block("accounting", acct, source=src, collector=collector, confidence=conf if has_pb else 0.45),
        "valuation": _block("valuation", val, source=src, collector=collector, confidence=conf),
        "kpis": _block("kpis", kpis, source=src, collector=collector, confidence=conf),
        "competition": _block("competition", comp, source=src, collector=collector, confidence=conf if has_pb else 0.45),
        "macro": _block("macro", macro, source="institutional_sector_prior+playbook", collector=collector, confidence=0.6),
        "government": _block("government", gov_links, source="government_intelligence_soft_link", collector=collector, confidence=0.7),
        "cycles": _block("cycles", cycles, source=src, collector=collector, confidence=conf if has_pb else 0.45),
        "playbook": _block("playbook", playbook, source=src, collector=collector, confidence=conf if has_pb else 0.45),
        "knowledge_graph": _block("knowledge_graph", graph, source="knowledge_reference", collector=collector, confidence=0.85),
    }
