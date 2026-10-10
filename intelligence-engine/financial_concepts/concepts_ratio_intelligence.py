"""Module 2 — Ratio Intelligence Expansion."""

from __future__ import annotations

from financial_concepts.schema import ConceptCard

M = "ratio_intelligence"

RATIO_INTELLIGENCE_CONCEPTS: dict[str, ConceptCard] = {
    "dupont_model": ConceptCard(
        "dupont_model", M, "DuPont Model",
        "A framework that decomposes Return on Equity into three drivers — profitability, efficiency, and leverage — to explain WHY ROE is what it is, not just what it is.",
        formula="ROE = Net Margin × Asset Turnover × Equity Multiplier = (Net Income/Revenue) × (Revenue/Assets) × (Assets/Equity)",
        business_meaning="Two companies can have identical ROE for completely different reasons — one from superior margins, another from leverage alone — and the DuPont breakdown tells them apart.",
        interpretation="Rising ROE driven by margin and turnover improvement is high quality; rising ROE driven purely by a rising equity multiplier (leverage) is lower quality and riskier.",
        common_mistakes="Looking at ROE as a single number without decomposing it — a leverage-driven ROE can mask deteriorating operating performance.",
        related_concepts=("roe_decomposition", "financial_leverage", "asset_turnover", "roa_decomposition"),
    ),
    "roe_decomposition": ConceptCard(
        "roe_decomposition", M, "ROE Decomposition",
        "Breaking Return on Equity down into its DuPont components (margin, turnover, leverage) to diagnose the source of a change in ROE.",
        formula="ΔROE ≈ Δ(Net Margin) + Δ(Asset Turnover) + Δ(Equity Multiplier), each held at the others' levels",
        business_meaning="Explains, for example, why ROE can rise even as PAT falls — if the equity base (denominator) shrinks faster than net income (numerator), such as via large buybacks or dividends.",
        interpretation="An analyst should always ask 'which DuPont lever moved?' before treating a change in ROE as good or bad news.",
        related_concepts=("dupont_model", "roa_decomposition", "financial_leverage"),
    ),
    "roa_decomposition": ConceptCard(
        "roa_decomposition", M, "ROA Decomposition",
        "Breaking Return on Assets into its two DuPont drivers — net margin and asset turnover — independent of leverage.",
        formula="ROA = Net Margin × Asset Turnover = Net Income/Revenue × Revenue/Total Assets",
        business_meaning="Because ROA excludes the leverage step of the full DuPont equation, it isolates pure operating efficiency from financing decisions.",
        interpretation="Comparing ROA (leverage-neutral) alongside ROE (leverage-inclusive) reveals how much of a company's equity return comes from operations versus financial engineering.",
        related_concepts=("dupont_model", "roe_decomposition", "asset_turnover"),
    ),
    "operating_leverage": ConceptCard(
        "operating_leverage", M, "Operating Leverage",
        "The degree to which a company's cost structure is fixed versus variable — and therefore how much profit swings for a given change in revenue.",
        formula="Degree of Operating Leverage = % Change in Operating Profit / % Change in Revenue",
        business_meaning=(
            "High fixed-cost businesses (airlines, hotels, manufacturing) see profit and margin "
            "swing dramatically with small revenue changes, since fixed costs don't fall when "
            "revenue does. For airlines, once the breakeven load factor is cleared, incremental "
            "passengers drop through to margin; below breakeven, empty seats still carry the "
            "fixed fleet and crew cost base."
        ),
        interpretation="High operating leverage magnifies both upside (in a recovery) and downside (in a downturn) — the same cost structure that drives outsized profit growth in good times drives outsized losses in bad times.",
        industry_exceptions="Asset-light, variable-cost businesses (many services and software-as-a-service companies with usage-based costs) have low operating leverage and steadier margins through cycles.",
        related_concepts=("financial_leverage", "fixed_charge_coverage", "contribution_margin"),
    ),
    "financial_leverage": ConceptCard(
        "financial_leverage", M, "Financial Leverage",
        "The extent to which a company uses debt to finance its assets, magnifying both potential returns to equity holders and potential losses.",
        formula="Financial Leverage (Equity Multiplier) = Total Assets / Total Equity",
        business_meaning="Debt magnifies ROE when the return on assets exceeds the cost of debt, but magnifies losses (and can wipe out equity) when it does not.",
        interpretation="Rising financial leverage without a corresponding improvement in ROIC/ROA is a red flag — the company is relying on leverage, not operating performance, to sustain returns.",
        related_concepts=("capital_structure", "dupont_model", "interest_coverage", "operating_leverage"),
    ),
    "interest_coverage": ConceptCard(
        "interest_coverage", M, "Interest Coverage Ratio",
        "How many times over a company's operating earnings can pay its interest expense.",
        formula="Interest Coverage = EBIT / Interest Expense",
        business_meaning="A direct measure of near-term solvency risk — low coverage means a modest earnings decline could leave the company unable to service its debt.",
        interpretation="Coverage below roughly 2x is generally considered risky; coverage compressing over time (even if still above 1x) signals deteriorating credit quality before a covenant breach or default actually occurs.",
        related_concepts=("fixed_charge_coverage", "debt_service_coverage", "cost_of_debt", "default_risk"),
    ),
    "fixed_charge_coverage": ConceptCard(
        "fixed_charge_coverage", M, "Fixed Charge Coverage Ratio",
        "A stricter version of interest coverage that also includes lease payments and other fixed financial obligations, not just interest.",
        formula="Fixed Charge Coverage = (EBIT + Lease Payments) / (Interest Expense + Lease Payments + Other Fixed Charges)",
        business_meaning="Interest coverage alone can overstate solvency for companies with heavy operating lease commitments (retailers, airlines) that behave like debt but aren't classified as such.",
        interpretation="A company can look safe on interest coverage alone yet be fragile on fixed charge coverage if lease obligations are large relative to EBIT.",
        related_concepts=("interest_coverage", "debt_service_coverage", "covenants"),
    ),
    "cash_conversion": ConceptCard(
        "cash_conversion", M, "Cash Conversion (Ratio)",
        "The proportion of accounting profit (typically EBITDA or Net Income) that actually converts into operating cash flow.",
        formula="Cash Conversion = Operating Cash Flow / EBITDA (or Net Income)",
        business_meaning="A company can report strong profit growth while cash conversion deteriorates if working capital is absorbing the gains — a classic early warning sign of earnings-quality problems.",
        interpretation="Cash conversion persistently and meaningfully below 100% (after normalizing for growth-driven working capital needs) warrants scrutiny of receivables, inventory, and revenue recognition practices.",
        related_concepts=("fcf_conversion", "working_capital"),
    ),
    "fcf_conversion": ConceptCard(
        "fcf_conversion", M, "FCF Conversion",
        "The share of accounting profit (EBITDA or Net Income) that converts into Free Cash Flow after capital expenditure.",
        formula="FCF Conversion = Free Cash Flow / EBITDA (or Net Income)",
        business_meaning="Distinguishes capital-light businesses (high FCF conversion) from capital-intensive ones (lower conversion because more profit must be reinvested to sustain/grow the asset base).",
        interpretation="Declining FCF conversion alongside rising EBITDA usually means capex intensity is increasing — worth checking whether that capex is maintenance or growth spending.",
        related_concepts=("free_cash_flow", "cash_conversion", "capex_intensity"),
    ),
    "asset_turnover": ConceptCard(
        "asset_turnover", M, "Asset Turnover",
        "How efficiently a company uses its total assets to generate revenue.",
        formula="Asset Turnover = Revenue / Total Assets",
        business_meaning="A key DuPont component — asset-light businesses (services, software) naturally run high turnover; asset-heavy businesses (utilities, manufacturing, telecom) run low turnover but often compensate with higher margins.",
        interpretation="A rising asset turnover alongside stable margins signals genuine efficiency improvement, not just balance-sheet shrinkage.",
        industry_exceptions="Capital-intensive industries (utilities, real estate) structurally run low asset turnover and should never be compared to asset-light peers on this metric alone.",
        related_concepts=("dupont_model", "capital_turnover", "roa_decomposition"),
    ),
    "capital_turnover": ConceptCard(
        "capital_turnover", M, "Capital Turnover",
        "How efficiently a company generates revenue from its invested/employed capital base, rather than total assets.",
        formula="Capital Turnover = Revenue / Invested Capital (or Capital Employed)",
        business_meaning="A more precise efficiency measure than asset turnover because it excludes non-interest-bearing operating liabilities (like payables) from the denominator.",
        interpretation="Combined with margin, capital turnover is one of the two levers (alongside margin) that together determine ROIC.",
        related_concepts=("asset_turnover", "invested_capital", "roic"),
    ),
    "inventory_days": ConceptCard(
        "inventory_days", M, "Inventory Days (Days Inventory Outstanding)",
        "The average number of days a company holds inventory before it is sold.",
        formula="Inventory Days = (Average Inventory / COGS) × 365",
        business_meaning="Rising inventory days can mean slowing demand, overproduction, or product obsolescence risk — cash is tied up in unsold goods for longer.",
        interpretation="Inventory doubling while revenue stays flat is a classic red flag: turnover has collapsed and markdowns or write-offs may follow.",
        industry_exceptions="Long-production-cycle industries (aircraft, shipbuilding, wine/spirits ageing) structurally carry much higher inventory days than fast-moving consumer goods.",
        related_concepts=("cash_conversion_cycle",),
    ),
    "receivable_days": ConceptCard(
        "receivable_days", M, "Receivable Days (Days Sales Outstanding)",
        "The average number of days it takes a company to collect cash after making a credit sale.",
        formula="Receivable Days = (Average Accounts Receivable / Revenue) × 365",
        business_meaning="Rising receivable days relative to revenue growth signals looser credit terms or weaker collection discipline — an early earnings-quality warning.",
        interpretation="Receivables growing materially faster than revenue (e.g. +60% vs. +10%) often means revenue is being recognised well ahead of cash collection.",
        related_concepts=("cash_conversion_cycle",),
    ),
    "payable_days": ConceptCard(
        "payable_days", M, "Payable Days (Days Payable Outstanding)",
        "The average number of days a company takes to pay its own suppliers.",
        formula="Payable Days = (Average Accounts Payable / COGS) × 365",
        business_meaning="A longer payable period means suppliers are effectively financing the company's working capital, improving its cash conversion cycle.",
        interpretation="A sharp, sudden increase in payable days can also signal cash-flow stress — the company may be stretching supplier payments involuntarily rather than by negotiated terms.",
        related_concepts=("cash_conversion_cycle", "working_capital"),
    ),
    "cash_cycle": ConceptCard(
        "cash_cycle", M, "Cash Cycle",
        "Shorthand for the Cash Conversion Cycle — the net number of days capital is tied up between paying suppliers and collecting from customers.",
        formula="Cash Cycle = Inventory Days + Receivable Days − Payable Days",
        business_meaning="A negative cash cycle (common in retail/e-commerce) means the business collects cash from customers before it has to pay suppliers — effectively self-funding working capital.",
        interpretation="A lengthening cash cycle over successive periods, even with revenue growing, signals rising working-capital intensity that will consume more cash to sustain the same growth rate.",
        related_concepts=("cash_conversion_cycle", "working_capital", "inventory_days"),
    ),
    "dividend_coverage": ConceptCard(
        "dividend_coverage", M, "Dividend Coverage Ratio",
        "How many times over a company's earnings could pay its declared dividend.",
        formula="Dividend Coverage = Net Income / Total Dividends Paid (inverse of the Payout Ratio)",
        business_meaning="Low coverage (near 1x) means the dividend has little cushion against an earnings downturn and may be at risk of a cut.",
        interpretation="Coverage should be assessed alongside cash-flow-based dividend sustainability, since a company can have adequate accounting earnings coverage yet still lack the cash to fund the payout.",
        related_concepts=("payout_ratio", "dividend_sustainability", "dividend_policy"),
    ),
    "contribution_margin": ConceptCard(
        "contribution_margin", M, "Contribution Margin",
        "The revenue remaining after variable costs are deducted, available to cover fixed costs and generate profit.",
        formula="Contribution Margin = (Revenue − Variable Costs) / Revenue",
        business_meaning="Determines how much additional profit flows through from each incremental unit of revenue once fixed costs are already covered — the engine behind operating leverage.",
        interpretation="A high contribution margin means revenue growth beyond the fixed-cost breakeven point drops through to profit at a very high rate.",
        related_concepts=("operating_leverage",),
    ),
    "asset_intensity": ConceptCard(
        "asset_intensity", M, "Asset Intensity",
        "How much investment in assets a business requires to generate a given level of revenue or profit — the inverse concept of asset turnover.",
        business_meaning="Asset-heavy businesses (telecom towers, refineries, utilities) require large upfront and ongoing capital commitments; asset-light businesses (software, brands) can scale revenue with comparatively little new capital.",
        interpretation="Rising asset intensity over time, without a corresponding rise in returns, means the business is becoming structurally less capital-efficient.",
        related_concepts=("asset_turnover", "capital_intensity", "maintenance_capex"),
    ),
    "capital_intensity": ConceptCard(
        "capital_intensity", M, "Capital Intensity",
        "The ratio of capital investment required to support a given level of sales or growth — a close cousin of asset intensity, framed around capex specifically.",
        formula="Capital Intensity = Capex / Revenue",
        business_meaning="High capital-intensity businesses need continuous heavy reinvestment just to maintain their competitive position (semiconductors, telecom, heavy industry).",
        interpretation="Rising capital intensity alongside falling incremental ROIC is a warning that the industry's growth may no longer be worth funding.",
        related_concepts=("capex_intensity", "asset_intensity", "growth_capex"),
    ),
}
