"""Deterministic Primary Industry → archetype / DNA / valuation / KPI maps.

Every mapping is keyed on the Capital IQ **Primary Industry** string. Company
descriptions and free text are never used — that is what produced
"Diversified Banks" → conglomerate → oil & gas GRM drivers.
"""

from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Primary Industry → (business archetype, Industry DNA key)
# Ordered regex rules; first match wins. Bank rules precede any "diversified"
# handling so "Diversified Banks" can never fall into a conglomerate bucket.
# ---------------------------------------------------------------------------
_INDUSTRY_RULES: tuple[tuple[str, str, str], ...] = (
    # --- Financials -------------------------------------------------------
    (r"^(diversified|regional|commercial)?\s*banks?$", "Universal Bank", "banks"),
    (r"\bbanks?\b(?!ing services)", "Universal Bank", "banks"),
    (r"asset management|custody banks", "Asset Manager", "asset_management"),
    (r"investment banking|brokerage|capital markets|financial exchanges",
     "Investment Bank / Broker", "asset_management"),
    (r"consumer finance|specialized finance|mortgage finance|diversified financial",
     "Non-Bank Lender", "nbfc"),
    (r"multi.?sector holdings", "Diversified Holding Company", "nbfc"),
    (r"reinsurance", "Reinsurer", "insurance"),
    (r"insurance brokers", "Insurance Broker", "insurance"),
    (r"life and health insurance|property and casualty insurance|insurance",
     "Insurance Company", "insurance"),
    (r"transaction and payment processing", "Payments Processor", "internet_platforms"),
    # --- Energy -----------------------------------------------------------
    (r"integrated oil", "Integrated Energy Company", "oil_gas"),
    (r"oil and gas refining|refining and marketing", "Refiner and Marketer", "oil_gas"),
    (r"oil and gas exploration", "Exploration and Production Company", "oil_gas"),
    (r"oil and gas drilling|oil and gas equipment", "Oilfield Services Company", "oil_gas"),
    (r"oil and gas storage|storage and transportation", "Midstream Energy Company", "oil_gas"),
    (r"coal and consumable fuels", "Coal Producer", "mining"),
    # --- Utilities --------------------------------------------------------
    (r"electric utilities", "Electric Utility", "utilities"),
    (r"gas utilities", "Gas Utility", "utilities"),
    (r"water utilities", "Water Utility", "utilities"),
    (r"renewable electricity", "Renewable Power Producer", "renewables"),
    (r"independent power producers|energy traders", "Independent Power Producer", "power"),
    (r"multi.?utilities", "Multi-Utility", "utilities"),
    # --- Information Technology ------------------------------------------
    (r"it consulting|data processing and outsourced", "IT Services", "it_services"),
    (r"application software|systems software|internet services and infrastructure",
     "Software Company", "software"),
    (r"semiconductors|semiconductor materials", "Semiconductor Company", "capital_goods"),
    (r"technology hardware|consumer electronics|electronic manufacturing services|"
     r"electronic equipment|electronic components|communications equipment",
     "Electronics Manufacturer", "capital_goods"),
    (r"technology distributors", "Technology Distributor", "logistics"),
    # --- Communication Services ------------------------------------------
    (r"integrated telecommunication|wireless telecommunication|alternative carriers",
     "Telecom Operator", "telecom"),
    (r"movies and entertainment|broadcasting|cable and satellite|publishing|advertising|"
     r"interactive home entertainment",
     "Media Company", "media"),
    (r"interactive media and services", "Internet Platform", "internet_platforms"),
    # --- Health Care ------------------------------------------------------
    (r"health care facilities|managed health care", "Hospital Network", "hospitals"),
    (r"pharmaceuticals", "Pharmaceutical Company", "pharma"),
    (r"biotechnology", "Biotechnology Company", "pharma"),
    (r"life sciences tools", "Life Sciences Tools Provider", "diagnostics"),
    (r"health care services|health care technology", "Health Care Services Provider", "diagnostics"),
    (r"health care equipment|health care supplies|health care distributors",
     "Medical Products Company", "pharma"),
    # --- Materials --------------------------------------------------------
    (r"^steel$|steel", "Steel Producer", "metals"),
    (r"aluminum|copper|gold|precious metals|diversified metals and mining",
     "Metals and Mining Company", "metals"),
    (r"construction materials", "Cement and Construction Materials Producer", "cement"),
    (r"specialty chemicals|commodity chemicals|diversified chemicals|industrial gases",
     "Chemicals Producer", "chemicals"),
    (r"fertilizers and agricultural chemicals", "Agri-Input Producer", "chemicals"),
    (r"paper and plastic packaging|metal, glass and plastic containers|paper products|"
     r"forest products",
     "Packaging and Paper Producer", "capital_goods"),
    # --- Industrials ------------------------------------------------------
    (r"construction and engineering", "Engineering and Construction Company", "infrastructure"),
    (r"industrial conglomerates", "Industrial Conglomerate", "capital_goods"),
    (r"aerospace and defense", "Aerospace and Defence Company", "capital_goods"),
    (r"industrial machinery|construction machinery|agricultural and farm machinery|"
     r"heavy electrical equipment|electrical components",
     "Capital Goods Manufacturer", "capital_goods"),
    (r"building products", "Building Products Manufacturer", "capital_goods"),
    (r"trading companies and distributors|distributors", "Industrial Distributor", "logistics"),
    (r"passenger airlines|airlines", "Airline", "airlines"),
    (r"airport services|marine ports", "Transport Infrastructure Operator", "infrastructure"),
    (r"highways and railtracks", "Roads and Rail Infrastructure Operator", "infrastructure"),
    (r"marine transportation", "Shipping Company", "shipping"),
    (r"air freight and logistics|cargo ground transportation|rail transportation|"
     r"passenger ground transportation",
     "Logistics Company", "logistics"),
    (r"human resource and employment|research and consulting|diversified support services|"
     r"environmental and facilities|office services|commercial printing|security and alarm",
     "Business Services Company", "capital_goods"),
    # --- Consumer Discretionary ------------------------------------------
    (r"automobile manufacturers|motorcycle manufacturers", "Automobile Manufacturer", "automobile"),
    (r"automotive parts|tires and rubber", "Auto Components Manufacturer", "auto_components"),
    (r"apparel, accessories and luxury goods|footwear|textiles",
     "Apparel and Textiles Manufacturer", "consumer_durables"),
    (r"household appliances|home furnishings|housewares|leisure products|consumer electronics",
     "Consumer Durables Manufacturer", "consumer_durables"),
    (r"hotels, resorts|leisure facilities|casinos and gaming", "Hospitality Operator", "hotels"),
    (r"restaurants", "Restaurant Operator", "qsr"),
    (r"education services", "Education Provider", "education"),
    (r"apparel retail|broadline retail|other specialty retail|automotive retail|"
     r"computer and electronics retail|home improvement retail|homefurnishing retail|"
     r"specialized consumer services",
     "Retail Chain", "retail"),
    # --- Consumer Staples -------------------------------------------------
    (r"packaged foods and meats|agricultural products", "Packaged Foods Producer", "fmcg"),
    (r"personal care products|household products", "Home and Personal Care Company", "fmcg"),
    (r"distillers and vintners|brewers|soft drinks|non.?alcoholic beverages",
     "Beverages Company", "fmcg"),
    (r"tobacco", "Tobacco Company", "fmcg"),
    (r"food retail|drug retail|consumer staples merchandise retail", "Retail Chain", "retail"),
    (r"food distributors", "Food Distributor", "logistics"),
    # --- Real Estate ------------------------------------------------------
    (r"real estate development", "Real Estate Developer", "real_estate"),
    (r"real estate operating companies|diversified real estate|real estate services",
     "Real Estate Operator", "real_estate"),
    (r"reits?\b", "REIT", "real_estate"),
)

_COMPILED: tuple[tuple[re.Pattern[str], str, str], ...] = tuple(
    (re.compile(pattern, re.I), archetype, dna) for pattern, archetype, dna in _INDUSTRY_RULES
)

# Sector-level fallback when an industry label is unmapped — still never
# infers from description, only from the canonical Primary Sector.
_SECTOR_FALLBACK: dict[str, tuple[str, str]] = {
    "Financials": ("Financial Services Company", "nbfc"),
    "Energy": ("Energy Company", "oil_gas"),
    "Utilities": ("Utility", "utilities"),
    "Information Technology": ("Technology Company", "it_services"),
    "Communication Services": ("Communications Company", "telecom"),
    "Health Care": ("Health Care Company", "pharma"),
    "Materials": ("Materials Producer", "chemicals"),
    "Industrials": ("Industrial Company", "capital_goods"),
    "Consumer Discretionary": ("Consumer Discretionary Company", "consumer_durables"),
    "Consumer Staples": ("Consumer Staples Company", "fmcg"),
    "Real Estate": ("Real Estate Company", "real_estate"),
}


def classify(
    primary_industry: Optional[str],
    primary_sector: Optional[str] = None,
) -> tuple[Optional[str], Optional[str]]:
    """Return (business_type, industry_dna_key) from canonical CapIQ fields."""
    label = str(primary_industry or "").strip()
    if label:
        # CapIQ exports sometimes render an en-dash as "0" (Multi0Sector Holdings).
        normalized = label.replace("0", " ") if re.search(r"[A-Za-z]0[A-Za-z]", label) else label
        for pattern, archetype, dna in _COMPILED:
            if pattern.search(normalized):
                return archetype, dna
    sector = str(primary_sector or "").strip()
    if sector in _SECTOR_FALLBACK:
        return _SECTOR_FALLBACK[sector]
    return None, None


# ---------------------------------------------------------------------------
# Valuation frameworks and KPI dictionaries, keyed on Industry DNA
# ---------------------------------------------------------------------------
_BANK_VALUATION = ("P/B", "Residual Income", "ROE", "Cost of Equity", "NIM", "CET1")
_BANK_KPIS = (
    "CASA",
    "NIM",
    "Credit Cost",
    "GNPA",
    "NNPA",
    "PCR",
    "CET1",
    "Loan Growth",
    "Deposit Growth",
)
_OIL_VALUATION = ("EV/EBITDA", "DCF", "Production", "GRM", "Reserve Replacement", "Crack Spread")
_OIL_KPIS = ("Production", "Refining Throughput", "GRM", "Reserves", "Reserve Replacement")
_IT_VALUATION = ("EV/EBITDA", "DCF", "FCF", "Margins", "Utilization", "P/E")
_IT_KPIS = ("Utilization", "Attrition", "TCV", "Deal Wins", "Offshore Mix")
_HOSPITAL_VALUATION = ("EV/EBITDA", "ARPOB", "Occupancy", "ALOS", "DCF")
_HOSPITAL_KPIS = ("Occupancy", "ARPOB", "ALOS", "Bed Additions")
_AIRLINE_VALUATION = ("EV/EBITDAR", "RASK", "CASK", "Load Factor", "DCF")
_AIRLINE_KPIS = ("RASK", "CASK", "Load Factor", "ASK", "RPK")
_RETAIL_VALUATION = ("EV/EBITDA", "P/E", "DCF", "SSSG")
_RETAIL_KPIS = ("SSSG", "Footfall", "Basket Size", "Inventory Turns", "Store Additions")
_METALS_VALUATION = ("EV/EBITDA", "EV/tonne", "Replacement Cost", "DCF")
_METALS_KPIS = ("Capacity", "Realization", "Utilization", "Volume")
_CEMENT_VALUATION = ("EV/EBITDA", "EV/tonne", "DCF")
_CEMENT_KPIS = ("Capacity", "Realization", "Utilization", "Volume")
_INSURANCE_VALUATION = ("P/EV", "Embedded Value", "VNB Margin", "P/B", "ROEV")
_INSURANCE_KPIS = ("APE", "VNB Margin", "Persistency", "Solvency Ratio", "Combined Ratio")
_NBFC_VALUATION = ("P/B", "ROE", "Residual Income", "Cost of Equity")
_NBFC_KPIS = ("AUM Growth", "NIM", "Credit Cost", "GNPA", "Cost of Funds")
_UTILITY_VALUATION = ("Regulated RAB", "DCF", "EV/EBITDA", "P/B")
_UTILITY_KPIS = ("PLF", "Availability", "Regulated Equity", "Tariff", "T&D Losses")
_REALESTATE_VALUATION = ("NAV", "DCF", "Pre-sales Multiple")
_REALESTATE_KPIS = ("Pre-sales", "Collections", "Launches", "Inventory Overhang")
_PHARMA_VALUATION = ("EV/EBITDA", "P/E", "DCF", "Pipeline NPV")
_PHARMA_KPIS = ("ANDA Filings", "US Sales", "R&D Spend", "Price Erosion")
_GENERIC_VALUATION = ("EV/EBITDA", "DCF", "P/E", "FCF")
_GENERIC_KPIS = ("Revenue Growth", "Margins", "Return on Capital", "Cash Conversion")

_FRAMEWORKS: dict[str, tuple[tuple[str, ...], tuple[str, ...]]] = {
    "banks": (_BANK_VALUATION, _BANK_KPIS),
    "nbfc": (_NBFC_VALUATION, _NBFC_KPIS),
    "asset_management": (("P/E", "AUM Multiple", "DCF"), ("AUM", "Net Flows", "Yield on AUM")),
    "insurance": (_INSURANCE_VALUATION, _INSURANCE_KPIS),
    "oil_gas": (_OIL_VALUATION, _OIL_KPIS),
    "mining": (_METALS_VALUATION, ("Production", "Realization", "Stripping Ratio", "Reserves")),
    "metals": (_METALS_VALUATION, _METALS_KPIS),
    "cement": (_CEMENT_VALUATION, _CEMENT_KPIS),
    "chemicals": (_GENERIC_VALUATION, ("Capacity", "Realization", "Spreads", "Utilization")),
    "it_services": (_IT_VALUATION, _IT_KPIS),
    "software": (("EV/Sales", "Rule of 40", "DCF", "EV/EBITDA"), ("ARR", "NRR", "Churn", "CAC Payback")),
    "internet_platforms": (("EV/Sales", "GMV Multiple", "DCF"), ("GMV", "Take Rate", "MAU", "Contribution Margin")),
    "telecom": (("EV/EBITDA", "DCF", "EV/Subscriber"), ("ARPU", "Subscribers", "Churn", "Data Usage")),
    "media": (("EV/EBITDA", "P/E", "DCF"), ("Ad Revenue", "Subscribers", "Viewership")),
    "hospitals": (_HOSPITAL_VALUATION, _HOSPITAL_KPIS),
    "pharma": (_PHARMA_VALUATION, _PHARMA_KPIS),
    "diagnostics": (("EV/EBITDA", "P/E", "DCF"), ("Test Volumes", "Realization per Test", "Network Reach")),
    "airlines": (_AIRLINE_VALUATION, _AIRLINE_KPIS),
    "logistics": (("EV/EBITDA", "DCF", "P/E"), ("Tonnage", "Yield", "Fleet Utilization")),
    "shipping": (("EV/EBITDA", "NAV", "DCF"), ("Freight Rates", "Fleet Utilization", "TCE")),
    "infrastructure": (("EV/EBITDA", "DCF", "Project IRR"), ("Order Book", "Execution", "Book-to-Bill")),
    "capital_goods": (("EV/EBITDA", "P/E", "DCF"), ("Order Book", "Book-to-Bill", "Execution", "Margins")),
    "automobile": (("EV/EBITDA", "P/E", "DCF"), ("Volumes", "Realization", "Market Share", "Discounts")),
    "auto_components": (("EV/EBITDA", "P/E", "DCF"), ("Content per Vehicle", "Volumes", "Utilization")),
    "consumer_durables": (("P/E", "EV/EBITDA", "DCF"), ("Volumes", "Realization", "Distribution Reach")),
    "retail": (_RETAIL_VALUATION, _RETAIL_KPIS),
    "qsr": (("EV/EBITDA", "DCF", "P/E"), ("SSSG", "Store Additions", "Average Daily Sales")),
    "fmcg": (("P/E", "EV/EBITDA", "DCF"), ("Volume Growth", "Gross Margin", "Distribution Reach", "Ad Spend")),
    "hotels": (("EV/EBITDA", "EV/Key", "DCF"), ("Occupancy", "ARR", "RevPAR")),
    "power": (_UTILITY_VALUATION, _UTILITY_KPIS),
    "utilities": (_UTILITY_VALUATION, _UTILITY_KPIS),
    "renewables": (_UTILITY_VALUATION, ("PLF", "Capacity", "PPA Tariff", "Curtailment")),
    "real_estate": (_REALESTATE_VALUATION, _REALESTATE_KPIS),
    "education": (("EV/EBITDA", "P/E", "DCF"), ("Enrolment", "Fee Realization", "Capacity Utilization")),
    "agriculture": (("EV/EBITDA", "P/E", "DCF"), ("Acreage", "Realization", "Yield")),
    "data_centers": (("EV/EBITDA", "EV/MW", "DCF"), ("Capacity MW", "Utilization", "Churn")),
}

# KPI / valuation vocabulary that is exclusive to one DNA family. Presence of a
# term outside its owning family is a cross-industry leak.
_EXCLUSIVE_TERMS: dict[str, tuple[str, ...]] = {
    "banks": ("casa", "gnpa", "nnpa", "cet1", "nim", "provision coverage"),
    "oil_gas": (
        "grm",
        "gross refining margin",
        "reserve replacement",
        "crack spread",
        "refining complexity",
    ),
    # "load factor" is deliberately absent: airlines measure passenger load
    # factor and power producers measure plant load factor (PLF).
    # "occupancy" likewise belongs to hospitals, hotels and real estate alike.
    "airlines": ("rask", "cask", "rpk", "ev/ebitdar"),
    "hospitals": ("arpob", "alos"),
    "it_services": ("offshore mix", "attrition"),
    "retail": ("sssg", "same-store sales", "footfall", "basket size"),
    "insurance": ("embedded value", "vnb margin", "persistency", "combined ratio"),
    "telecom": ("arpu",),
    "real_estate": ("pre-sales", "inventory overhang"),
}

# DNA families that legitimately share vocabulary (no leak between them).
# Declared as groups so the relation is symmetric by construction — an
# asymmetric table let FMCG names be flagged for using retail's SSSG.
_ALLY_GROUPS: tuple[frozenset[str], ...] = (
    # Lending economics — CASA / NIM / GNPA / CET1
    frozenset({"banks", "nbfc", "asset_management"}),
    # Hydrocarbon economics — GRM / reserves / crack spread
    frozenset({"oil_gas", "mining"}),
    # Bed economics — ARPOB / ALOS
    frozenset({"hospitals", "diagnostics"}),
    # Store economics — SSSG / footfall / basket size
    frozenset({"retail", "qsr", "fmcg", "consumer_durables", "hotels"}),
    # Delivery economics — utilization / attrition / offshore mix
    frozenset({"it_services", "software"}),
    # Subscriber economics — ARPU
    frozenset({"telecom", "media", "internet_platforms"}),
    # Project economics — pre-sales / inventory overhang
    frozenset({"real_estate", "infrastructure"}),
    frozenset({"power", "utilities", "renewables"}),
)


def _allies_for(dna: str) -> frozenset[str]:
    allies = {dna}
    for group in _ALLY_GROUPS:
        if dna in group:
            allies |= set(group)
    return frozenset(allies)


_TERM_ALLIES: dict[str, frozenset[str]] = {
    dna: _allies_for(dna) for group in _ALLY_GROUPS for dna in group
}


def framework_for(industry_dna: Optional[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (allowed_valuation_methods, kpis) for a DNA key."""
    if not industry_dna:
        return _GENERIC_VALUATION, _GENERIC_KPIS
    return _FRAMEWORKS.get(industry_dna, (_GENERIC_VALUATION, _GENERIC_KPIS))


def forbidden_for(industry_dna: Optional[str]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Return (forbidden_valuation_terms, forbidden_kpis) for a DNA key."""
    if not industry_dna:
        return (), ()
    allies = _TERM_ALLIES.get(industry_dna, frozenset({industry_dna}))
    forbidden: list[str] = []
    for owner, terms in _EXCLUSIVE_TERMS.items():
        if owner in allies:
            continue
        forbidden.extend(terms)
    # EV/EBITDA is meaningless for banks — treat as a valuation leak.
    if industry_dna in {"banks", "insurance"}:
        forbidden.extend(["ev/ebitda", "ev/ebitdar", "ev/sales"])
    return tuple(sorted(set(forbidden))), tuple(sorted(set(forbidden)))


def owning_family(term: str) -> Optional[str]:
    """Which DNA family exclusively owns this term, if any."""
    t = term.strip().lower()
    for owner, terms in _EXCLUSIVE_TERMS.items():
        if t in terms:
            return owner
    return None
