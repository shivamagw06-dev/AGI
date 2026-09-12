"""Deterministic industry → value-driver / unit-econ / capital-intensity templates."""

from __future__ import annotations

from typing import Any

# Each industry template is institutional and fixed — no LLM.
INDUSTRY_TEMPLATES: dict[str, dict[str, Any]] = {
    "banks": {
        "value_drivers": ["NIM", "CASA", "Credit Cost", "Fee Income", "Operating Efficiency"],
        "unit_econ_chain": [
            "Interest / fee income",
            "Net interest income after funding cost",
            "Contribution after credit cost",
            "Operating profit after opex",
            "Free cash / capital generation after regulatory buffers",
        ],
        "capital_intensity": "Balance-sheet intensive — equity and deposits fund the loan book",
        "working_capital": "Working capital is the loan book and deposit franchise, not inventory",
        "operating_leverage": "High fixed franchise cost; incremental deposits/loans drop through when credit costs stay controlled",
        "pricing_model": "Spread (NIM) + fees; price is funding cost vs lending yield",
        "porter": {
            "rivalry": "High — product overlap, rate competition, brand fight for deposits",
            "entry_barriers": "High — licensing, capital, distribution, regulatory scrutiny",
            "supplier_power": "Medium — depositors and wholesale funders set funding cost",
            "customer_power": "Medium — retail sticky via CASA; wholesale more price-sensitive",
            "substitutes": "Medium — capital markets, NBFCs, fintech payments",
        },
        "concentration": "Oligopolistic at the top; long tail of smaller banks",
        "typical_moats": ["switching_costs", "distribution", "scale", "brand", "licensing"],
        "lifecycle_default": "mature",
    },
    "nbfc": {
        "value_drivers": ["Spread", "Asset Quality", "Cost of Funds", "Origination Yield", "Leverage"],
        "unit_econ_chain": [
            "Interest income on loans",
            "Net interest after borrowing cost",
            "Contribution after credit cost",
            "Operating profit after opex",
            "Free cash after growth in receivables",
        ],
        "capital_intensity": "High — growth consumes capital and wholesale funding",
        "working_capital": "Receivables-heavy; cash tied in loan book growth",
        "operating_leverage": "Moderate — fixed opex over growing AUM when credit stays clean",
        "pricing_model": "Risk-based lending spreads over cost of funds",
        "porter": {
            "rivalry": "High — banks and peers compete on yield and underwriting",
            "entry_barriers": "Medium-High — capital, funding access, regulation",
            "supplier_power": "High — wholesale funding markets",
            "customer_power": "Medium — rate-sensitive borrowers",
            "substitutes": "High — banks, fintech lenders, informal credit",
        },
        "concentration": "Fragmented with a few large national players",
        "typical_moats": ["distribution", "cost_leadership", "customer_lock_in"],
        "lifecycle_default": "growth",
    },
    "saas": {
        "value_drivers": ["Retention", "NRR", "CAC", "Gross Margin", "Payback Period"],
        "unit_econ_chain": [
            "Subscription / usage revenue",
            "Gross profit after hosting & support COGS",
            "Contribution after CAC amortized",
            "Operating profit after R&D/S&M",
            "Free cash flow after deferred revenue / WC",
        ],
        "capital_intensity": "Asset-light; growth spend is opex (S&M/R&D), not plant",
        "working_capital": "Often negative WC via deferred revenue / annual prepay",
        "operating_leverage": "Very high once CAC is covered — incremental seats drop through at high GM",
        "pricing_model": "Subscription / usage tiers; expansion via seats and modules",
        "porter": {
            "rivalry": "High — feature and price competition",
            "entry_barriers": "Medium — product + brand + switching costs",
            "supplier_power": "Low-Medium — cloud infra commoditized",
            "customer_power": "Medium — multi-year contracts raise switching costs",
            "substitutes": "Medium — build-in-house, point tools",
        },
        "concentration": "Winner-take-most in many categories",
        "typical_moats": ["switching_costs", "network_effects", "technology", "customer_lock_in"],
        "lifecycle_default": "growth",
    },
    "it_services": {
        "value_drivers": ["Utilization", "Billing Rate", "Attrition", "Deal Wins", "Offshore Mix"],
        "unit_econ_chain": [
            "Billable revenue",
            "Gross profit after delivery cost",
            "Contribution after account acquisition cost",
            "Operating profit after SG&A",
            "Free cash flow after WC (receivables)",
        ],
        "capital_intensity": "People-intensive, asset-light on plant; cash tied in receivables",
        "working_capital": "Receivables-driven; DSO discipline matters",
        "operating_leverage": "Moderate — fixed bench and SG&A vs utilization",
        "pricing_model": "T&M / fixed-price / outcome contracts",
        "porter": {
            "rivalry": "High — global majors and specialists",
            "entry_barriers": "Medium — relationships, scale, delivery talent",
            "supplier_power": "High — scarce skilled talent",
            "customer_power": "High — large enterprise buyers",
            "substitutes": "Medium — captive centers, automation, SaaS",
        },
        "concentration": "Top-tier oligopoly + long specialist tail",
        "typical_moats": ["switching_costs", "scale", "brand", "customer_lock_in"],
        "lifecycle_default": "mature",
    },
    "cement": {
        "value_drivers": ["Utilization", "Realization", "Fuel Cost", "Freight", "Regional Market Share"],
        "unit_econ_chain": [
            "Volume × realization",
            "Gross profit after fuel/power/raw materials",
            "Contribution after freight",
            "Operating profit after fixed plant opex",
            "Free cash after maintenance/growth capex",
        ],
        "capital_intensity": "Very high — kilns, grinding, logistics",
        "working_capital": "Inventory + receivables; freight and fuel WC swings",
        "operating_leverage": "High — fixed plant costs amplify utilization swings",
        "pricing_model": "Regional realization; freight-parity pricing",
        "porter": {
            "rivalry": "High — regional price wars",
            "entry_barriers": "High — capex, limestone, logistics",
            "supplier_power": "Medium-High — fuel and power",
            "customer_power": "Medium — dealers and projects",
            "substitutes": "Low — limited structural substitutes for cement",
        },
        "concentration": "Regional oligopolies",
        "typical_moats": ["scale", "cost_leadership", "distribution", "licensing"],
        "lifecycle_default": "cyclical_recovery",
    },
    "airlines": {
        "value_drivers": ["Load Factor", "Yield", "ATF", "Ancillary Revenue", "Fleet Utilization"],
        "unit_econ_chain": [
            "Passenger + ancillary revenue",
            "Gross contribution after fuel/airport",
            "Contribution after variable crew/handling",
            "Operating profit after fixed fleet costs",
            "Free cash after aircraft capex/leases",
        ],
        "capital_intensity": "Extremely high — fleet and leases",
        "working_capital": "Tickets prepaid (favorable) vs fuel/maintenance WC",
        "operating_leverage": "Extreme — fixed fleet costs vs load factor",
        "pricing_model": "Dynamic yield management + ancillaries",
        "porter": {
            "rivalry": "Very high — price competition on routes",
            "entry_barriers": "High — slots, fleet, regulation",
            "supplier_power": "High — OEMs, lessors, fuel",
            "customer_power": "High — price-sensitive travelers",
            "substitutes": "Medium — rail/road on short haul; video for business",
        },
        "concentration": "Route-level oligopoly / duopoly common",
        "typical_moats": ["scale", "cost_leadership", "distribution"],
        "lifecycle_default": "cyclical_recovery",
    },
    "hospitals": {
        "value_drivers": ["ARPOB", "Occupancy", "ALOS", "Payer Mix", "Specialty Mix"],
        "unit_econ_chain": [
            "Patient revenue (ARPOB × occupied beds)",
            "Gross profit after medical consumables",
            "Contribution after variable clinical cost",
            "Operating profit after fixed hospital opex",
            "Free cash after equipment/expansion capex",
        ],
        "capital_intensity": "High — land, beds, equipment",
        "working_capital": "Receivables from insurers/government; inventory of consumables",
        "operating_leverage": "High — fixed hospital costs vs occupancy",
        "pricing_model": "Procedure/package pricing; payer contracts",
        "porter": {
            "rivalry": "Medium-High — local catchment competition",
            "entry_barriers": "High — licenses, specialists, capex",
            "supplier_power": "Medium — device/pharma vendors",
            "customer_power": "Medium — patients + insurance payers",
            "substitutes": "Low-Medium — outpatient / day-care shift",
        },
        "concentration": "Fragmented nationally; local leadership matters",
        "typical_moats": ["brand", "scale", "licensing", "customer_lock_in"],
        "lifecycle_default": "expansion",
    },
    "retail": {
        "value_drivers": ["Same-Store Growth", "Gross Margin", "Inventory Turns", "Rent/Sales", "Traffic"],
        "unit_econ_chain": [
            "Store / e-comm revenue",
            "Gross profit after COGS",
            "Contribution after store variable cost",
            "Operating profit after rent/SG&A",
            "Free cash after inventory and store capex",
        ],
        "capital_intensity": "Moderate-High — inventory and stores",
        "working_capital": "Inventory-heavy; payables can offset",
        "operating_leverage": "Medium — rent and labor fixed vs traffic",
        "pricing_model": "EDLP / promotional / private label mix",
        "porter": {
            "rivalry": "High",
            "entry_barriers": "Medium — brand, locations, supply chain",
            "supplier_power": "Medium",
            "customer_power": "High",
            "substitutes": "High — online and formats",
        },
        "concentration": "Format-dependent",
        "typical_moats": ["scale", "cost_leadership", "brand", "distribution"],
        "lifecycle_default": "mature",
    },
    "marketplace": {
        "value_drivers": ["GMV", "Take Rate", "Liquidity", "CAC", "Contribution Margin"],
        "unit_econ_chain": [
            "Take-rate revenue on GMV",
            "Gross profit after payment/fulfillment COGS",
            "Contribution after subsidies/CAC",
            "Operating profit after platform opex",
            "Free cash after WC and growth investment",
        ],
        "capital_intensity": "Asset-light platform; optional logistics capex",
        "working_capital": "Often float / deferred settlement favorable",
        "operating_leverage": "Very high once liquidity and brand exist",
        "pricing_model": "Take rate + ads + financing attachments",
        "porter": {
            "rivalry": "High — winner-take-most dynamics",
            "entry_barriers": "High once network effects lock in",
            "supplier_power": "Medium — sellers",
            "customer_power": "Medium — buyers multi-home early",
            "substitutes": "Medium — direct brand sites, offline",
        },
        "concentration": "Often duopoly / monopoly by category",
        "typical_moats": ["network_effects", "scale", "brand", "technology"],
        "lifecycle_default": "hypergrowth",
    },
    "manufacturing": {
        "value_drivers": ["Utilization", "Realization", "Input Cost", "Mix", "Warranty/Quality"],
        "unit_econ_chain": [
            "Unit volume × ASP",
            "Gross profit after materials/energy",
            "Contribution after variable conversion cost",
            "Operating profit after fixed plant opex",
            "Free cash after maintenance/growth capex and WC",
        ],
        "capital_intensity": "High — plant and tooling",
        "working_capital": "Inventory + receivables intensive",
        "operating_leverage": "High with utilization",
        "pricing_model": "Contract / list pricing with commodity pass-through",
        "porter": {
            "rivalry": "High",
            "entry_barriers": "Medium-High — capex and OEM qualification",
            "supplier_power": "Medium-High — commodities and components",
            "customer_power": "High — OEM concentration common",
            "substitutes": "Medium",
        },
        "concentration": "Industry-specific",
        "typical_moats": ["scale", "cost_leadership", "technology", "customer_lock_in"],
        "lifecycle_default": "mature",
    },
    "commodity": {
        "value_drivers": ["Crack/Spread", "Utilization", "Feedstock Cost", "Product Mix", "Inventory Gain/Loss"],
        "unit_econ_chain": [
            "Throughput × realization",
            "Gross margin after feedstock",
            "Contribution after variable energy/chemicals",
            "Operating profit after fixed plant",
            "Free cash after sustaining/growth capex",
        ],
        "capital_intensity": "Very high",
        "working_capital": "Large inventory swings with commodity prices",
        "operating_leverage": "High + commodity cyclicality",
        "pricing_model": "Benchmark-linked commodity pricing",
        "porter": {
            "rivalry": "High globally",
            "entry_barriers": "Very high — scale and regulation",
            "supplier_power": "High — crude/feedstock",
            "customer_power": "Medium",
            "substitutes": "Medium — energy transition over time",
        },
        "concentration": "Global majors + regional refiners",
        "typical_moats": ["scale", "cost_leadership", "integration", "licensing"],
        "lifecycle_default": "cyclical_recovery",
    },
    "insurance": {
        "value_drivers": ["Combined Ratio", "Investment Yield", "Persistency", "New Business Margin", "Solvency"],
        "unit_econ_chain": [
            "Premium income",
            "Underwriting result after claims/expenses",
            "Contribution after commission",
            "Operating profit including float investment",
            "Free capital generation after solvency buffers",
        ],
        "capital_intensity": "Capital intensive via solvency requirements",
        "working_capital": "Float is a funding advantage when underwriting is disciplined",
        "operating_leverage": "Moderate — actuarial and distribution scale",
        "pricing_model": "Risk-priced premiums; product riders",
        "porter": {
            "rivalry": "High",
            "entry_barriers": "High — license and capital",
            "supplier_power": "Low-Medium",
            "customer_power": "Medium",
            "substitutes": "Medium — self-insure / alternate risk transfer",
        },
        "concentration": "Regulated oligopoly traits",
        "typical_moats": ["brand", "distribution", "scale", "licensing"],
        "lifecycle_default": "growth",
    },
    "utility": {
        "value_drivers": ["Regulated RoE", "Volume", "Tariff", "AT&C Losses", "Capex Allowance"],
        "unit_econ_chain": [
            "Regulated revenue",
            "Gross margin after power purchase",
            "Contribution after variable distribution cost",
            "Operating profit after fixed network opex",
            "Free cash after regulated capex",
        ],
        "capital_intensity": "Very high network assets",
        "working_capital": "Receivables from consumers / discoms",
        "operating_leverage": "High fixed network costs",
        "pricing_model": "Regulated tariffs",
        "porter": {
            "rivalry": "Low in franchise area",
            "entry_barriers": "Very high — franchise/license",
            "supplier_power": "Medium — generation",
            "customer_power": "Low-Medium — captive consumers",
            "substitutes": "Low near-term; distributed generation long-term",
        },
        "concentration": "Geographic monopoly / franchise",
        "typical_moats": ["licensing", "scale", "distribution"],
        "lifecycle_default": "mature",
    },
    "infrastructure": {
        "value_drivers": ["Utilization", "ARPU", "Tenancy", "Capex Intensity", "Regulatory Spectrum"],
        "unit_econ_chain": [
            "Service / tenancy revenue",
            "Gross profit after network COGS",
            "Contribution after variable traffic cost",
            "Operating profit after fixed network opex",
            "Free cash after spectrum/network capex",
        ],
        "capital_intensity": "Very high",
        "working_capital": "Moderate; capex dominates cash use",
        "operating_leverage": "High once network is built",
        "pricing_model": "ARPU / tenancy / wholesale",
        "porter": {
            "rivalry": "High among operators",
            "entry_barriers": "Very high — spectrum and capex",
            "supplier_power": "Medium — vendors",
            "customer_power": "Medium-High",
            "substitutes": "Medium — OTT / alternate access",
        },
        "concentration": "Oligopoly",
        "typical_moats": ["scale", "licensing", "network_effects", "distribution"],
        "lifecycle_default": "mature",
    },
    "platform": {
        "value_drivers": ["Active Users", "Engagement", "Take Rate / Ads", "Network Density", "CAC"],
        "unit_econ_chain": [
            "Platform revenue (ads/take-rate/subscriptions)",
            "Gross profit after infra COGS",
            "Contribution after user acquisition",
            "Operating profit after platform opex",
            "Free cash after growth investment",
        ],
        "capital_intensity": "Asset-light relative to industrials",
        "working_capital": "Often favorable platform float",
        "operating_leverage": "Very high with network density",
        "pricing_model": "Ads, take-rate, subscriptions",
        "porter": {
            "rivalry": "High early; winner-take-most later",
            "entry_barriers": "High once network effects compound",
            "supplier_power": "Low-Medium",
            "customer_power": "Medium",
            "substitutes": "Medium",
        },
        "concentration": "Winner-take-most",
        "typical_moats": ["network_effects", "technology", "brand", "switching_costs"],
        "lifecycle_default": "growth",
    },
    "conglomerate": {
        "value_drivers": ["Segment Mix", "Capital Allocation", "Subsidiary ROIC", "Synergies", "Holding Discount"],
        "unit_econ_chain": [
            "Segment revenues",
            "Segment gross profits",
            "Consolidated contribution",
            "Operating profit after corporate cost",
            "Group free cash after allocation across segments",
        ],
        "capital_intensity": "Varies by segment — allocation skill is the constraint",
        "working_capital": "Segment-specific",
        "operating_leverage": "Segment-dependent",
        "pricing_model": "Multi-model across businesses",
        "porter": {
            "rivalry": "Competes in each industry separately",
            "entry_barriers": "Capital and complexity",
            "supplier_power": "Varies",
            "customer_power": "Varies",
            "substitutes": "Varies",
        },
        "concentration": "N/A at group level",
        "typical_moats": ["scale", "distribution", "brand", "cost_leadership"],
        "lifecycle_default": "mature",
    },
    "restaurant": {
        "value_drivers": ["Same-Store Sales", "Food Cost %", "Labor Cost %", "Table Turns", "AUV"],
        "unit_econ_chain": [
            "Ticket revenue",
            "Gross profit after food cost",
            "Contribution after store labor/variable",
            "Store operating profit after rent",
            "Free cash after store maintenance / new-unit capex",
        ],
        "capital_intensity": "Moderate — fit-outs and equipment",
        "working_capital": "Low inventory; cash business often",
        "operating_leverage": "High store-level fixed rent/labor",
        "pricing_model": "Menu pricing; value tiers",
        "porter": {
            "rivalry": "Very high",
            "entry_barriers": "Low-Medium",
            "supplier_power": "Medium",
            "customer_power": "High",
            "substitutes": "Very high",
        },
        "concentration": "Fragmented",
        "typical_moats": ["brand", "scale", "cost_leadership"],
        "lifecycle_default": "growth",
    },
    "subscription": {
        "value_drivers": ["Retention", "ARPU", "CAC", "Gross Margin", "Expansion Revenue"],
        "unit_econ_chain": [
            "Subscription revenue",
            "Gross profit after service COGS",
            "Contribution after CAC",
            "Operating profit after growth opex",
            "Free cash after deferred revenue / WC",
        ],
        "capital_intensity": "Asset-light",
        "working_capital": "Deferred revenue often favorable",
        "operating_leverage": "High with retention",
        "pricing_model": "Recurring membership / tiers",
        "porter": {
            "rivalry": "High",
            "entry_barriers": "Medium — brand and habit",
            "supplier_power": "Low-Medium",
            "customer_power": "Medium",
            "substitutes": "High",
        },
        "concentration": "Category-specific",
        "typical_moats": ["switching_costs", "brand", "customer_lock_in"],
        "lifecycle_default": "growth",
    },
    "unknown": {
        "value_drivers": ["Revenue Growth", "Margins", "Returns on Capital", "Cash Conversion", "Competitive Position"],
        "unit_econ_chain": [
            "Revenue",
            "Gross Profit",
            "Contribution Margin",
            "Operating Profit",
            "Free Cash Flow",
        ],
        "capital_intensity": "Requires industry classification before precision",
        "working_capital": "Industry-dependent",
        "operating_leverage": "Industry-dependent",
        "pricing_model": "Industry-dependent",
        "porter": {
            "rivalry": "Unknown without industry context",
            "entry_barriers": "Unknown without industry context",
            "supplier_power": "Unknown without industry context",
            "customer_power": "Unknown without industry context",
            "substitutes": "Unknown without industry context",
        },
        "concentration": "Unknown",
        "typical_moats": [],
        "lifecycle_default": "mature",
    },
}


# BI industry keys → Phase 3.1 Industry DNA keys (BI consumes DNA; does not duplicate).
_BI_TO_II_KEY: dict[str, str] = {
    "saas": "software",
    "utility": "utilities",
    "marketplace": "internet_platforms",
    "platform": "internet_platforms",
    "restaurant": "qsr",
    "subscription": "software",
    "commodity": "metals",
    "manufacturing": "capital_goods",
    # A conglomerate is not an oil & gas company. The old oil_gas fallback
    # handed GRM / Reserve Replacement drivers to every diversified name.
    "conglomerate": "capital_goods",
}


def _overlay_industry_dna(industry_key: str, base: dict[str, Any]) -> dict[str, Any]:
    """Enrich BI templates from canonical Industry DNA when available."""
    ii_key = _BI_TO_II_KEY.get(industry_key, industry_key)
    try:
        from industry_intelligence.dna_catalog import get_dna

        dna = get_dna(ii_key)
    except Exception:
        return base
    if not dna:
        return base

    out = dict(base)
    if dna.value_drivers:
        out["value_drivers"] = list(dna.value_drivers)
    if dna.capital_intensity:
        out["capital_intensity"] = dna.capital_intensity
    if dna.working_capital:
        out["working_capital"] = dna.working_capital
    if dna.operating_leverage:
        out["operating_leverage"] = dna.operating_leverage
    if dna.pricing_power:
        out["pricing_model"] = dna.pricing_power
    if dna.porter:
        out["porter"] = {
            "rivalry": dna.porter.rivalry,
            "entry_barriers": dna.porter.entry_barriers,
            "supplier_power": dna.porter.supplier_power,
            "customer_power": dna.porter.buyer_power,
            "substitutes": dna.porter.substitutes,
        }
    if dna.concentration:
        out["concentration"] = dna.concentration
    if dna.lifecycle:
        out["lifecycle_default"] = dna.lifecycle
    # Prefer DNA revenue/margin chain as unit-econ narrative when BI chain empty-ish
    if dna.revenue_drivers and dna.margin_drivers:
        out["unit_econ_chain"] = [
            f"Revenue: {', '.join(dna.revenue_drivers[:3])}",
            f"Margins: {', '.join(dna.margin_drivers[:3])}",
            f"Cash conversion: {dna.cash_conversion}",
            f"Capital intensity: {dna.capital_intensity}",
            f"Typical ROIC: {dna.typical_roic}",
        ]
    out["from_industry_dna"] = True
    out["industry_dna_key"] = ii_key
    out["valuation_methods"] = list(dna.valuation_methods)
    out["typical_risks"] = list(dna.typical_risks)
    return out


def template_for(industry_key: str) -> dict[str, Any]:
    base = dict(INDUSTRY_TEMPLATES.get(industry_key) or INDUSTRY_TEMPLATES["unknown"])
    return _overlay_industry_dna(industry_key, base)
