#!/usr/bin/env python3
"""Generate dna_catalog.py — run once: python3 -m industry_intelligence._generate_dna_catalog"""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

ROOT = Path(__file__).resolve().parent


def K(key, name, definition, importance, good, poor, rel, lim=""):
    return dict(
        key=key, name=name, definition=definition, importance=importance,
        good_range=good, poor_range=poor, relationships=list(rel), limitations=lim,
    )


def P(entry, supplier, buyer, substitutes, rivalry):
    return dict(
        entry_barriers=entry, supplier_power=supplier, buyer_power=buyer,
        substitutes=substitutes, rivalry=rivalry,
    )


def dna(**kw):
    required = [
        "key", "name", "aliases", "revenue_drivers", "margin_drivers", "cost_drivers",
        "value_drivers", "capital_intensity", "working_capital", "cash_conversion",
        "operating_leverage", "pricing_power", "competitive_structure", "porter",
        "concentration", "regulators", "regulatory_risks", "valuation_methods",
        "valuation_why", "lifecycle", "typical_roic", "typical_growth", "typical_risks",
        "risk_weightings", "macro_sensitivity", "customers", "suppliers",
        "adjacent_industries", "substitutes", "capital_allocation_typical", "kpis",
        "why_margins", "why_roic", "why_leverage", "why_working_capital", "why_valuation",
        "primary_cycle",
    ]
    missing = [r for r in required if r not in kw]
    if missing:
        raise ValueError(f"{kw.get('key')}: missing {missing}")
    return kw


INDUSTRIES: list[dict] = []


def add(**kw):
    INDUSTRIES.append(dna(**kw))


# ========== FINANCIALS ==========
add(
    key="banks", name="Banks", aliases=["bank", "banking"],
    revenue_drivers=["Loan growth", "NIM", "Fee income"],
    margin_drivers=["CASA / funding cost", "Credit cost", "Cost-to-income"],
    cost_drivers=["Interest expense", "Provisions", "Opex"],
    value_drivers=["NIM", "CASA", "Credit Cost", "Fee Income", "Operating Efficiency"],
    capital_intensity="Balance-sheet intensive — equity and deposits fund loans",
    working_capital="Loan book and deposit franchise",
    cash_conversion="Strong when credit costs are controlled",
    operating_leverage="High fixed franchise cost vs incremental loans",
    pricing_power="Moderate — CASA franchise creates funding edge",
    competitive_structure="oligopoly",
    porter=P("High — RBI license, capital, distribution", "Medium — depositors/wholesale", "Medium", "Medium — NBFCs, markets", "High"),
    concentration="Top banks dominate; long tail",
    regulators=["RBI", "SEBI", "DICGC"],
    regulatory_risks=["CET1", "Asset classification", "LCR/NSFR", "PCA"],
    valuation_methods=["P/B", "Residual Income"],
    valuation_why="Book equity is the scarce resource earning the spread",
    lifecycle="mature", typical_roic="Mid-teens ROE for quality franchises",
    typical_growth="Mid-single to low-double-digit loan growth",
    typical_risks=["Credit", "NIM compression", "Liquidity", "Regulatory"],
    risk_weightings={"credit": "High", "regulatory": "High", "demand": "Medium", "refinancing": "Medium", "commodity": "Low"},
    macro_sensitivity=["Interest rates", "Credit cycle", "GDP"],
    customers=["Retail", "SME", "Corporate"], suppliers=["Depositors", "Wholesale markets"],
    adjacent_industries=["nbfc", "insurance", "asset_management"], substitutes=["NBFC credit", "Bonds"],
    capital_allocation_typical="Retain earnings for loan growth and CET1; dividends when buffers comfortable",
    kpis=[
        K("casa", "CASA Ratio", "CASA / deposits", "Cheap sticky funding", "High vs peers", "Falling", ["NIM"]),
        K("nim", "NIM", "NII / average interest-earning assets", "Core spread", "Stable/expanding", "Compressing", ["CASA"]),
        K("gnpa", "Gross NPA", "GNPA / advances", "Asset quality", "Low", "Rising", ["Credit cost"]),
        K("nnpa", "Net NPA", "NNPA / net advances", "Residual credit risk", "Very low", "Elevated", ["PCR"]),
        K("pcr", "PCR", "Provisions / GNPA", "Loss buffer", "High", "Thin", ["GNPA"]),
        K("cet1", "CET1", "CET1 / RWA", "Solvency", "Headroom above minimum", "Near floor", ["Growth"]),
        K("credit_cost", "Credit Cost", "Provisions / advances", "Earnings quality", "Low stable", "Spiking", ["GNPA"]),
    ],
    why_margins="Spreads (NIM) minus credit cost and opex — not merchandise gross margin",
    why_roic="Returns on equity/regulatory capital; ROA structurally low",
    why_leverage="Deposit leverage is the model, capped by capital ratios",
    why_working_capital="The loan book is the WC analogue — growth consumes capital",
    why_valuation="P/B because equity book earns the spread; EV/EBITDA unfit for deposit lenders",
    primary_cycle="credit_cycle",
)

add(
    key="nbfc", name="NBFC", aliases=["nbfc", "housing finance", "hfc", "non-banking"],
    revenue_drivers=["AUM growth", "Yield on advances", "Fees"],
    margin_drivers=["Cost of funds", "Credit cost", "Opex"],
    cost_drivers=["Borrowing cost", "Provisions", "Origination"],
    value_drivers=["Spread", "Asset Quality", "Cost of Funds", "Leverage"],
    capital_intensity="High — growth needs capital and wholesale funding",
    working_capital="Receivables-heavy loan book",
    cash_conversion="Weak in rapid growth; improves when growth slows",
    operating_leverage="Moderate fixed opex over AUM",
    pricing_power="Risk-based; compressed in prime segments",
    competitive_structure="fragmented",
    porter=P("Medium-High — capital, funding, RBI", "High — wholesale funding", "Medium", "High — banks/fintech", "High"),
    concentration="Fragmented with large nationals",
    regulators=["RBI", "NHB", "SEBI"],
    regulatory_risks=["Scale-based rules", "Liquidity", "Capital"],
    valuation_methods=["P/B", "P/E"],
    valuation_why="ROE vs COE with funding-risk discount versus banks",
    lifecycle="growth", typical_roic="Wide dispersion by underwriting quality",
    typical_growth="Often faster than banks when liquidity is easy",
    typical_risks=["ALM/refinancing", "Credit", "Regulatory"],
    risk_weightings={"refinancing": "High", "credit": "High", "regulatory": "High", "demand": "Medium"},
    macro_sensitivity=["Rates", "Liquidity", "Credit cycle"],
    customers=["Retail", "SME", "Vehicle/gold/housing"], suppliers=["Banks", "Bond markets"],
    adjacent_industries=["banks", "real_estate"], substitutes=["Bank loans", "Fintech"],
    capital_allocation_typical="Retain for AUM growth; raise capital when leverage binds",
    kpis=[
        K("spread", "Spread", "Yield − cost of funds", "Core earning power", "Wide/stable", "Compressing", ["COF"]),
        K("aum_growth", "AUM Growth", "Change in AUM", "Momentum", "Funding-sustainable", "Funding spike", ["Leverage"]),
        K("stage3", "Stage-3 / GNPA", "Impaired / advances", "Asset quality", "Low", "Rising", ["Credit cost"]),
        K("crar", "Capital Adequacy", "Capital / RWA", "Solvency", "Headroom", "Tight", ["Growth"]),
    ],
    why_margins="Spreads over wholesale funding — no deposit franchise",
    why_roic="Leverage and credit costs drive more fragile ROE than banks",
    why_leverage="Wholesale leverage amplifies ALM risk",
    why_working_capital="Loan growth is the WC sink",
    why_valuation="P/B with funding and asset-quality discounts",
    primary_cycle="credit_cycle",
)

add(
    key="insurance", name="Insurance", aliases=["life insurance", "general insurance", "insurer"],
    revenue_drivers=["Premiums", "Investment income", "Renewals"],
    margin_drivers=["Underwriting margin", "Combined ratio / VNB", "Investment yield"],
    cost_drivers=["Claims", "Commissions", "Opex"],
    value_drivers=["Premium Growth", "Persistency", "VNB Margin", "Solvency"],
    capital_intensity="Solvency capital intensive; float is investable",
    working_capital="Float and claims reserves",
    cash_conversion="Strong with disciplined underwriting and persistency",
    operating_leverage="Moderate — distribution fixed cost vs premium scale",
    pricing_power="Regulated products; underwriting selection is the edge",
    competitive_structure="oligopoly",
    porter=P("High — IRDAI license, capital", "Medium — agents/reinsurers", "Medium", "Medium — savings/govt schemes", "High"),
    concentration="Top insurers dominate",
    regulators=["IRDAI", "SEBI"],
    regulatory_risks=["Solvency", "Product filing", "Commission caps"],
    valuation_methods=["Embedded Value", "P/EV", "Appraisal Value"],
    valuation_why="In-force book and new-business franchise, not GAAP profit alone",
    lifecycle="growth", typical_roic="Measured via EV/VNB growth",
    typical_growth="Premium/APE tracks protection demand and distribution",
    typical_risks=["Claims", "Persistency", "Markets", "Regulatory"],
    risk_weightings={"regulatory": "High", "execution": "High", "demand": "Medium", "market": "High"},
    macro_sensitivity=["Rates", "Equities (ULIP)", "Household savings"],
    customers=["Retail", "Group"], suppliers=["Agents", "Banks", "Reinsurers"],
    adjacent_industries=["banks", "asset_management", "hospitals"], substitutes=["Deposits", "Mutual funds"],
    capital_allocation_typical="Hold solvency capital; reinvest in distribution",
    kpis=[
        K("ape", "APE", "Normalized new-business premium", "Franchise growth", "Quality growth", "Volume without margin", ["VNB"]),
        K("vnb_margin", "VNB Margin", "VNB / APE", "New-business profitability", "Healthy", "Collapsing", ["Persistency"]),
        K("persistency", "Persistency", "Policies remaining in force", "Book quality", "High", "Falling", ["EV"]),
        K("solvency", "Solvency Ratio", "Available / required capital", "Capital adequacy", "Comfortable", "Near floor", ["Growth"]),
        K("combined_ratio", "Combined Ratio", "(Claims+expense)/premium", "Underwriting profit", "<100%", "Sustained >100%", ["Investment income"]),
    ],
    why_margins="Underwriting plus investment income on float",
    why_roic="EV/VNB versus cost of capital, not industrial ROIC",
    why_leverage="Actuarial/investment leverage on float via solvency",
    why_working_capital="Float/reserves, not inventory",
    why_valuation="Embedded Value captures in-force duration",
    primary_cycle="interest_rate_cycle",
)

add(
    key="asset_management", name="Asset Management", aliases=["amc", "mutual fund", "asset manager"],
    revenue_drivers=["AUM", "Management fees", "Performance fees"],
    margin_drivers=["Fee rate", "Operating leverage on AUM", "Mix"],
    cost_drivers=["Talent", "Distribution", "Compliance"],
    value_drivers=["AUM Growth", "Fee Rate", "Net Flows", "Operating Margin"],
    capital_intensity="Asset-light",
    working_capital="Low — fee receivables",
    cash_conversion="Very high — fees convert with little capex",
    operating_leverage="Very high — incremental AUM drops through",
    pricing_power="Fee compression competitive; brand/performance sustain",
    competitive_structure="oligopoly",
    porter=P("High — SEBI license, distribution, brand", "Medium — talent/distributors", "High", "Medium — PMS/ETFs", "High"),
    concentration="Top AMCs hold most AUM",
    regulators=["SEBI", "AMFI"],
    regulatory_risks=["TER/fee caps", "Distributor rules"],
    valuation_methods=["P/E", "EV/EBITDA", "AUM multiples"],
    valuation_why="Capital-light fee earnings and AUM franchise",
    lifecycle="growth", typical_roic="High when flows positive",
    typical_growth="Tracks financialization and markets",
    typical_risks=["Market beta", "Fee compression", "Outflows"],
    risk_weightings={"market": "High", "regulatory": "High", "demand": "High"},
    macro_sensitivity=["Equity markets", "Rates", "Household savings"],
    customers=["Retail SIPs", "HNIs", "Institutions"], suppliers=["Distributors", "Talent"],
    adjacent_industries=["banks", "insurance"], substitutes=["Direct equities", "ETFs", "PMS"],
    capital_allocation_typical="High FCF to dividends/buybacks after growth opex",
    kpis=[
        K("aum", "AUM", "Assets under management", "Fee base", "Growing quality mix", "Shrinking", ["Fees"]),
        K("net_flows", "Net Flows", "Inflows − outflows", "Organic franchise", "Positive sustained", "Persistent outflows", ["AUM"]),
        K("fee_rate", "Blended Fee Rate", "Fees / AUM", "Pricing power", "Stable", "Compressing", ["Mix"]),
        K("operating_margin", "Operating Margin", "EBIT / revenue", "Scale leverage", "High/expanding", "Falling", ["AUM"]),
    ],
    why_margins="Fee rate minus distribution and talent — scale expands margins",
    why_roic="Little invested capital; structurally high when AUM sticky",
    why_leverage="Low financial leverage; operating leverage on AUM",
    why_working_capital="Minimal fee accrual",
    why_valuation="Earnings/AUM multiples fit capital-light fee models",
    primary_cycle="interest_rate_cycle",
)


def emit_remaining():
    """Add remaining industries in compact form."""
    # IT / software already planned as separate adds below
    pass


# Continue file in part 2 — appended by main()
PART2 = Path(__file__).with_name("_dna_part2.py")


def main() -> None:
    # Import part2 industries if present
    if PART2.exists():
        ns: dict = {}
        exec(PART2.read_text(), {"K": K, "P": P, "add": add, "dna": dna}, ns)

    out = ROOT / "dna_catalog.py"
    lines = [
        '"""Industry DNA catalog — canonical deterministic industry objects.',
        "",
        "Generated/maintained for Phase 3.1 Industry Intelligence Engine.",
        "Do not fabricate company-specific numbers. Qualitative bands only.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
        "from industry_intelligence.schema import IndustryDNA, KPIDefinition, PorterForces",
        "",
        "def _kpi(d: dict) -> KPIDefinition:",
        "    return KPIDefinition(**d)",
        "",
        "def _porter(d: dict) -> PorterForces:",
        "    return PorterForces(**d)",
        "",
        "def _dna(d: dict) -> IndustryDNA:",
        "    raw = dict(d)",
        "    raw['kpis'] = [_kpi(k) for k in raw['kpis']]",
        "    raw['porter'] = _porter(raw['porter'])",
        "    return IndustryDNA(**raw)",
        "",
        "_RAW: list[dict] = [",
    ]
    import pprint
    for ind in INDUSTRIES:
        lines.append(indent_repr(ind) + ",")
    lines.append("]")
    lines.append("")
    lines.append("INDUSTRY_DNA: dict[str, IndustryDNA] = {d['key']: _dna(d) for d in _RAW}")
    lines.append("")
    lines.append("def list_industries() -> list[str]:")
    lines.append("    return sorted(INDUSTRY_DNA.keys())")
    lines.append("")
    lines.append("def get_dna(key: str) -> IndustryDNA | None:")
    lines.append("    return INDUSTRY_DNA.get(key)")
    lines.append("")
    lines.append(f"assert len(INDUSTRY_DNA) >= 30, len(INDUSTRY_DNA)")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {out} with {len(INDUSTRIES)} industries")


def indent_repr(obj: dict) -> str:
    import pprint
    return pprint.pformat(obj, width=100, sort_dicts=False)


if __name__ == "__main__":
    # Load part2 before emit
    if PART2.exists():
        exec(PART2.read_text(), {"K": K, "P": P, "add": add, "dna": dna})
    main()
