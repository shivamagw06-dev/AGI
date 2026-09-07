"""Phase 2A IT Services institutional curriculum."""
from __future__ import annotations

from financials_valuation.schema import KPIKnowledge, SectorValuationModel, ValuationMethodRule

TECHNOLOGY_VALUATION_VERSION = "technology-valuation-v2a.0.0"
TECHNOLOGY_PARENT_SECTOR = "TECHNOLOGY_AND_DIGITAL"
IT_SERVICES_SUBSECTOR = "IT_SERVICES"


def _k(key: str, name: str, definition: str, formula: str, unit: str, why: str,
       causal: tuple[str, ...], valuation: str, limitations: str) -> KPIKnowledge:
    return KPIKnowledge(key, name, definition, formula, unit, "Quarterly/Annual",
        ("Regulatory filing", "NSE/BSE filing", "Audited financial statements", "Official company disclosure"),
        why, causal, valuation, limitations, ("VALIDATED", "TRUSTED"))


def _m(method: str, tier: str, reason: str, required: tuple[str, ...], failure: tuple[str, ...]) -> ValuationMethodRule:
    return ValuationMethodRule(method, tier, reason, required, (reason,),
        ("Sensitive to normalization, durability and point-in-time assumptions.",), failure)


IT_SERVICES_KPIS = (
    _k("revenue_growth", "Revenue Growth", "Reported revenue change, separated into volume, price, mix, currency and acquisitions.", "(revenue / prior revenue) - 1", "decimal", "Measures demand conversion, not demand quality by itself.", ("client spending -> deal conversion -> revenue",), "Growth durability affects earnings and multiples.", "Currency, acquisitions and a low base can obscure organic growth."),
    _k("constant_currency_growth", "Constant-Currency Growth", "Revenue growth excluding reported currency translation.", "company disclosed or validated currency bridge", "decimal", "Separates operating demand from translation.", ("client demand -> constant-currency revenue",), "Supports comparable growth expectations.", "Company methodologies can differ."),
    _k("headcount", "Headcount", "Period-end employees in the relevant delivery scope.", "reported headcount", "employees", "Represents delivery capacity and the principal cost base.", ("headcount x utilization x billing rate -> revenue capacity",), "Capacity and cost discipline influence margins.", "Scope, contractors and acquisitions may differ."),
    _k("utilization", "Utilization", "Billable delivery capacity divided by available delivery capacity.", "billable capacity / available capacity", "decimal", "Connects demand to employee productivity and margins.", ("demand -> utilization -> operating leverage",), "Sustainable utilization supports EBIT margin.", "Reported with or without trainees; definitions vary."),
    _k("billing_rate", "Billing Rate", "Realized revenue per billed delivery unit.", "service revenue / billed units", "currency_per_unit", "Captures pricing, mix and client bargaining power.", ("pricing and mix -> billing rate -> revenue",), "Pricing durability supports earnings quality.", "Often inferred; geography and service mix matter."),
    _k("revenue_per_employee", "Revenue per Employee", "Revenue divided by average headcount.", "revenue / average headcount", "currency_per_employee", "A productivity bridge across delivery and mix.", ("utilization and billing rate -> revenue per employee",), "Productivity affects incremental margins.", "Currency, subcontracting and onsite mix limit comparisons."),
    _k("attrition", "Attrition", "Employee departures relative to the relevant workforce.", "company disclosed attrition", "decimal", "High attrition can raise hiring, wage and delivery costs.", ("attrition -> replacement cost -> margin",), "Persistent attrition weakens margin durability.", "Definitions and trailing periods differ."),
    _k("tcv", "Total Contract Value", "Value of signed contracts under the disclosed convention.", "reported signed contract value", "currency", "Provides a forward demand indicator.", ("deal wins -> conversion schedule -> revenue",), "Backlog quality informs growth visibility.", "TCV is not revenue; renewals and pass-throughs may be included."),
    _k("book_to_bill", "Book-to-Bill", "Contract value signed divided by comparable-period revenue.", "TCV / revenue", "multiple", "Compares bookings with current delivery scale.", ("book-to-bill -> future revenue visibility",), "Can support or challenge forecast growth.", "Duration, renewals and conversion timing limit comparability."),
    _k("client_concentration", "Client Concentration", "Revenue share from the largest clients.", "large-client revenue / revenue", "decimal", "Measures bargaining and renewal exposure.", ("client loss -> revenue and utilization",), "Concentration raises required return and scenario risk.", "Disclosure buckets differ."),
    _k("ebit_margin", "EBIT Margin", "Operating profit divided by revenue.", "EBIT / revenue", "decimal", "Captures pricing, utilization, wages, delivery mix and overhead.", ("utilization, pricing, wages and mix -> EBIT margin",), "Margin durability drives EPS, FCF and valuation.", "Restructuring and acquisitions require normalization."),
    _k("fcf_margin", "FCF Margin", "Free cash flow divided by revenue.", "FCF / revenue", "decimal", "Tests whether accounting earnings convert to cash.", ("EBIT -> tax -> working capital -> capex -> FCF",), "Cash conversion supports DCF and valuation quality.", "Acquisitions and one-time working-capital movements distort periods."),
    _k("roic", "ROIC", "Normalized after-tax operating profit relative to invested capital.", "NOPAT / average invested capital", "decimal", "Tests whether growth creates economic value.", ("margin and capital efficiency -> ROIC",), "Sustained excess returns support durability.", "Goodwill and capitalized development require consistent treatment."),
)

IT_SERVICES_METHODS = (
    _m("TECH_PRICE_TO_EARNINGS", "PRIMARY", "Normalized P/E fits mature, profitable, capital-light IT-services earnings.", ("market_price", "normalized_eps"), ("Negative or unnormalized earnings", "Material acquisition distortion")),
    _m("EV_EBITDA", "PRIMARY_CROSS_CHECK", "EV/EBITDA cross-checks capital structure and operating profit.", ("enterprise_value", "ebitda"), ("Non-comparable lease or acquisition accounting",)),
    _m("GORDON_DCF", "SECONDARY", "DCF connects sustainable FCF, reinvestment and growth durability.", ("next_fcf", "discount_rate", "terminal_growth"), ("Unstable cash flow", "Discount rate not above terminal growth")),
    _m("FCF_YIELD", "SECONDARY", "FCF yield tests cash support for the quoted price.", ("fcf_per_share", "market_price"), ("One-time working-capital distortion",)),
    _m("PEG", "SUPPLEMENTARY_ONLY", "PEG may frame price paid for growth but cannot replace cash-flow and durability analysis.", (), ("Used as a primary valuation method",)),
)

IT_SERVICES_MODEL = SectorValuationModel(
    sector_id="TECHNOLOGY_AND_DIGITAL.IT_SERVICES", sector_name="IT Services", subsector=IT_SERVICES_SUBSECTOR,
    business_model_types=("IT Services", "IT Consulting", "BPM / Digital Services"),
    economic_structure="Employees and subcontractors convert client contracts into billed delivery. Utilization, billing rates, delivery mix, wages and currency determine margins; working capital and modest capex determine free cash flow.",
    revenue_drivers=("Enterprise IT spending", "Deal wins and renewals", "TCV conversion", "Utilization", "Billing rates", "Service and geography mix", "Currency", "Acquisitions"),
    cost_drivers=("Employee compensation", "Attrition and replacement", "Subcontracting", "Onsite/offshore mix", "Hiring and bench", "SG&A", "Currency hedging"),
    capital_structure="Usually capital-light and cash generative; acquisitions, leases, buybacks and working capital still affect equity value.",
    regulatory_characteristics=("Data privacy", "Cybersecurity", "Labour and immigration", "Client-industry regulation", "Tax and transfer pricing"),
    key_kpis=IT_SERVICES_KPIS, valuation_methods=IT_SERVICES_METHODS,
    valuation_drivers=("Organic constant-currency growth", "Utilization", "Billing rates", "EBIT margin", "FCF conversion", "ROIC", "Client concentration", "Growth durability", "AI net impact"),
    valuation_risks=("Discretionary spending slowdown", "Pricing pressure", "Client concentration", "Wage inflation", "Attrition", "Currency", "AI cannibalization", "Acquisition accounting"),
    scenario_variables=("Revenue growth", "Utilization", "Billing rate", "EBIT margin", "Tax rate", "FCF margin", "Target P/E"),
    monitoring_variables=("Deal wins and TCV", "Book-to-bill", "Constant-currency growth", "Utilization", "Attrition", "Headcount", "Large-client growth", "EBIT margin", "FCF conversion", "AI pricing evidence"),
    common_analytical_errors=("Treating TCV as revenue", "Assuming revenue growth expands margins", "Treating currency growth as organic", "Assuming AI is automatically positive", "Ignoring client concentration", "Using historical average P/E as fair value"),
    evidence_sources=("Regulatory filings", "Audited annual reports", "NSE", "BSE", "Official results", "Investor presentations", "Licensed earnings transcripts"),
    effective_date="2026-08-15", confidence=.90, validation_status="VALIDATED", version=TECHNOLOGY_VALUATION_VERSION,
)
