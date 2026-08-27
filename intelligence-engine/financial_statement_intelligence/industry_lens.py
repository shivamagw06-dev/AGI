"""Industry Interpretation — Module 11.

"Same numbers mean different things." This module does two things:

1. Teaches the sector-specific KPIs the brief lists (NIM/GNPA/CASA for
   banks, utilization/attrition for IT services, SSSG for retail,
   ARPOB/occupancy for hospitals, GRM/crack spread for oil & gas) as a
   knowledge base — these are not fields in our generic statement
   schema, so they are taught as concepts, the same way Phase 1 teaches
   accounting concepts.
2. Annotates which of the STANDARD ratios computed by ``ratio_engine``
   are the primary lens, a secondary check, structurally not comparable,
   or not meaningful for a given sector — mirroring the same
   forbidden-by-sector pattern used by ``framework_selection`` elsewhere
   in this codebase, applied here to ratio interpretation instead of
   valuation-framework selection.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SectorKpi:
    key: str
    sector: str
    title: str
    definition: str
    why_it_matters: str


SECTOR_KPIS: dict[str, list[SectorKpi]] = {
    "banks": [
        SectorKpi("nim", "banks", "Net Interest Margin (NIM)",
                  "Net interest income as a percentage of average interest-earning assets.",
                  "The core profitability driver of a bank's lending book — the spread between what it earns on assets and pays on liabilities."),
        SectorKpi("gnpa", "banks", "Gross Non-Performing Assets (GNPA)",
                  "Loans where interest/principal payments are overdue, as a percentage of gross advances.",
                  "The primary asset-quality signal — rising GNPA foreshadows provisioning and capital pressure."),
        SectorKpi("casa", "banks", "CASA Ratio",
                  "Current Account + Savings Account deposits as a percentage of total deposits.",
                  "Low-cost, sticky funding — a high CASA ratio supports NIM by lowering the cost of funds."),
        SectorKpi("provision_coverage", "banks", "Provision Coverage Ratio (PCR)",
                  "Provisions held against NPAs as a percentage of Gross NPAs.",
                  "Measures how conservatively a bank has already absorbed expected credit losses — higher PCR means less future earnings shock from the same NPA pool."),
        SectorKpi("credit_cost", "banks", "Credit Cost",
                  "Provisions for the period as a percentage of average advances.",
                  "The annualised cost of credit risk — rising credit cost directly compresses PAT independent of NIM."),
    ],
    "it_services": [
        SectorKpi("utilization", "it_services", "Utilization Rate",
                  "Percentage of billable employees actually deployed on client work.",
                  "The primary operating-leverage lever for a people business — rising utilization drops straight to margin."),
        SectorKpi("attrition", "it_services", "Attrition Rate",
                  "Annualised percentage of employees who leave voluntarily.",
                  "High attrition raises hiring/training costs and risks client delivery quality — a leading indicator of margin pressure."),
        SectorKpi("deal_wins", "it_services", "Deal Wins / TCV",
                  "Total Contract Value of new deals signed in the period.",
                  "The forward revenue indicator for a services business — current revenue reflects deals signed 1-3 years ago."),
        SectorKpi("offshore_mix", "it_services", "Offshore Mix",
                  "Percentage of delivery effort performed offshore versus onshore.",
                  "Offshore delivery carries structurally higher margin — a rising offshore mix supports margin expansion independent of pricing."),
    ],
    "retail": [
        SectorKpi("sssg", "retail", "Same-Store Sales Growth (SSSG)",
                  "Revenue growth from stores open for at least a full comparable period, excluding new store openings.",
                  "Isolates organic demand growth from growth that is purely a function of adding new stores."),
        SectorKpi("inventory_turns", "retail", "Inventory Turns",
                  "How many times inventory is sold and replaced per year.",
                  "Retail economics are turns-driven — a retailer can be profitable on thin margins if turns are high enough."),
    ],
    "hospitals": [
        SectorKpi("arpob", "hospitals", "Average Revenue Per Occupied Bed (ARPOB)",
                  "Revenue divided by occupied bed-days in the period.",
                  "The core realisation metric for a hospital — driven by payor mix, case complexity, and pricing."),
        SectorKpi("occupancy", "hospitals", "Occupancy Rate",
                  "Occupied beds as a percentage of total operating beds.",
                  "The primary capacity-utilization lever — hospitals have high fixed costs, so occupancy drives operating leverage."),
        SectorKpi("alos", "hospitals", "Average Length of Stay (ALOS)",
                  "Average number of days a patient occupies a bed per admission.",
                  "Shorter ALOS with stable case mix generally signals efficiency gains; a rising ALOS can signal case-mix shift or inefficiency."),
        SectorKpi("case_mix", "hospitals", "Case Mix",
                  "The proportion of complex/high-realisation cases versus routine cases.",
                  "A shift toward complex cases raises ARPOB even with flat occupancy and ALOS."),
    ],
    "oil_gas": [
        SectorKpi("grm", "oil_gas", "Gross Refining Margin (GRM)",
                  "Revenue per barrel of crude refined, minus the cost of that crude.",
                  "The core refining profitability metric — largely a function of regional crack spreads, not company-specific execution."),
        SectorKpi("crack_spread", "oil_gas", "Crack Spread",
                  "The price difference between refined products (petrol/diesel) and crude oil input.",
                  "The macro driver behind GRM — refiners have limited control over this and are largely price-takers."),
        SectorKpi("upstream_production", "oil_gas", "Upstream Production",
                  "Volume of crude oil/gas extracted in the period.",
                  "The volume driver for exploration & production economics, independent of price."),
        SectorKpi("downstream_margin", "oil_gas", "Downstream Margin",
                  "Margin earned on refined-product marketing and distribution.",
                  "Downstream margins are typically more stable than upstream/refining margins, providing earnings ballast through commodity cycles."),
    ],
}


@dataclass(frozen=True)
class RatioApplicability:
    ratio_key: str
    role: str  # "primary" | "secondary" | "structurally_different" | "not_meaningful" | "not_applicable"
    note: str


SECTOR_RATIO_APPLICABILITY: dict[str, list[RatioApplicability]] = {
    "banks": [
        RatioApplicability("roe", "primary", "Banks are best judged on ROE given their capital-intensive, leveraged balance sheets."),
        RatioApplicability("debt_to_equity", "not_meaningful", "Deposits are a bank's core funding, not comparable debt in the industrial sense — Debt/Equity is structurally high by design."),
        RatioApplicability("current_ratio", "not_applicable", "Banks do not operate a conventional current-asset/current-liability cycle; liquidity is assessed via LCR/NSFR-style metrics instead."),
        RatioApplicability("inventory_turnover", "not_applicable", "Banks carry no inventory."),
        RatioApplicability("gross_margin", "not_meaningful", "Banks have no COGS in the conventional sense — use NIM instead."),
        RatioApplicability("interest_coverage", "structurally_different", "Interest expense IS the cost of a bank's core funding, not a cost of debt on top of an operating business — read alongside NIM, not in isolation."),
    ],
    "it_services": [
        RatioApplicability("inventory_turnover", "not_applicable", "IT services businesses hold minimal/no inventory."),
        RatioApplicability("gross_margin", "primary", "A clean proxy for utilization and offshore-mix trends in a people-driven business."),
        RatioApplicability("roic", "primary", "Asset-light economics make ROIC a clean capital-efficiency signal for this sector."),
        RatioApplicability("debt_to_equity", "secondary", "IT services businesses are typically low-leverage; large moves here are more unusual and worth investigating."),
    ],
    "retail": [
        RatioApplicability("inventory_turnover", "primary", "Retail economics are turns-driven — this is often more diagnostic than gross margin alone."),
        RatioApplicability("cash_conversion_cycle", "primary", "Negative or very low CCC (collect before paying suppliers) is a hallmark of efficient retail models."),
        RatioApplicability("interest_coverage", "secondary", "Relevant mainly for retailers carrying store-expansion or inventory-financing debt."),
    ],
    "hospitals": [
        RatioApplicability("gross_margin", "secondary", "Less diagnostic than ARPOB/Occupancy — high fixed-cost structure means operating margin swings more with occupancy than with a conventional COGS line."),
        RatioApplicability("roce", "primary", "Capital-intensive bed/equipment base makes ROCE a strong capital-efficiency signal."),
        RatioApplicability("inventory_turnover", "secondary", "Applies to pharmacy/consumables inventory only — a small part of total hospital economics."),
    ],
    "oil_gas": [
        RatioApplicability("gross_margin", "structurally_different", "Highly volatile and driven by regional crack spreads/commodity prices, not company execution — read alongside GRM."),
        RatioApplicability("net_debt_to_ebitda", "primary", "Capital-intensive, cyclical earnings make leverage capacity a critical solvency signal through the cycle."),
        RatioApplicability("roic", "primary", "The clearest test of whether upstream/downstream capital allocation is creating value through a full commodity cycle."),
    ],
}


def sector_kpis(sector: str) -> list[dict]:
    return [
        {"key": k.key, "title": k.title, "definition": k.definition, "why_it_matters": k.why_it_matters}
        for k in SECTOR_KPIS.get(sector, [])
    ]


def ratio_applicability(sector: str) -> list[dict]:
    return [
        {"ratio_key": r.ratio_key, "role": r.role, "note": r.note}
        for r in SECTOR_RATIO_APPLICABILITY.get(sector, [])
    ]


def industry_context(sector: str) -> dict:
    return {
        "sector": sector,
        "found": sector in SECTOR_KPIS or sector in SECTOR_RATIO_APPLICABILITY,
        "sector_kpis": sector_kpis(sector),
        "ratio_applicability": ratio_applicability(sector),
    }


def list_sectors() -> list[str]:
    return sorted(set(SECTOR_KPIS.keys()) | set(SECTOR_RATIO_APPLICABILITY.keys()))
