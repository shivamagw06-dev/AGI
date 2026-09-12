"""Module 5 — Cash Flow Concepts."""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "cash_flow"

CASH_FLOW_CONCEPTS: dict[str, ConceptCard] = {
    "owner_earnings": ConceptCard(
        "owner_earnings", M, "Owner Earnings",
        "A concept popularized by Warren Buffett: reported earnings adjusted to reflect the actual cash an owner could extract from the business without impairing its competitive position.",
        formula="Owner Earnings ≈ Net Income + Depreciation & Amortization − Maintenance Capex − Working Capital Increases",
        business_meaning="Deliberately differs from GAAP earnings and even from simple Free Cash Flow by isolating maintenance (not growth) capex — it asks 'what could the owner take out every year forever, unchanged'.",
        interpretation="A business with owner earnings well below reported Net Income is quietly consuming more cash to sustain itself than the income statement suggests.",
        common_mistakes="Using total capex instead of maintenance capex — this understates owner earnings for a business that is also investing meaningfully in growth.",
        related_concepts=("free_cash_flow", "maintenance_capex", "fcf_yield"),
    ),
    "free_cash_flow": ConceptCard(
        "free_cash_flow", M, "Free Cash Flow (FCF)",
        "The cash a business generates after covering the capital expenditure needed to maintain and grow its operations — cash available to all capital providers (or to equity holders, depending on definition).",
        formula="FCF = Operating Cash Flow − Capital Expenditure",
        business_meaning="FCF is what ultimately funds dividends, buybacks, debt paydown, and further investment — accounting profit that never becomes FCF cannot fund any of those things.",
        interpretation="Persistently positive and growing FCF alongside growing profit is the clearest sign of a healthy, self-funding business; profit growing while FCF stagnates or falls warrants investigation into capex intensity or working capital.",
        related_concepts=("levered_fcf", "unlevered_fcf", "owner_earnings", "fcf_yield", "fcf_conversion"),
    ),
    "unlevered_fcf": ConceptCard(
        "unlevered_fcf", M, "Unlevered Free Cash Flow (FCFF)",
        "Free cash flow available to ALL capital providers — both debt and equity holders — before any interest payments or debt principal repayment.",
        formula="Unlevered FCF = NOPAT + D&A − Capex − Increase in Working Capital",
        business_meaning="This is the cash flow discounted at WACC in an Enterprise-Value DCF, because it belongs to the whole capital structure, not just equity.",
        interpretation="Unlevered FCF isolates operating cash generation from financing decisions, making it the right basis for comparing companies with very different debt levels.",
        related_concepts=("free_cash_flow", "levered_fcf", "dcf", "wacc", "nopat"),
    ),
    "levered_fcf": ConceptCard(
        "levered_fcf", M, "Levered Free Cash Flow (FCFE)",
        "Free cash flow available specifically to equity holders, after all interest payments and net debt repayment/issuance.",
        formula="Levered FCF = Unlevered FCF − Interest Expense × (1 − Tax Rate) − Net Debt Repayment",
        business_meaning="This is the cash flow actually available to fund dividends and buybacks, or to be discounted at the cost of equity in an equity-value DCF.",
        interpretation="Levered FCF can be negative even when unlevered FCF is healthy, if the company is aggressively repaying debt — this is a capital-allocation choice, not necessarily distress.",
        related_concepts=("unlevered_fcf", "free_cash_flow", "cost_of_equity"),
    ),
    "working_capital_release": ConceptCard(
        "working_capital_release", M, "Working Capital Release",
        "Cash freed up when working capital (receivables + inventory − payables) shrinks — typically during a demand slowdown or a deliberate efficiency drive.",
        business_meaning="Can flatter cash flow temporarily: a company can show strong cash generation even with falling revenue, purely because it is running down inventory and collecting old receivables.",
        interpretation="Cash flow boosted mainly by working capital release is not sustainable — once working capital normalizes (or the business grows again), that cash tailwind reverses.",
        related_concepts=("working_capital", "working_capital_absorption", "cash_conversion_cycle"),
    ),
    "working_capital_absorption": ConceptCard(
        "working_capital_absorption", M, "Working Capital Absorption",
        "Cash consumed when working capital grows — typically alongside revenue growth, as more inventory and receivables are needed to support a larger business.",
        business_meaning="Fast-growing companies often show strong accounting profit growth alongside weak (or negative) operating cash flow purely because growth itself absorbs cash into working capital.",
        interpretation="Working capital absorption tied to genuine, profitable growth is healthy and temporary; absorption growing faster than revenue for several periods in a row signals a structural efficiency problem.",
        related_concepts=("working_capital", "working_capital_release", "receivable_days"),
    ),
    "capex_intensity": ConceptCard(
        "capex_intensity", M, "Capex Intensity",
        "Capital expenditure expressed as a percentage of revenue — a headline measure of how capital-hungry a business model is.",
        formula="Capex Intensity = Capital Expenditure / Revenue",
        business_meaning="High capex-intensity businesses (telecom, semiconductors, utilities, airlines) must reinvest continuously just to maintain competitive position, leaving less free cash flow per dollar of revenue than asset-light peers.",
        interpretation="Rising capex intensity without a corresponding acceleration in revenue growth or incremental ROIC signals deteriorating capital efficiency.",
        related_concepts=("capital_intensity", "maintenance_capex", "growth_capex", "fcf_conversion"),
    ),
    "cash_burn": ConceptCard(
        "cash_burn", M, "Cash Burn",
        "The rate at which a company is depleting its cash reserves, typically used for pre-profitability or loss-making growth companies.",
        formula="Cash Burn Rate = Cash Used in Operations (+ Investing) over a period, usually expressed monthly or quarterly",
        business_meaning="Directly determines how long a company can continue operating before it must raise additional capital or reach profitability.",
        interpretation="An accelerating burn rate against a fixed cash balance is an urgent solvency signal, regardless of how impressive revenue growth looks.",
        related_concepts=("runway", "free_cash_flow"),
    ),
    "runway": ConceptCard(
        "runway", M, "Runway",
        "How many months or years a company can continue operating at its current cash-burn rate before running out of cash.",
        formula="Runway (months) = Current Cash Balance / Monthly Cash Burn Rate",
        business_meaning="A core solvency metric for growth-stage or loss-making companies — short runway forces near-term capital raises, often on unfavorable, dilutive terms.",
        interpretation="Runway shrinking faster than a company's path to profitability is closing is the single clearest early-warning signal for growth-company investors.",
        related_concepts=("cash_burn", "free_cash_flow"),
    ),
    "cash_flow_coverage_ratio": ConceptCard(
        "cash_flow_coverage_ratio", M, "Cash Flow Coverage Ratio",
        "How many times over a company's operating cash flow could cover its total debt obligations.",
        formula="Cash Flow Coverage Ratio = Operating Cash Flow / Total Debt",
        business_meaning="A cash-flow-based solvency check that complements earnings-based interest coverage, since cash flow (not accounting earnings) is what actually services debt.",
        interpretation="A low or declining ratio, even alongside healthy accounting profit, signals rising refinancing and default risk.",
        related_concepts=("debt_service_coverage", "interest_coverage", "refinancing_risk"),
    ),
}
