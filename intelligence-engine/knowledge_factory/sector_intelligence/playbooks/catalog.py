"""Executable institutional Sector Playbooks — how professionals analyse the sector."""

from __future__ import annotations

from typing import Any

from knowledge_factory.sector_intelligence.dna.catalog import sector_dna
from knowledge_factory.sector_intelligence.schema import SECTOR_UNIVERSE

_PLAYBOOKS: dict[str, dict[str, Any]] = {
    "it_services": {
        "primary_value_drivers": [
            "Digital transformation spending",
            "AI adoption",
            "Large-deal pipeline / TCV",
            "USD/INR",
        ],
        "watch_metrics": ["ebit_margin", "utilisation", "attrition", "deal_tcv", "revenue_growth"],
        "typical_risks": [
            "Wage inflation",
            "Pricing pressure",
            "Client IT budget cuts",
            "Currency appreciation (INR)",
        ],
        "preferred_valuation": ["pe", "ev_ebitda", "dcf_stable_mature"],
        "historical_behaviour": [
            "Outperforms during global tech spending cycles",
            "Sensitive to US recession expectations",
            "Often rerates before earnings acceleration",
        ],
        "analysis_checklist": [
            "Vertical mix (BFSI / retail / manufacturing)",
            "Deal win rates and large-deal concentration",
            "Margin bridge (util, pricing, pyramid)",
            "FX hedge book",
        ],
    },
    "banks": {
        "primary_value_drivers": [
            "Credit growth",
            "NIM trajectory",
            "Asset quality / credit costs",
            "Deposit franchise cost",
        ],
        "watch_metrics": ["nim", "roe", "gnpa", "slippages", "casa", "cet1"],
        "typical_risks": [
            "Asset quality cycle",
            "Liability cost spikes",
            "Regulatory capital raises",
            "Unsecured retail stress",
        ],
        "preferred_valuation": ["residual_income", "pb", "roe"],
        "historical_behaviour": [
            "PB converges to ROE through the credit cycle",
            "Rate hiking cycles reprice assets with lag",
            "Drawdowns cluster around NPA surprises",
        ],
        "analysis_checklist": [
            "Loan mix (retail / corporate / agri)",
            "Deposit beta vs rate cycle",
            "Provision coverage and restructured book",
            "Capital adequacy headroom",
        ],
        "framework_note": "Do not use traditional DCF as primary — use Residual Income / P/B.",
    },
    "nbfc": {
        "primary_value_drivers": ["AUM growth", "Spreads", "Credit costs", "Funding access"],
        "watch_metrics": ["nim", "roe", "stage3", "leverage", "al_m"],
        "typical_risks": ["Wholesale funding freeze", "Asset-liability mismatch", "Regulatory tightening"],
        "preferred_valuation": ["pb", "roe", "residual_income"],
        "historical_behaviour": ["Funding shocks dominate", "Rate cuts support volumes and spreads"],
        "analysis_checklist": ["Liability mix", "Co-lending / partnerships", "Geographic concentration"],
    },
    "pharma": {
        "primary_value_drivers": ["US launches", "India branded growth", "FDA compliance", "API"],
        "watch_metrics": ["us_sales", "ebitda_margin", "r_and_d", "anda_pipeline"],
        "typical_risks": ["FDA warnings", "Price erosion", "Litigation", "FX"],
        "preferred_valuation": ["pe", "ev_ebitda", "dcf"],
        "historical_behaviour": ["Binary regulatory events", "Defensive domestically"],
        "analysis_checklist": ["Plant compliance status", "Channel inventory", "Therapy mix"],
    },
    "auto": {
        "primary_value_drivers": ["Volumes", "Mix / premiumisation", "Commodity costs", "Financing rates"],
        "watch_metrics": ["wholesale_retail_volumes", "asp", "ebitda_margin", "inventory_days"],
        "typical_risks": ["Rate-driven demand freeze", "Commodity spike", "EV transition capex"],
        "preferred_valuation": ["ev_ebitda", "pe", "dcf_cycle_normalised"],
        "historical_behaviour": ["Rate cuts unlock volumes", "Operating leverage amplifies earnings"],
        "analysis_checklist": ["Channel inventory", "EV roadmap", "Export mix"],
    },
    "fmcg": {
        "primary_value_drivers": ["Volume growth", "Gross margin", "Premiumisation", "Rural recovery"],
        "watch_metrics": ["volume_growth", "gross_margin", "ad_spend", "distribution_reach"],
        "typical_risks": ["Input inflation", "Rural slowdown", "Competitive intensity"],
        "preferred_valuation": ["pe", "ev_ebitda", "dcf"],
        "historical_behaviour": ["Defensive; volume recovery drives rerate"],
        "analysis_checklist": ["Price vs volume bridge", "Category competitive intensity", "Rural/urban mix"],
    },
    "oil_gas": {
        "primary_value_drivers": ["Oil price", "Crack spreads", "Marketing margins", "Volumes"],
        "watch_metrics": ["brent", "singapore_cracks", "grm", "inventory"],
        "typical_risks": ["Oil crash", "Under-recoveries", "Policy"],
        "preferred_valuation": ["ev_ebitda", "pe_normalised", "dcf_midcycle"],
        "historical_behaviour": ["Commodity beta dominates equity returns"],
        "analysis_checklist": ["Upstream vs downstream mix", "Inventory gains quality", "Debt"],
    },
    "industrials": {
        "primary_value_drivers": ["Order inflow", "Capex cycle", "Margin mix", "Execution"],
        "watch_metrics": ["order_book", "order_inflow", "ebitda_margin", "working_capital"],
        "typical_risks": ["Order deferrals", "Working capital blowouts", "Execution delays"],
        "preferred_valuation": ["ev_ebitda", "dcf", "pe"],
        "historical_behaviour": ["Leads private capex recoveries"],
        "analysis_checklist": ["Order book quality", "Bid pipeline", "Receivables"],
    },
    "utilities": {
        "primary_value_drivers": ["Regulated returns", "Capacity adds", "Dividend capacity"],
        "watch_metrics": ["regulated_roe", "plf", "receivables", "capex"],
        "typical_risks": ["Rate hikes (bond proxy)", "Regulatory resets", "Fuel cost"],
        "preferred_valuation": ["dcf", "dividend_discount", "ev_ebitda"],
        "historical_behaviour": ["Bond-proxy; rate cuts support multiples"],
        "analysis_checklist": ["PPA quality", "Regulatory asset backlog", "Leverage"],
    },
    "internet": {
        "primary_value_drivers": ["GMV / take rate", "Unit economics", "Cohort retention", "Cash burn"],
        "watch_metrics": ["revenue_growth", "contribution_margin", "cash_burn", "users"],
        "typical_risks": ["Indefinite losses", "Competition", "Regulation"],
        "preferred_valuation": ["ev_sales", "revenue_multiple", "growth"],
        "historical_behaviour": ["Multiples compress when growth decelerates"],
        "analysis_checklist": ["Path to profit", "Cohort LTV/CAC", "Competitive intensity"],
        "framework_note": "Avoid book-value / traditional Graham as primary.",
    },
}


def sector_playbook(sector: str) -> dict[str, Any]:
    from knowledge_factory.sector_intelligence.schema import canonicalize

    key = canonicalize(sector) or sector
    dna = sector_dna(key)
    custom = _PLAYBOOKS.get(key, {})
    return {
        "sector": key,
        "display_name": dna.get("display_name"),
        "business_model": dna.get("business_model"),
        "primary_value_drivers": custom.get("primary_value_drivers") or dna.get("growth_drivers") or [],
        "watch_metrics": custom.get("watch_metrics")
        or ["revenue_growth", "ebitda_margin", "roic", "leverage"],
        "typical_risks": custom.get("typical_risks")
        or list(dna.get("common_accounting_risks") or [])
        or ["cyclical_downturn"],
        "preferred_valuation": custom.get("preferred_valuation") or dna.get("preferred_frameworks") or [],
        "historical_behaviour": custom.get("historical_behaviour")
        or list(dna.get("historical_characteristics") or []),
        "analysis_checklist": custom.get("analysis_checklist")
        or ["Margins", "Growth durability", "Balance sheet", "Capital allocation"],
        "framework_note": custom.get("framework_note")
        or (
            f"Preferred: {', '.join(dna.get('preferred_frameworks') or [])}. "
            f"Avoid: {', '.join(dna.get('forbidden_frameworks') or []) or 'none'}."
        ),
        "executable": True,
    }


def all_playbooks() -> dict[str, dict[str, Any]]:
    return {s: sector_playbook(s) for s in SECTOR_UNIVERSE}
