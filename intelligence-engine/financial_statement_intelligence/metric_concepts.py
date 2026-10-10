"""Module 1 (Income Statement), 2 (Balance Sheet), 3 (Cash Flow), 5
(Ratios), 8 (Margins) — metric concept library.

Every metric gets definition + formula + drivers + interpretation +
industry differences + common distortions. This is deeper than Phase
1's line-item cards: Phase 1 explained what a line IS; this explains
how an ANALYST reads it.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class MetricCard:
    key: str
    module: int
    title: str
    definition: str
    formula: str
    drivers: list[str]
    interpretation: str
    industry_differences: str
    common_distortions: str


INCOME_STATEMENT_METRICS: dict[str, MetricCard] = {
    "revenue_analysis": MetricCard(
        "revenue_analysis", 1, "Revenue",
        "Value of goods/services delivered to customers in the period.",
        "Revenue = Σ(units × price), recognised on delivery.",
        ["Volume", "Pricing / realisation", "Product mix", "New customer wins", "Churn"],
        "Revenue growth alone says nothing about quality — always check whether it converted "
        "to EBITDA and cash, and whether it came from price, volume, or mix.",
        "Subscription businesses watch ARR/net revenue retention; project businesses watch "
        "order book and execution velocity; retailers watch same-store sales growth (SSSG).",
        "Channel stuffing (pulling forward future sales), aggressive bundling, or one-time "
        "contract recognition can inflate a single period's revenue without repeatable demand.",
    ),
    "gross_margin": MetricCard(
        "gross_margin", 1, "Gross Margin",
        "Gross Profit as a percentage of Revenue.",
        "Gross Margin = Gross Profit / Revenue.",
        ["Pricing power", "Raw material costs", "Product mix", "Manufacturing efficiency", "FX (import costs)"],
        "Expanding gross margin with flat/declining revenue usually signals pricing power or "
        "input cost relief; expanding margin WITH volume growth signals both demand and "
        "operating discipline.",
        "Asset-light software businesses run 70-90% gross margins; manufacturers typically "
        "run 15-40%; comparing the two directly is meaningless.",
        "Reclassifying costs between COGS and OpEx can shift gross margin without any real "
        "change in economics — always check for consistent classification across periods.",
    ),
    "ebitda_margin": MetricCard(
        "ebitda_margin", 1, "EBITDA Margin",
        "EBITDA as a percentage of Revenue.",
        "EBITDA Margin = EBITDA / Revenue.",
        ["Gross margin", "Operating leverage", "Cost discipline (SG&A)", "Scale economies"],
        "If Revenue grows 15% but EBITDA grows only 5%, EBITDA margin is compressing — this "
        "suggests cost inflation, weak operating leverage, or price competition eating into gains.",
        "Capital-intensive industrials often target 15-25% EBITDA margins; asset-light "
        "platforms can run 40%+; compare within-sector only.",
        "One-off cost cuts (furloughs, deferred maintenance) can flatter EBITDA margin "
        "temporarily without reflecting a sustainable structural improvement.",
    ),
    "operating_margin": MetricCard(
        "operating_margin", 1, "Operating Margin (EBIT Margin)",
        "EBIT as a percentage of Revenue — profitability after depreciation.",
        "Operating Margin = EBIT / Revenue.",
        ["EBITDA margin", "Depreciation intensity", "Asset base age", "Capex cycle stage"],
        "A widening gap between EBITDA margin and Operating margin over time signals rising "
        "depreciation — usually from an ongoing capex cycle; watch whether that capex is "
        "growth-driven or maintenance-driven.",
        "Asset-heavy sectors (telecom, utilities, hospitals) show a much larger EBITDA-to-EBIT "
        "gap than asset-light sectors (IT services, consulting).",
        "Extending useful-life assumptions on assets lowers depreciation and inflates EBIT "
        "without any real change in cash economics.",
    ),
    "net_margin": MetricCard(
        "net_margin", 1, "Net Margin (PAT Margin)",
        "PAT as a percentage of Revenue — the bottom-line conversion rate.",
        "Net Margin = PAT / Revenue.",
        ["Operating margin", "Interest burden (leverage)", "Effective tax rate", "One-off items"],
        "Net margin can move for reasons entirely unrelated to the operating business — a tax "
        "rate change or a refinancing that alters interest expense will move net margin without "
        "any change in EBIT.",
        "Highly-levered sectors (real estate, infrastructure) show more net-margin volatility "
        "from interest costs than asset-light, low-debt sectors.",
        "One-off gains (asset sales, tax credits) can flatter net margin in a single period — "
        "always check if EBIT margin moved in the same direction.",
    ),
    "eps_analysis": MetricCard(
        "eps_analysis", 1, "Earnings Per Share (EPS)",
        "PAT allocated per outstanding share — the per-share claim on profit.",
        "EPS = PAT / Weighted Average Shares Outstanding.",
        ["PAT growth", "Share count changes (dilution/buybacks)"],
        "EPS can grow faster than PAT through buybacks (fewer shares), or slower than PAT "
        "through dilution (more shares from ESOPs, QIPs, or convertible conversions).",
        "Growth companies raising equity frequently often show EPS growing slower than PAT; "
        "mature cash-generative companies buying back stock often show the opposite.",
        "Aggressive buybacks funded by debt can flatter EPS growth while quietly increasing "
        "financial risk — check net debt alongside EPS trend.",
    ),
}

BALANCE_SHEET_METRICS: dict[str, MetricCard] = {
    "receivables_quality": MetricCard(
        "receivables_quality", 2, "Accounts Receivable Trend",
        "Amounts owed by customers for revenue already recognised.",
        "Receivable Days = (Receivables / Revenue) × 365.",
        ["Credit terms extended to customers", "Customer concentration", "Collection discipline"],
        "Receivables growing meaningfully faster than Revenue is one of the single strongest "
        "early-warning signs of aggressive revenue recognition or deteriorating collections.",
        "B2B/enterprise sellers naturally carry higher receivable days than B2C/retail "
        "businesses that collect at point of sale.",
        "Extending credit terms to pull sales forward, or factoring receivables off the "
        "balance sheet, can both distort the apparent trend.",
    ),
    "inventory_quality": MetricCard(
        "inventory_quality", 2, "Inventory Trend",
        "Goods held for sale, not yet converted to revenue.",
        "Inventory Days = (Inventory / COGS) × 365.",
        ["Demand forecasting accuracy", "Supply chain lead times", "Strategic stocking decisions"],
        "Inventory rising faster than sales can mean weakening demand (unsold stock piling "
        "up) OR a deliberate strategic build ahead of an anticipated demand surge — the "
        "direction of Gross Margin and forward order book disambiguates the two.",
        "Retail/FMCG carries low inventory days (fast turns); capital goods/shipbuilding "
        "carries very high inventory days (long production cycles) — context matters.",
        "Failing to write down obsolete/slow-moving inventory overstates both Inventory and "
        "reported profitability.",
    ),
    "goodwill_and_intangibles": MetricCard(
        "goodwill_and_intangibles", 2, "Goodwill & Intangibles",
        "The premium paid over net identifiable assets in an acquisition (Goodwill), plus "
        "other non-physical assets (Intangibles).",
        "Goodwill = Purchase Price − Fair Value of Net Identifiable Assets Acquired.",
        ["Acquisition activity", "Impairment testing outcomes", "Brand/IP capitalisation policy"],
        "A rising Goodwill balance after acquisitions is expected, but Goodwill that is large "
        "relative to Total Assets concentrates risk — any future impairment can be a material "
        "one-off hit to PAT and Equity.",
        "Roll-up / serial-acquirer business models (services, healthcare platforms) "
        "structurally carry much higher Goodwill/Assets than organically-grown industrials.",
        "Companies can delay recognising an impairment they know is coming, overstating "
        "Assets and Equity until forced to write down.",
    ),
    "leverage_structure": MetricCard(
        "leverage_structure", 2, "Debt & Leverage Structure",
        "The mix of short-term debt, long-term debt, and lease liabilities funding the business.",
        "Total Debt = Short-term Debt + Long-term Debt (+ Lease Liabilities, if capitalised).",
        ["Growth capex needs", "Working capital financing", "Refinancing decisions", "Dividend/buyback funding"],
        "Cash declining WHILE debt is rising is a classic financial-stress signal — the "
        "business is burning liquidity and replacing it with borrowed capital rather than "
        "internally generated cash.",
        "Utilities/infrastructure structurally run high leverage against stable cash flows; "
        "asset-light services businesses should carry far less debt for the same risk profile.",
        "Off-balance-sheet lease structures (operating leases pre-IFRS16/Ind-AS116) understate "
        "true leverage if not added back.",
    ),
}

CASH_FLOW_METRICS: dict[str, MetricCard] = {
    "free_cash_flow": MetricCard(
        "free_cash_flow", 3, "Free Cash Flow (FCF)",
        "Cash generated by operations after funding the capex needed to sustain/grow the business.",
        "FCF = Operating Cash Flow − Capex.",
        ["Operating Cash Flow", "Capex intensity", "Working capital swings"],
        "FCF is what actually funds dividends, buybacks, and debt paydown without external "
        "financing — a company can report growing PAT for years while FCF stays negative if "
        "capex or working capital consumes it all.",
        "Capital-intensive sectors (telecom, power, steel) can run negative FCF for years "
        "during expansion; asset-light sectors should convert PAT to FCF much more directly.",
        "Deferring necessary maintenance capex temporarily inflates FCF at the cost of future "
        "asset productivity.",
    ),
    "dividend_sustainability": MetricCard(
        "dividend_sustainability", 3, "Dividend Sustainability",
        "Whether dividends paid are covered by cash the business actually generates.",
        "Dividend Coverage = Free Cash Flow / Dividends Paid.",
        ["FCF generation", "Payout policy", "Balance sheet capacity to fund a gap with debt"],
        "Dividends funded from FCF are sustainable; dividends funded by drawing down cash or "
        "raising debt are not — a coverage ratio below 1x for multiple periods is a warning sign.",
        "Mature utilities/consumer staples with stable FCF sustain higher payout ratios than "
        "growth companies still reinvesting most of their cash flow.",
        "A company can maintain a dividend through a downturn by borrowing specifically to "
        "fund it — this looks fine on the Income Statement but shows up as rising debt.",
    ),
    "buyback_discipline": MetricCard(
        "buyback_discipline", 3, "Share Buyback Discipline",
        "Whether repurchases are funded by surplus FCF and priced sensibly.",
        "Buyback Coverage = Free Cash Flow / Buybacks.",
        ["FCF surplus after dividends", "Valuation at time of buyback", "Alternative uses of capital (capex, M&A)"],
        "Buybacks funded by FCF surplus with no incremental debt are a capital-return "
        "decision; buybacks funded by NEW debt while FCF is flat or negative shift risk from "
        "shareholders to lenders.",
        "Cash-generative, low-growth mature businesses (IT services, staples) are natural "
        "buyback candidates; high-growth businesses buying back stock instead of reinvesting "
        "may signal a lack of growth opportunities.",
        "Buying back stock right before a decline in fundamentals (rather than opportunistically "
        "when cheap) destroys value even though EPS still looks like it 'improved'.",
    ),
    "working_capital_cf": MetricCard(
        "working_capital_cf", 3, "Working Capital (Cash Flow Lens)",
        "The capital tied up in receivables + inventory net of payables — the reason PAT and "
        "Operating Cash Flow diverge.",
        "Working Capital = (Receivables + Inventory) − Payables.",
        ["Revenue growth rate", "Credit terms (customer and supplier)", "Inventory strategy"],
        "A growing business often needs MORE working capital even while highly profitable — "
        "this is precisely why PAT can rise while Operating Cash Flow falls.",
        "Fast-growing D2C/retail businesses with negative working capital (collect before "
        "paying suppliers) can scale with minimal capital; B2B manufacturers with long "
        "payment cycles need much more capital per unit of growth.",
        "Stretching supplier payment terms (increasing Payables) can flatter near-term "
        "working capital and cash flow at the cost of supplier relationships.",
    ),
}

RATIO_METRICS: dict[str, MetricCard] = {
    "current_ratio": MetricCard(
        "current_ratio", 5, "Current Ratio",
        "Whether current assets cover current liabilities.",
        "Current Ratio = Current Assets / Current Liabilities.",
        ["Cash balance", "Receivables/Inventory levels", "Short-term debt and payables"],
        "Below 1.0x means current liabilities exceed current assets — a near-term liquidity "
        "concern unless the business has reliable access to fresh financing.",
        "Retailers with fast inventory turns can operate safely below 1.0x; capital goods "
        "businesses with long working-capital cycles need meaningfully above 1.0x.",
        "Warning sign below 1.2x for a working-capital-intensive business.",
    ),
    "quick_ratio": MetricCard(
        "quick_ratio", 5, "Quick Ratio (Acid-Test)",
        "Liquidity excluding inventory, which may not convert to cash quickly.",
        "Quick Ratio = (Current Assets − Inventory) / Current Liabilities.",
        ["Cash and receivables", "Current liabilities"],
        "A large gap between Current Ratio and Quick Ratio signals heavy reliance on selling "
        "inventory to meet near-term obligations.",
        "Software/services businesses (minimal inventory) see Current and Quick Ratios "
        "converge; manufacturers/retailers see a meaningful gap.",
        "Warning sign below 1.0x, especially alongside slow inventory turns.",
    ),
    "cash_ratio": MetricCard(
        "cash_ratio", 5, "Cash Ratio",
        "The most conservative liquidity measure — cash alone against current liabilities.",
        "Cash Ratio = Cash / Current Liabilities.",
        ["Cash generation", "Dividend/buyback policy", "Debt maturities"],
        "A very low Cash Ratio is only a concern if the Current/Quick Ratios are also weak — "
        "many efficient businesses deliberately run low cash balances.",
        "Businesses with strong access to credit lines can run lower cash ratios safely than "
        "those without.",
        "Warning sign below 0.2x combined with weak Quick Ratio.",
    ),
    "debt_to_equity": MetricCard(
        "debt_to_equity", 5, "Debt / Equity",
        "How much the business relies on debt versus owner capital.",
        "Debt/Equity = Total Debt / Total Equity.",
        ["Capex funding choices", "Buyback/dividend funding", "Profitability retained as equity"],
        "Rising Debt/Equity alongside falling profitability compounds risk; rising Debt/Equity "
        "alongside rising ROE (from disciplined leverage) can be a rational capital structure choice.",
        "Financials/real estate/infrastructure structurally run high Debt/Equity; software "
        "and services should run low.",
        "Warning sign above 1.5-2.0x outside naturally leveraged sectors (financials, "
        "infrastructure, real estate).",
    ),
    "net_debt_to_ebitda": MetricCard(
        "net_debt_to_ebitda", 5, "Net Debt / EBITDA",
        "How many years of current EBITDA it would take to pay off net debt.",
        "Net Debt/EBITDA = (Total Debt − Cash) / EBITDA.",
        ["Debt level", "Cash balance", "EBITDA generation"],
        "Rising Net Debt/EBITDA while EBITDA itself is falling is a double deterioration — "
        "leverage capacity is shrinking exactly when debt service becomes harder.",
        "Investment-grade industrials typically target below 2-3x; leveraged buyouts/private "
        "equity portfolio companies routinely run 4-6x+.",
        "Warning sign above 3.5-4x for a non-financial, non-infrastructure business.",
    ),
    "interest_coverage": MetricCard(
        "interest_coverage", 5, "Interest Coverage",
        "How comfortably operating profit covers interest obligations.",
        "Interest Coverage = EBIT / Interest Expense.",
        ["EBIT trend", "Cost of debt", "Debt level"],
        "Falling Interest Coverage — from EITHER declining EBIT or rising interest expense — "
        "signals shrinking headroom before covenant breach or refinancing stress.",
        "Regulated utilities with predictable cash flows can safely run lower coverage than "
        "cyclical industrials.",
        "Warning sign below 2.0-2.5x; below 1.0x means EBIT does not even cover interest.",
    ),
    "roe": MetricCard(
        "roe", 5, "Return on Equity (ROE)",
        "Profit generated per unit of shareholder capital.",
        "ROE = PAT / Average Total Equity.",
        ["Net margin", "Asset turnover", "Financial leverage (DuPont decomposition)"],
        "ROE improving despite LOWER net income usually means Equity shrank faster than "
        "income (buybacks, dividends exceeding retained earnings) — always decompose ROE "
        "(DuPont) before treating a rising ROE as pure operating improvement.",
        "Banks/financials run structurally higher ROE than capital-intensive industrials due "
        "to inherent leverage in the business model.",
        "Aggressive buybacks or debt-funded special dividends can inflate ROE by shrinking "
        "the equity base rather than growing profit.",
    ),
    "roa": MetricCard(
        "roa", 5, "Return on Assets (ROA)",
        "Profit generated per unit of total assets, independent of financing structure.",
        "ROA = PAT / Average Total Assets.",
        ["Net margin", "Asset turnover"],
        "ROA is a cleaner cross-company comparison than ROE because it strips out leverage — "
        "a company can have high ROE and low ROA if it simply carries more debt.",
        "Asset-light services businesses naturally run higher ROA than capital-intensive "
        "manufacturers.",
        "One-off asset sales can temporarily boost ROA without any operating improvement.",
    ),
    "roce": MetricCard(
        "roce", 5, "Return on Capital Employed (ROCE)",
        "Operating profit generated per unit of capital employed (debt + equity).",
        "ROCE = EBIT / (Total Assets − Current Liabilities).",
        ["EBIT margin", "Capital intensity", "Working capital efficiency"],
        "ROCE consistently above the cost of capital signals value-creating operations; "
        "persistently below it signals value destruction regardless of headline profit growth.",
        "Asset-light, high-margin businesses (software, brands) run structurally higher ROCE "
        "than capital-intensive commodity businesses (steel, cement).",
        "Fully depreciated old assets mechanically inflate ROCE (smaller capital base) "
        "without reflecting current reinvestment economics.",
    ),
    "roic": MetricCard(
        "roic", 5, "Return on Invested Capital (ROIC)",
        "After-tax operating profit generated per unit of invested capital, the cleanest "
        "capital-allocation quality metric.",
        "ROIC = EBIT × (1 − Tax Rate) / Invested Capital (Debt + Equity − Cash).",
        ["Operating margin", "Capital intensity", "Tax rate"],
        "ROIC vs WACC is THE capital-allocation test: ROIC > WACC creates value from every "
        "incremental rupee invested; ROIC < WACC destroys value even if absolute profit is growing.",
        "Compare ROIC only within the same industry — capital intensity varies enormously "
        "across sectors.",
        "Excess cash sitting idle on the balance sheet (not netted correctly) can distort "
        "ROIC comparisons across companies with different cash policies.",
    ),
    "asset_turnover": MetricCard(
        "asset_turnover", 5, "Asset Turnover",
        "How efficiently assets are converted into revenue.",
        "Asset Turnover = Revenue / Average Total Assets.",
        ["Revenue growth", "Asset base growth/efficiency"],
        "Asset Turnover falling while Revenue still grows means the asset base is growing "
        "even faster — capital intensity is rising, which should show up eventually in ROCE/ROIC.",
        "Retail/distribution businesses run high asset turnover; capital-intensive utilities "
        "run low turnover by nature.",
        "Aggressive asset write-downs mechanically boost turnover without any real efficiency gain.",
    ),
    "inventory_turnover": MetricCard(
        "inventory_turnover", 5, "Inventory Turnover",
        "How many times inventory is sold and replaced in a period.",
        "Inventory Turnover = COGS / Average Inventory.",
        ["Demand strength", "Supply chain efficiency", "Product obsolescence risk"],
        "Falling inventory turnover (rising inventory days) alongside flat/falling revenue "
        "growth suggests demand softness rather than a deliberate strategic build.",
        "Fashion/perishables need very high turnover; capital goods/aerospace naturally turn "
        "inventory slowly.",
        "Bulk-buying ahead of a price increase can temporarily lower turnover without "
        "signalling any operational problem.",
    ),
    "receivable_days": MetricCard(
        "receivable_days", 5, "Receivable Days (DSO)",
        "Average number of days to collect cash after a sale.",
        "Receivable Days = (Receivables / Revenue) × 365.",
        ["Credit terms", "Customer mix", "Collections discipline"],
        "Rising Receivable Days is one of the clearest, earliest signals of either collection "
        "risk or aggressive revenue recognition — always cross-check against Revenue growth.",
        "Government/enterprise-heavy sellers run structurally higher DSO than cash-collecting "
        "retail/consumer businesses.",
        "A large one-off sale near period-end can spike DSO without reflecting the underlying "
        "run-rate collection experience.",
    ),
    "payable_days": MetricCard(
        "payable_days", 5, "Payable Days (DPO)",
        "Average number of days taken to pay suppliers.",
        "Payable Days = (Payables / COGS) × 365.",
        ["Supplier negotiating power", "Working capital strategy", "Supplier relationships"],
        "Rising Payable Days can be efficient working-capital management OR a sign of cash "
        "stress (stretching suppliers because cash is tight) — check the cash and debt trend "
        "alongside it.",
        "Large retailers with strong bargaining power run high DPO by design; smaller "
        "suppliers have far less room to negotiate extended terms.",
        "Aggressively stretching payables right before period-end window-dresses working "
        "capital metrics temporarily.",
    ),
    "cash_conversion_cycle": MetricCard(
        "cash_conversion_cycle", 5, "Cash Conversion Cycle (CCC)",
        "Net number of days cash is tied up in the operating cycle.",
        "CCC = Receivable Days + Inventory Days − Payable Days.",
        ["Receivable days", "Inventory days", "Payable days"],
        "A rising CCC means more cash is trapped in operations per unit of revenue — this is "
        "precisely why a growing, profitable business can still be a growing consumer of cash.",
        "Efficient D2C/retail models can run a NEGATIVE CCC (collect from customers before "
        "paying suppliers); capital goods manufacturers often run a CCC of 100+ days.",
        "One-off supplier or customer term renegotiations can move CCC without reflecting a "
        "structural change in the business.",
    ),
    "revenue_cagr": MetricCard(
        "revenue_cagr", 5, "Revenue CAGR",
        "Compounded annual growth rate of Revenue across the analysis window.",
        "Revenue CAGR = (Revenue_end / Revenue_start)^(1/years) − 1.",
        ["Volume growth", "Pricing/realisation", "M&A-driven growth", "Base effects"],
        "Is growth accelerating or decelerating relative to the CAGR? A single strong recent "
        "period can mask a longer-run deceleration, and vice versa.",
        "Compare CAGR against sector/GDP-linked benchmarks — 8% CAGR is exceptional for a "
        "mature utility but subpar for a high-growth software business.",
        "M&A-driven revenue growth is not the same as organic growth — always check for "
        "acquisitions distorting the trend.",
    ),
    "eps_cagr": MetricCard(
        "eps_cagr", 5, "EPS CAGR",
        "Compounded annual growth rate of EPS across the analysis window.",
        "EPS CAGR = (EPS_end / EPS_start)^(1/years) − 1.",
        ["PAT CAGR", "Share count changes (buybacks accelerate, dilution decelerates)"],
        "EPS CAGR consistently exceeding PAT CAGR signals ongoing buybacks; EPS CAGR trailing "
        "PAT CAGR signals ongoing dilution — neither is automatically good or bad without context.",
        "Buyback-heavy mature businesses often show EPS CAGR > PAT CAGR by design.",
        "A single large one-time buyback can distort EPS CAGR in a way that will not repeat.",
    ),
    "fcf_cagr": MetricCard(
        "fcf_cagr", 5, "Free Cash Flow CAGR",
        "Compounded annual growth rate of Free Cash Flow across the analysis window.",
        "FCF CAGR = (FCF_end / FCF_start)^(1/years) − 1.",
        ["Operating Cash Flow growth", "Capex intensity trend", "Working capital trend"],
        "FCF CAGR trailing badly behind Revenue/PAT CAGR over multiple years is a structural "
        "cash-conversion problem, not a one-period anomaly — treat it as more diagnostic than "
        "any single period's PAT-vs-OCF gap.",
        "Capital-intensive expansion-phase businesses can show negative FCF CAGR for years "
        "even while Revenue/PAT CAGR looks strong — this is expected during a build-out phase.",
        "A large working-capital release in the final year of the window can flatter FCF CAGR "
        "without reflecting a repeatable trend.",
    ),
}


def all_metrics() -> dict[str, MetricCard]:
    merged: dict[str, MetricCard] = {}
    for module in (INCOME_STATEMENT_METRICS, BALANCE_SHEET_METRICS, CASH_FLOW_METRICS, RATIO_METRICS):
        merged.update(module)
    return merged


def get_metric(key: str) -> MetricCard | None:
    return all_metrics().get(key)
