"""Extended Module — Reporting Metrics & Market-Convention Terms.

Additional legitimate, widely-used institutional vocabulary that analysts
encounter daily in earnings releases and management commentary — extends
Modules 1/2/6 without duplicating financial_foundations or
financial_statement_intelligence's existing metric coverage.
"""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "ratio_intelligence"

REPORTING_METRICS_CONCEPTS: dict[str, ConceptCard] = {
    "return_on_sales": ConceptCard(
        "return_on_sales", M, "Return on Sales (ROS)",
        "Operating profit expressed as a percentage of revenue — another name for operating margin, framed as a 'return' metric.",
        formula="Return on Sales = Operating Income / Revenue",
        business_meaning="Measures how much operating profit is generated per dollar of sales, independent of capital structure or asset base.",
        related_concepts=("contribution_margin",),
    ),
    "fixed_asset_turnover": ConceptCard(
        "fixed_asset_turnover", M, "Fixed Asset Turnover",
        "How efficiently a company generates revenue from its fixed (property, plant & equipment) asset base specifically, rather than total assets.",
        formula="Fixed Asset Turnover = Revenue / Net Fixed Assets (PP&E)",
        business_meaning="Particularly relevant for capital-intensive manufacturing and infrastructure businesses, where fixed assets dominate the balance sheet.",
        interpretation="A rising fixed asset turnover as a company matures past a heavy capex phase signals improving utilization of prior investment.",
        related_concepts=("asset_turnover", "capital_intensity", "capex_intensity"),
    ),
    "croci": ConceptCard(
        "croci", M, "CROCI (Cash Return on Capital Invested)",
        "A cash-flow-based capital-efficiency measure comparing gross cash flow to the gross (undepreciated) capital invested in a business.",
        formula="CROCI = Gross Cash Flow / Gross Invested Capital",
        business_meaning="Avoids distortions from differing depreciation policies and asset ages across companies by using gross (not net-of-depreciation) capital in the denominator.",
        related_concepts=("roic", "invested_capital"),
    ),
    "rote": ConceptCard(
        "rote", M, "ROTE (Return on Tangible Equity)",
        "Net income expressed as a percentage of tangible book value (equity minus goodwill/intangibles) — commonly used for banks and financial institutions.",
        formula="ROTE = Net Income / Average Tangible Common Equity",
        business_meaning="A more conservative, 'real capital' return measure than plain ROE for banks that have grown through acquisitions and carry meaningful goodwill on the balance sheet.",
        related_concepts=("roe_decomposition", "tangible_book", "p_b"),
    ),
    "days_working_capital": ConceptCard(
        "days_working_capital", M, "Days Working Capital",
        "The number of days of revenue tied up in net working capital, a single summary measure related to the Cash Conversion Cycle.",
        business_meaning="A single-number summary of working-capital intensity, useful for tracking trend direction over time without decomposing into inventory/receivable/payable days separately.",
        formula="Days Working Capital = (Net Working Capital / Revenue) × 365",
        related_concepts=("cash_conversion_cycle", "working_capital"),
    ),
    "adjusted_ebitda": ConceptCard(
        "adjusted_ebitda", M, "Adjusted EBITDA",
        "EBITDA further adjusted by management to exclude items deemed one-off or non-representative — stock-based compensation, restructuring, litigation costs, and similar items.",
        business_meaning="Frequently used in credit agreements and management guidance, but is a non-standardized, company-defined metric that can vary significantly in what it excludes.",
        interpretation="Always compare Adjusted EBITDA back to reported EBITDA/Net Income and scrutinize the size and recurrence of the adjustments before relying on it.",
        related_concepts=("non_gaap_adjustments",),
    ),
    "ltm_ntm": ConceptCard(
        "ltm_ntm", M, "LTM / NTM (Last Twelve Months / Next Twelve Months)",
        "LTM aggregates a company's most recent four reported quarters into a rolling annual figure; NTM projects the next four quarters forward — both used to avoid the distortion of comparing a single fiscal year cut at an arbitrary point.",
        business_meaning="LTM multiples are grounded in actual reported results; NTM multiples embed forward estimates and are more sensitive to the accuracy of analyst forecasts.",
        related_concepts=("ev_ebitda", "p_e"),
    ),
    "run_rate": ConceptCard(
        "run_rate", M, "Run-Rate",
        "An annualized estimate of future performance based on extrapolating a recent, shorter period (a quarter or a month) forward.",
        business_meaning="Useful for fast-changing businesses where the most recent period is more representative of the current state than trailing full-year figures, but can overstate or understate true annual performance if the recent period was unusually strong or weak (seasonality, one-offs).",
        common_mistakes="Annualizing a seasonally strong quarter without adjusting for seasonality, overstating the true run-rate.",
        related_concepts=("ltm_ntm",),
    ),
    "same_store_sales": ConceptCard(
        "same_store_sales", M, "Same-Store Sales (Like-for-Like Growth)",
        "Revenue growth measured only across stores/units that have been open for a full comparable period in both years, excluding the effect of new store openings or closures.",
        business_meaning="Isolates organic demand growth at existing locations from growth that is purely mechanical (simply having more stores) — critical for retail, restaurant, and hospitality analysis.",
        interpretation="A retailer can show strong total revenue growth purely from aggressive new-store expansion while same-store sales are flat or declining — a sign that the core existing business is not actually growing organically.",
        related_concepts=("organic_growth",),
    ),
    "organic_growth": ConceptCard(
        "organic_growth", M, "Organic Growth",
        "Revenue growth generated from a company's existing operations — volume, pricing, and mix — excluding the effect of acquisitions, divestitures, and currency translation.",
        business_meaning="The cleanest measure of a business's genuine underlying demand and competitive performance, stripped of growth simply purchased via M&A.",
        interpretation="A company relying heavily on inorganic (acquired) growth to sustain its headline growth rate faces a structurally harder path once acquisition targets or capital become scarce.",
        related_concepts=("inorganic_growth", "same_store_sales", "constant_currency"),
    ),
    "inorganic_growth": ConceptCard(
        "inorganic_growth", M, "Inorganic Growth",
        "Revenue or earnings growth achieved through mergers and acquisitions, rather than from the existing business's own operations.",
        business_meaning="Can accelerate scale and capability quickly, but its value-creation depends entirely on paying a sensible price and successfully integrating the acquired business (see Acquisition Returns).",
        related_concepts=("organic_growth", "acquisition_returns"),
    ),
    "constant_currency": ConceptCard(
        "constant_currency", M, "Constant Currency (Growth)",
        "Revenue or earnings growth restated using a fixed exchange rate from a prior period, removing the distorting effect of currency fluctuations for companies with significant foreign operations.",
        business_meaning="Lets analysts see the genuine underlying business growth trend, separate from purely mechanical translation gains or losses from a strengthening or weakening reporting currency.",
        interpretation="A large gap between reported (as-translated) growth and constant-currency growth signals that currency moves, not the underlying business, are driving the headline number.",
        related_concepts=("organic_growth",),
    ),
    "free_float": ConceptCard(
        "free_float", M, "Free Float",
        "The proportion of a company's total shares outstanding that are freely available for public trading, excluding shares held by promoters, founders, governments, or other strategic/locked-in holders.",
        business_meaning="A low free float can mean lower liquidity and higher price volatility, since a smaller pool of shares is available to absorb buying and selling pressure.",
        interpretation="Index providers typically weight constituents by free-float market cap rather than total market cap, precisely because only the free float is actually available to index-tracking investors.",
        related_concepts=("liquidity", "promoter_holding"),
    ),
    "promoter_holding": ConceptCard(
        "promoter_holding", M, "Promoter Holding",
        "The percentage of a company's shares held by its founders/controlling shareholders (a term used especially in Indian capital markets).",
        business_meaning="High promoter holding can signal skin-in-the-game alignment with minority shareholders; declining promoter holding over time (especially via pledging or open-market sales) can be a governance red flag.",
        related_concepts=("free_float", "pledge_of_shares"),
    ),
    "pledge_of_shares": ConceptCard(
        "pledge_of_shares", M, "Pledge of Shares",
        "Promoters or major shareholders using their shares as collateral to raise loans, rather than selling them outright.",
        business_meaning="A high or rising pledge percentage is a governance and stock-price risk: a sharp price decline can trigger a margin call, forcing the lender to sell the pledged shares into a falling market and accelerating the decline.",
        interpretation="Rising pledge levels alongside financial stress at the promoter's other entities is a classic warning sign analysts monitor closely.",
        related_concepts=("promoter_holding", "refinancing_risk"),
    ),
    "related_party_transactions": ConceptCard(
        "related_party_transactions", M, "Related Party Transactions (RPTs)",
        "Business dealings between a company and its promoters, directors, or affiliated entities, disclosed separately because of the potential for conflicts of interest.",
        business_meaning="RPTs are not inherently improper, but a pattern of transactions at non-market terms can be used to extract value from minority shareholders toward controlling shareholders.",
        interpretation="Large, growing, or opaque related-party transactions — especially loans to or purchases from promoter-affiliated entities — warrant close governance scrutiny.",
        related_concepts=("promoter_holding", "audit_qualification"),
    ),
    "audit_qualification": ConceptCard(
        "audit_qualification", M, "Audit Qualification",
        "A formal note or exception an independent auditor adds to their opinion on a company's financial statements, flagging a specific concern, uncertainty, or disagreement with management's accounting treatment.",
        business_meaning="A qualified audit opinion is a material red flag — it means the auditor cannot fully vouch for the accuracy of the reported financials without a specific caveat.",
        interpretation="Even a single audit qualification warrants materially deeper diligence into the underlying issue before relying on the reported numbers.",
        related_concepts=("going_concern", "related_party_transactions"),
    ),
    "going_concern": ConceptCard(
        "going_concern", M, "Going Concern (Qualification)",
        "An auditor's assessment of substantial doubt about a company's ability to continue operating for the foreseeable future (typically the next 12 months).",
        business_meaning="One of the most severe warnings an auditor can issue — it directly signals a material risk of insolvency or bankruptcy absent a change in circumstances (refinancing, capital raise, asset sale).",
        interpretation="A going-concern qualification typically triggers a sharp repricing of both equity and debt, since it formally elevates default risk in the eyes of every market participant.",
        related_concepts=("audit_qualification", "default_risk", "liquidity"),
    ),
}
