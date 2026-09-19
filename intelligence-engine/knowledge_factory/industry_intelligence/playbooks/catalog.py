"""Institutional industry playbooks — accounting, valuation, KPIs, cycles, VC.

Deep curated where known; otherwise soft Sector DNA priors with UNKNOWN gaps.
Never fabricate company-specific claims.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.industry_intelligence.schema import UNKNOWN

DEEP_INDUSTRIES: tuple[str, ...] = (
    "it_services",
    "private_banks",
    "psu_banks",
    "nbfc",
    "life_insurance",
    "cement",
    "steel",
    "hospitals",
    "generics",
    "fmcg",
    "passenger_vehicles",
    "telecom",
    "specialty_chem",
    "power_generation",
    "renewables",
    "real_estate",
    "retail",
    "consumer_internet",
)

_PLAYBOOKS: dict[str, dict[str, Any]] = {
    "it_services": {
        "description": "Global digital services & consulting delivered via offshore/onshore networks.",
        "business_model": {
            "how_money_earned": "Time-and-material / fixed-price / managed services contracts",
            "pricing": "Effort-based and outcome-linked",
            "revenue_sources": ["Application services", "Digital", "Consulting", "BPO/ops"],
            "cost_structure": "People cost dominant",
            "fixed_costs": "Campus / delivery capacity",
            "variable_costs": "Contractors, travel, subcontract",
            "working_capital": "Receivables / unbilled revenue",
            "capital_intensity": "Low",
            "operating_leverage": "Moderate-High",
            "margins": "High-teens to mid-twenties EBIT typical for majors",
            "customer_model": "Global enterprise accounts",
            "supplier_model": "Human capital / talent market",
        },
        "value_chain": [
            {"stage": "talent", "participants": ["Campus hiring", "Lateral talent"]},
            {"stage": "delivery", "participants": ["Offshore centres", "Onsite teams"]},
            {"stage": "client", "participants": ["BFSI", "Retail", "Manufacturing clients"]},
            {"stage": "platforms", "participants": ["Cloud hyperscalers", "AI tools"]},
        ],
        "supply_chain": {
            "critical_inputs": ["Skilled engineers", "Visa access", "Cloud capacity"],
            "commodities": [],
            "imports": "Onsite deployment / travel",
            "exports": "Services exports (USD)",
            "dependencies": ["US/EU IT budgets", "INR cost base"],
            "bottlenecks": ["Attrition", "Skill mix for AI/cloud"],
        },
        "economics": {
            "growth": "Large deal TCV + digital mix",
            "margins": "Utilisation / pyramid / pricing",
            "roic": "High (asset-light)",
            "capital_cycle": "Hiring cycle / deal cycle",
            "demand_drivers": ["Digital transformation", "Cost takeout", "AI adoption"],
            "pricing_power": "Moderate; competitive",
            "typical_multiples": ["PE", "EV/EBITDA"],
            "cash_conversion": "Strong FCF conversion",
        },
        "accounting": {
            "core_metrics": ["Utilisation", "Attrition", "Digital Mix", "Offshore Mix", "TCV", "DSO"],
            "playbook": "Track utilisation, attrition, deal wins, and digital mix; revenue recognition on milestones matters.",
        },
        "valuation": {
            "preferred_framework": "pe",
            "preferred_multiple": "PE / EV-EBITDA",
            "dcf_applicability": "Stable mature cash flows — applicable with care",
            "apply": ["PE", "EV/EBITDA", "DCF_stable"],
            "not_apply": ["Book value primary", "NAV"],
        },
        "kpis": {
            "core": ["Revenue growth", "EBIT margin", "Utilisation", "Attrition"],
            "leading": ["Deal TCV", "Pipeline", "Hiring"],
            "lagging": ["Revenue", "Margins"],
            "quality": ["Client concentration", "Digital mix"],
            "risk": ["FX", "Visa", "Attrition"],
        },
        "competition": {
            "porters": {"rivalry": "high", "buyer_power": "high", "new_entrants": "moderate", "substitutes": "AI/automation", "supplier_power": "talent"},
            "entry_barriers": "Scale, brand, delivery network",
            "switching_costs": "Moderate-High for large accounts",
            "moat": "Scale + relationships + delivery",
        },
        "macro": [
            {"factor": "fx_usd_inr", "direction": "positive_for_inr_depreciation", "strength": "high", "confidence": 0.85},
            {"factor": "us_gdp_it_spend", "direction": "positive", "strength": "high", "confidence": 0.8},
            {"factor": "interest_rates", "direction": "mixed", "strength": "low", "confidence": 0.6},
        ],
        "government": ["sebi_lodr_listed", "export_services_policy", "data_privacy"],
        "cycles": {
            "phases": ["expansion", "peak", "slowdown", "recovery"],
            "drivers": ["Global IT budgets", "USD cycles", "Hiring freezes"],
            "typical_duration": "2-4 years discretionary spend cycles",
            "typical_valuation": "Rerates ahead of earnings in tech upcycles",
        },
        "playbook": {
            "how_to_study": ["Deal pipeline", "Margin walk", "Vertical mix", "FX sensitivity"],
            "warning_signs": ["Utilisation collapse", "Large client loss", "Wage spike without pricing"],
            "best_metrics": ["Utilisation", "Digital mix", "TCV", "FCF"],
            "best_frameworks": ["PE", "EV/EBITDA"],
            "common_mistakes": ["Ignoring FX", "Extrapolating peak hiring"],
            "historical_lessons": ["GFC freeze", "COVID remote acceleration", "AI spend cycle"],
        },
    },
    "private_banks": {
        "description": "Deposit-funded private sector banks; NIM + fees + credit quality franchise.",
        "business_model": {
            "how_money_earned": "Net interest income + fee income",
            "pricing": "Lending spreads vs deposit costs",
            "revenue_sources": ["NII", "Fees", "Treasury"],
            "cost_structure": "Interest expense + opex + credit costs",
            "capital_intensity": "High (regulatory capital)",
            "operating_leverage": "Moderate",
            "margins": "NIM-driven",
            "customer_model": "Retail + wholesale",
            "supplier_model": "Depositors / wholesale liabilities",
        },
        "value_chain": [
            {"stage": "liabilities", "participants": ["Retail deposits", "CASA", "Wholesale"]},
            {"stage": "assets", "participants": ["Retail loans", "Corporate credit", "Cards"]},
            {"stage": "distribution", "participants": ["Branches", "Digital", "BC network"]},
            {"stage": "risk", "participants": ["Credit underwriting", "Collections"]},
        ],
        "supply_chain": {
            "critical_inputs": ["Deposits", "Capital", "Credit data"],
            "commodities": [],
            "dependencies": ["RBI policy", "Credit cycle"],
            "bottlenecks": ["Liability franchise", "Capital adequacy"],
        },
        "economics": {
            "growth": "Loan growth vs deposit growth",
            "margins": "NIM",
            "roic": "ROE / ROA primary",
            "capital_cycle": "Credit cycle",
            "demand_drivers": ["Credit demand", "GDP", "Rates"],
            "pricing_power": "Franchise-dependent",
            "typical_multiples": ["PB", "ROE"],
            "cash_conversion": "N/A classic FCF — deposit-funded",
        },
        "accounting": {
            "core_metrics": ["NIM", "CASA", "GNPA", "NNPA", "PCR", "CAR/CET1", "Credit Cost", "CD ratio"],
            "playbook": "Asset quality and liability mix dominate; avoid traditional DCF as primary.",
        },
        "valuation": {
            "preferred_framework": "residual_income_pb",
            "preferred_multiple": "PB vs ROE",
            "dcf_applicability": "Not preferred as primary",
            "apply": ["PB", "ROE", "Residual income"],
            "not_apply": ["Traditional DCF primary", "EV/EBITDA"],
        },
        "kpis": {
            "core": ["NIM", "GNPA", "CET1", "Loan growth"],
            "leading": ["Deposit growth", "SMA", "Unsecured mix"],
            "lagging": ["Credit cost", "ROA"],
            "risk": ["Slippages", "Concentration", "Liquidity"],
        },
        "competition": {
            "porters": {"rivalry": "high", "buyer_power": "moderate", "new_entrants": "low_regulated", "substitutes": "NBFC/fintech", "supplier_power": "depositors"},
            "entry_barriers": "License + capital + trust",
            "moat": "Liability franchise + underwriting culture",
        },
        "macro": [
            {"factor": "interest_rates", "direction": "NIM_sensitive", "strength": "high", "confidence": 0.9},
            {"factor": "gdp_credit", "direction": "positive", "strength": "high", "confidence": 0.85},
            {"factor": "inflation", "direction": "mixed", "strength": "moderate", "confidence": 0.7},
        ],
        "government": ["rbi_monetary", "rbi_banking_reg", "budget_financials"],
        "cycles": {
            "phases": ["expansion", "peak", "asset_quality_stress", "recovery"],
            "drivers": ["Credit cycle", "Rates", "Regulatory capital"],
            "typical_duration": "Multi-year credit cycles",
            "typical_valuation": "PB tracks ROE",
        },
        "playbook": {
            "how_to_study": ["Liability franchise", "Asset mix", "Credit cost walk", "Capital"],
            "warning_signs": ["Unsecured spike", "SMA rise", "Deposit market share loss"],
            "best_metrics": ["NIM", "GNPA", "CET1", "CASA"],
            "best_frameworks": ["PB", "ROE"],
            "common_mistakes": ["Using EV/EBITDA", "Ignoring liability quality"],
            "historical_lessons": ["GFC", "COVID moratoriums", "HDFC merger scale shift"],
        },
    },
    "cement": {
        "description": "Regional oligopoly; realisation, fuel, freight, and capacity utilisation drive economics.",
        "business_model": {
            "how_money_earned": "Cement / RMX sales",
            "pricing": "Regional realisations",
            "cost_structure": "Fuel + power + freight + limestone",
            "capital_intensity": "High",
            "operating_leverage": "High",
            "margins": "EBITDA/t sensitive to fuel & freight",
            "customer_model": "Trade + institutional",
            "supplier_model": "Limestone, coal/petcoke, logistics",
        },
        "value_chain": [
            {"stage": "raw_materials", "participants": ["Limestone mines", "Coal/petcoke"]},
            {"stage": "manufacturing", "participants": ["Kilns", "Grinding units"]},
            {"stage": "distribution", "participants": ["Dealers", "Bulk logistics"]},
            {"stage": "customer", "participants": ["Housing", "Infra"]},
        ],
        "supply_chain": {
            "critical_inputs": ["Limestone", "Fuel", "Freight"],
            "commodities": ["coal", "petcoke", "diesel"],
            "bottlenecks": ["Logistics", "Clinker capacity"],
        },
        "economics": {
            "growth": "Housing + infra demand",
            "margins": "Realisation − fuel − freight",
            "capital_cycle": "Capacity additions / consolidation",
            "typical_multiples": ["EV/EBITDA", "EV/t"],
            "cash_conversion": "Capex heavy in expansion",
        },
        "accounting": {
            "core_metrics": ["Realisation", "Fuel cost/t", "Freight/t", "Capacity utilisation", "EBITDA/t"],
            "playbook": "Per-tonne bridge is the institutional language.",
        },
        "valuation": {
            "preferred_framework": "ev_ebitda",
            "preferred_multiple": "EV/EBITDA / EV per tonne",
            "apply": ["EV/EBITDA", "Replacement cost"],
            "not_apply": ["PB primary for pure cement"],
        },
        "kpis": {
            "core": ["Volumes", "Realisation", "EBITDA/t", "Utilisation"],
            "leading": ["Housing starts", "Infra awards", "Fuel prices"],
            "risk": ["Fuel spike", "Freight", "Regional overcapacity"],
        },
        "competition": {
            "porters": {"rivalry": "high_regional", "buyer_power": "moderate", "new_entrants": "high_capex_barrier"},
            "entry_barriers": "Limestone + capex + logistics",
            "moat": "Regional cost position",
        },
        "macro": [
            {"factor": "housing", "direction": "positive", "strength": "high", "confidence": 0.85},
            {"factor": "oil_coal", "direction": "negative_for_margins", "strength": "high", "confidence": 0.85},
            {"factor": "infra_spending", "direction": "positive", "strength": "high", "confidence": 0.8},
        ],
        "government": ["budget_capex", "infra_policy", "environmental_rules"],
        "cycles": {
            "phases": ["expansion", "peak", "overcapacity", "recovery"],
            "drivers": ["Capacity cycle", "Demand", "Fuel"],
            "typical_duration": "3-5 year capacity cycles",
        },
        "playbook": {
            "how_to_study": ["Per-tonne P&L", "Regional pricing", "Capacity map"],
            "warning_signs": ["Price war", "Fuel spike without pricing"],
            "best_metrics": ["EBITDA/t", "Utilisation", "Realisation"],
            "best_frameworks": ["EV/EBITDA", "EV/t"],
            "common_mistakes": ["National average pricing blindness"],
            "historical_lessons": ["Consolidation eras", "Fuel shocks"],
        },
    },
    "steel": {
        "description": "Spread business; iron ore, coking coal, and capacity utilisation dominate.",
        "business_model": {
            "how_money_earned": "Steel product sales (HRC/CRC/longs)",
            "pricing": "Spread over raw materials",
            "capital_intensity": "Very High",
            "operating_leverage": "Very High",
            "customer_model": "Auto, construction, infra, exports",
            "supplier_model": "Iron ore, coking coal",
        },
        "value_chain": [
            {"stage": "raw_materials", "participants": ["Iron ore", "Coking coal"]},
            {"stage": "manufacturing", "participants": ["Blast furnace / DRI", "Mills"]},
            {"stage": "customer", "participants": ["Auto", "Construction", "Infra"]},
        ],
        "supply_chain": {
            "critical_inputs": ["Iron ore", "Coking coal"],
            "commodities": ["iron_ore", "coking_coal", "steel"],
            "imports": "Coking coal (often)",
            "bottlenecks": ["Coking coal", "Logistics"],
        },
        "economics": {
            "growth": "Domestic demand + exports",
            "margins": "Steel spread",
            "capital_cycle": "Capacity / China cycle linked",
            "typical_multiples": ["EV/EBITDA", "PB cycle"],
        },
        "accounting": {
            "core_metrics": ["Spread", "Capacity utilisation", "Iron ore cost", "Coal cost", "Debt/EBITDA"],
            "playbook": "Follow spreads and inventory; leverage amplifies cycle.",
        },
        "valuation": {
            "preferred_framework": "ev_ebitda_cycle",
            "preferred_multiple": "EV/EBITDA through cycle",
            "apply": ["EV/EBITDA", "Replacement cost"],
            "not_apply": ["Peak PE extrapolation"],
        },
        "kpis": {
            "core": ["Spread", "Utilisation", "Net debt"],
            "leading": ["China steel", "Iron ore", "Auto/infra demand"],
            "risk": ["Commodity shock", "Leverage"],
        },
        "competition": {
            "porters": {"rivalry": "high", "buyer_power": "moderate", "new_entrants": "very_high_capex"},
            "moat": "Integrated cost position",
        },
        "macro": [
            {"factor": "iron_ore", "direction": "cost", "strength": "high", "confidence": 0.9},
            {"factor": "coking_coal", "direction": "cost", "strength": "high", "confidence": 0.9},
            {"factor": "gdp_infra", "direction": "positive", "strength": "high", "confidence": 0.8},
        ],
        "government": ["trade_duties", "infra_budget", "environmental_rules"],
        "cycles": {
            "phases": ["boom", "peak", "slowdown", "recovery"],
            "drivers": ["Global steel cycle", "China", "Raw materials"],
            "typical_duration": "Multi-year commodity cycles",
        },
        "playbook": {
            "how_to_study": ["Spread bridge", "Balance sheet leverage", "Capacity"],
            "warning_signs": ["Inventory build", "Spread collapse", "Net debt spike"],
            "best_metrics": ["Spread", "Utilisation", "Net debt/EBITDA"],
            "best_frameworks": ["EV/EBITDA through-cycle"],
            "common_mistakes": ["Valuing on peak spreads"],
            "historical_lessons": ["China super-cycle", "COVID demand shock"],
        },
    },
    "hospitals": {
        "description": "Healthcare services; occupancy, ARPOB, and case mix drive unit economics.",
        "business_model": {
            "how_money_earned": "Inpatient / outpatient / procedures",
            "pricing": "ARPOB / procedure pricing",
            "capital_intensity": "High (beds, equipment)",
            "operating_leverage": "High once occupied",
            "customer_model": "Patients + insurers + government schemes",
        },
        "value_chain": [
            {"stage": "clinical", "participants": ["Doctors", "Nurses", "Equipment OEMs"]},
            {"stage": "facility", "participants": ["Hospitals", "ICUs"]},
            {"stage": "payers", "participants": ["Insurance", "Self-pay", "Govt schemes"]},
        ],
        "supply_chain": {
            "critical_inputs": ["Clinicians", "Devices", "Consumables"],
            "bottlenecks": ["Specialist talent", "Regulatory licenses"],
        },
        "economics": {
            "growth": "Bed additions + ARPOB + case mix",
            "margins": "Occupancy operating leverage",
            "typical_multiples": ["EV/EBITDA", "EV/bed"],
        },
        "accounting": {
            "core_metrics": ["ARPOB", "Occupancy", "ALOS", "Bed count", "Payor mix"],
            "playbook": "Unit economics per occupied bed; watch ALOS and payor mix.",
        },
        "valuation": {
            "preferred_framework": "ev_ebitda",
            "preferred_multiple": "EV/EBITDA / EV per bed",
            "apply": ["EV/EBITDA", "DCF for mature chains"],
            "not_apply": ["PB primary"],
        },
        "kpis": {
            "core": ["Occupancy", "ARPOB", "ALOS"],
            "leading": ["Doctor hiring", "New beds"],
            "risk": ["Regulatory", "Payor pressure"],
        },
        "competition": {
            "porters": {"rivalry": "regional", "buyer_power": "insurers_rising"},
            "entry_barriers": "Licenses + specialists + brand",
        },
        "macro": [
            {"factor": "consumption_healthcare", "direction": "positive", "strength": "moderate", "confidence": 0.75},
            {"factor": "insurance_penetration", "direction": "positive", "strength": "high", "confidence": 0.8},
        ],
        "government": ["health_regulation", "scheme_pricing", "gst_healthcare_context"],
        "cycles": {
            "phases": ["expansion", "stabilisation"],
            "drivers": ["Capex for beds", "Elective procedures"],
            "typical_duration": "Structural growth with elective cyclicality",
        },
        "playbook": {
            "how_to_study": ["ARPOB walk", "Occupancy", "New hospital ramp"],
            "warning_signs": ["Occupancy drop", "Payor mix shift adverse"],
            "best_metrics": ["ARPOB", "Occupancy", "ALOS"],
            "best_frameworks": ["EV/EBITDA"],
            "common_mistakes": ["Ignoring ramp-up losses on new beds"],
            "historical_lessons": ["COVID elective freeze then rebound"],
        },
    },
}

# Alias PSU banks to private bank structure with PSU-specific notes
_PLAYBOOKS["psu_banks"] = {
    **{k: v for k, v in _PLAYBOOKS["private_banks"].items() if k != "description"},
    "description": "Public sector banks; same accounting language as private banks with ownership/governance overlays.",
    "playbook": {
        **_PLAYBOOKS["private_banks"]["playbook"],
        "how_to_study": ["Asset quality", "Capital", "CASA", "Govt ownership constraints"],
        "common_mistakes": ["Ignoring PCR / recognition differences historically"],
    },
}

# Compact deep packs for remaining DEEP_INDUSTRIES
for _iid, _desc, _acct, _val, _gov in [
    ("nbfc", "Credit intermediaries without full deposit franchise; liability-sensitive.",
     ["AUM growth", "NIM/spreads", "Credit cost", "Leverage", "ALM"],
     ["PB", "ROE"], ["rbi_nbfc_reg", "interest_rates"]),
    ("life_insurance", "Long-duration liabilities + VNB / embedded value economics.",
     ["VNB", "VNB margin", "APE", "Persistency", "Solvency"],
     ["EV", "VNB multiple"], ["irdai_context", "tax_insurance"]),
    ("generics", "Formulation generics; US/India/EM mix; price erosion vs volumes.",
     ["US price erosion", "ANDA pipeline", "Gross margin", "R&D"],
     ["PE", "EV/EBITDA"], ["usfda_context", "drug_pricing"]),
    ("fmcg", "Brand + distribution; volume/value growth and gross margin.",
     ["Volume growth", "Value growth", "Gross margin", "A&P", "Distribution"],
     ["PE", "EV/EBITDA"], ["gst", "rural_schemes"]),
    ("passenger_vehicles", "OEM cyclical; volumes, mix, discounts, commodity costs.",
     ["Volumes", "ASP/mix", "Discounts", "Commodity costs", "Inventory"],
     ["PE", "EV/EBITDA"], ["plI_auto", "emission_norms"]),
    ("telecom", "Spectrum + network opex; ARPU and competitive intensity.",
     ["ARPU", "Subscribers", "Capex intensity", "Net debt"],
     ["EV/EBITDA", "SOTP"], ["trai_dot", "spectrum_policy"]),
    ("specialty_chem", "Niche chemistries; product mix and China+1 demand.",
     ["Gross margin", "Capacity", "Product mix", "RM costs"],
     ["PE", "EV/EBITDA"], ["trade_duties", "environmental"]),
    ("power_generation", "Regulated/merchant generation; PLF and fuel.",
     ["PLF", "Tariff", "Fuel cost", "Receivables"],
     ["PB", "DCF regulated"], ["power_policy", "renewables_transition"]),
    ("renewables", "Project IRR / CUF / PPA framework.",
     ["CUF", "PPA tariff", "Debt/equity", "Pipeline MW"],
     ["DCF", "EV/EBITDA"], ["renewables_policy", "pli_context"]),
    ("real_estate", "Pre-sales, collections, and project-level cash flows.",
     ["Pre-sales", "Collections", "Net debt", "Inventory"],
     ["NAV", "SOTP"], ["rera", "housing_policy"]),
    ("retail", "Same-store growth, margins, and inventory turns.",
     ["SSSG", "Gross margin", "Inventory days", "Store adds"],
     ["PE", "EV/EBITDA"], ["gst", "consumption"]),
    ("consumer_internet", "Platform unit economics; growth vs losses.",
     ["GMV", "Take rate", "Contribution margin", "MAU"],
     ["EV/Sales", "Growth"], ["it_rules", "competition_cci"]),
]:
    if _iid not in _PLAYBOOKS:
        _PLAYBOOKS[_iid] = {
            "description": _desc,
            "business_model": {
                "how_money_earned": _desc,
                "capital_intensity": UNKNOWN,
                "operating_leverage": UNKNOWN,
                "customer_model": UNKNOWN,
                "supplier_model": UNKNOWN,
            },
            "value_chain": [{"stage": "core", "participants": [_iid]}],
            "supply_chain": {"critical_inputs": [UNKNOWN], "commodities": [], "bottlenecks": [UNKNOWN]},
            "economics": {"growth": UNKNOWN, "margins": UNKNOWN, "typical_multiples": _val},
            "accounting": {"core_metrics": _acct, "playbook": f"Industry accounting focus: {', '.join(_acct)}"},
            "valuation": {"preferred_framework": _val[0], "preferred_multiple": _val[0], "apply": _val, "not_apply": []},
            "kpis": {"core": _acct[:4], "leading": _acct[:2], "lagging": _acct[-2:], "risk": []},
            "competition": {"porters": {}, "entry_barriers": UNKNOWN, "moat": UNKNOWN},
            "macro": [{"factor": "gdp", "direction": "positive", "strength": "moderate", "confidence": 0.6}],
            "government": _gov,
            "cycles": {"phases": ["expansion", "peak", "slowdown", "recovery"], "drivers": [UNKNOWN], "typical_duration": UNKNOWN},
            "playbook": {
                "how_to_study": _acct[:3],
                "warning_signs": [UNKNOWN],
                "best_metrics": _acct[:3],
                "best_frameworks": _val,
                "common_mistakes": [UNKNOWN],
                "historical_lessons": [UNKNOWN],
            },
        }


def get_playbook(industry_id: str) -> dict[str, Any] | None:
    return _PLAYBOOKS.get(str(industry_id or "").lower())
