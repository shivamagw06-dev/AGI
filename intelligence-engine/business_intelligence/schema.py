"""FIRE-03 — Business & Management Intelligence contracts."""

from __future__ import annotations

WORKSTREAM_ID = "FIRE-03"
PROGRAMME = "AGIB_FINANCIAL_INTELLIGENCE_REASONING_ENGINE"
SUBSYSTEM = "business_management_intelligence"
VERSION = "fire-03-v1.0.0"
PHASE = "phase_3"
SPEC = "docs/FIRE_03_BUSINESS_MANAGEMENT_INTELLIGENCE.md"

ISSUES_RECOMMENDATIONS = False
RECOMMENDATION_POLICY = "evidence_backed_disclosure_extraction_only_no_buy_sell"

CONF_HIGH = "High"
CONF_MEDIUM = "Medium"
CONF_LOW = "Low"

# Fact categories
CAT_BUSINESS_DESCRIPTION = "Business Description"
CAT_PRODUCTS = "Products"
CAT_SERVICES = "Services"
CAT_OPERATING_MODEL = "Operating Model"
CAT_REVENUE_MODEL = "Revenue Model"
CAT_SEGMENTS = "Business Segments"
CAT_GEOGRAPHY = "Geographic Exposure"
CAT_CUSTOMERS = "Customer Profile"
CAT_DISTRIBUTION = "Distribution Channels"
CAT_SUPPLY_CHAIN = "Supply Chain"
CAT_SEGMENT_ANALYSIS = "Segment Analysis"
CAT_GROWTH_STRATEGY = "Growth Strategy"
CAT_EXPANSION = "Expansion Plans"
CAT_COST_OPTIMISATION = "Cost Optimisation"
CAT_DIGITAL = "Digital Initiatives"
CAT_CAPACITY = "Capacity Expansion"
CAT_PRODUCT_LAUNCH = "Product Launches"
CAT_ACQUISITION = "Acquisitions"
CAT_DIVESTITURE = "Divestitures"
CAT_CAPEX = "Capital Expenditure"
CAT_DEBT_REDUCTION = "Debt Reduction"
CAT_BUYBACKS = "Buybacks"
CAT_DIVIDENDS = "Dividends"
CAT_LIQUIDITY = "Liquidity"
CAT_CASH_DEPLOYMENT = "Cash Deployment"
CAT_INVESTMENT_PRIORITIES = "Investment Priorities"
CAT_RISK = "Risk"
CAT_OPPORTUNITY = "Opportunity"
CAT_GUIDANCE_REVENUE = "Revenue Guidance"
CAT_GUIDANCE_MARGIN = "Margin Guidance"
CAT_GUIDANCE_CAPEX = "Capex Guidance"
CAT_GUIDANCE_DEMAND = "Demand Outlook"
CAT_GUIDANCE_INDUSTRY = "Industry Outlook"
CAT_GUIDANCE_COST = "Cost Outlook"
CAT_GOVERNANCE = "Governance"

FACT_CATEGORIES = (
    CAT_BUSINESS_DESCRIPTION,
    CAT_PRODUCTS,
    CAT_SERVICES,
    CAT_OPERATING_MODEL,
    CAT_REVENUE_MODEL,
    CAT_SEGMENTS,
    CAT_GEOGRAPHY,
    CAT_CUSTOMERS,
    CAT_DISTRIBUTION,
    CAT_SUPPLY_CHAIN,
    CAT_SEGMENT_ANALYSIS,
    CAT_GROWTH_STRATEGY,
    CAT_EXPANSION,
    CAT_COST_OPTIMISATION,
    CAT_DIGITAL,
    CAT_CAPACITY,
    CAT_PRODUCT_LAUNCH,
    CAT_ACQUISITION,
    CAT_DIVESTITURE,
    CAT_CAPEX,
    CAT_DEBT_REDUCTION,
    CAT_BUYBACKS,
    CAT_DIVIDENDS,
    CAT_LIQUIDITY,
    CAT_CASH_DEPLOYMENT,
    CAT_INVESTMENT_PRIORITIES,
    CAT_RISK,
    CAT_OPPORTUNITY,
    CAT_GUIDANCE_REVENUE,
    CAT_GUIDANCE_MARGIN,
    CAT_GUIDANCE_CAPEX,
    CAT_GUIDANCE_DEMAND,
    CAT_GUIDANCE_INDUSTRY,
    CAT_GUIDANCE_COST,
    CAT_GOVERNANCE,
)

# BIR sections (ordered)
REPORT_SECTIONS = (
    "executive_summary",
    "business_model",
    "products_and_services",
    "revenue_model",
    "segment_analysis",
    "geographic_footprint",
    "management_strategy",
    "capital_allocation",
    "risk_register",
    "opportunity_register",
    "management_guidance",
    "governance_highlights",
    "source_references",
)

# Official document type priority (lower = higher priority)
DOC_TYPE_PRIORITY: dict[str, int] = {
    "ANNUAL_REPORT": 1,
    "MANAGEMENT_COMMENTARY": 2,
    "SEGMENT_REPORT": 3,
    "RISK_DISCLOSURE": 4,
    "CORPORATE_GOVERNANCE_REPORT": 5,
    "INVESTOR_PRESENTATION": 6,
    "QUARTERLY_REPORT": 7,
    "CONFERENCE_CALL_TRANSCRIPT": 8,
    "EXCHANGE_FILING": 9,
    "NOTES_TO_ACCOUNTS": 10,
    "ESG_REPORT": 11,
}

# Section → preferred confidence floor
SECTION_CONFIDENCE: dict[str, str] = {
    "MANAGEMENT_DISCUSSION": CONF_HIGH,
    "STRATEGY": CONF_HIGH,
    "RISK_FACTORS": CONF_HIGH,
    "BUSINESS_SEGMENTS": CONF_HIGH,
    "CAPITAL_ALLOCATION": CONF_HIGH,
    "GUIDANCE": CONF_MEDIUM,
    "NOTES": CONF_MEDIUM,
    "FINANCIAL_STATEMENTS": CONF_MEDIUM,
    "TABLES": CONF_MEDIUM,
    "OTHER": CONF_LOW,
}

# Pack names exposed to consumers
PACK_BUSINESS_PROFILE = "BusinessProfile"
PACK_MANAGEMENT_STRATEGY = "ManagementStrategy"
PACK_SEGMENT_ANALYSIS = "SegmentAnalysis"
PACK_RISK_REGISTER = "RiskRegister"
PACK_OPPORTUNITY_REGISTER = "OpportunityRegister"
PACK_GUIDANCE_SUMMARY = "GuidanceSummary"
PACK_CAPITAL_ALLOCATION = "CapitalAllocationNarrative"

OUTPUT_PACKS = (
    PACK_BUSINESS_PROFILE,
    PACK_MANAGEMENT_STRATEGY,
    PACK_SEGMENT_ANALYSIS,
    PACK_RISK_REGISTER,
    PACK_OPPORTUNITY_REGISTER,
    PACK_GUIDANCE_SUMMARY,
    PACK_CAPITAL_ALLOCATION,
)

PROFILE_CATEGORIES = frozenset(
    {
        CAT_BUSINESS_DESCRIPTION,
        CAT_PRODUCTS,
        CAT_SERVICES,
        CAT_OPERATING_MODEL,
        CAT_REVENUE_MODEL,
        CAT_SEGMENTS,
        CAT_GEOGRAPHY,
        CAT_CUSTOMERS,
        CAT_DISTRIBUTION,
        CAT_SUPPLY_CHAIN,
    }
)

STRATEGY_CATEGORIES = frozenset(
    {
        CAT_GROWTH_STRATEGY,
        CAT_EXPANSION,
        CAT_COST_OPTIMISATION,
        CAT_DIGITAL,
        CAT_CAPACITY,
        CAT_PRODUCT_LAUNCH,
        CAT_ACQUISITION,
        CAT_DIVESTITURE,
        CAT_CAPEX,
        CAT_DEBT_REDUCTION,
    }
)

CAPITAL_CATEGORIES = frozenset(
    {
        CAT_CAPEX,
        CAT_BUYBACKS,
        CAT_DIVIDENDS,
        CAT_DEBT_REDUCTION,
        CAT_LIQUIDITY,
        CAT_CASH_DEPLOYMENT,
        CAT_INVESTMENT_PRIORITIES,
    }
)

GUIDANCE_CATEGORIES = frozenset(
    {
        CAT_GUIDANCE_REVENUE,
        CAT_GUIDANCE_MARGIN,
        CAT_GUIDANCE_CAPEX,
        CAT_GUIDANCE_DEMAND,
        CAT_GUIDANCE_INDUSTRY,
        CAT_GUIDANCE_COST,
    }
)
