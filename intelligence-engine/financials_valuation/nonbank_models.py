"""Versioned curricula for non-bank financial subsectors."""
from __future__ import annotations

from financials_valuation.schema import KPIKnowledge, SectorValuationModel, ValuationMethodRule


def _k(key: str, name: str, why: str, causal: str, valuation: str, unit: str = "decimal") -> KPIKnowledge:
    return KPIKnowledge(key, name, name, f"Reported or deterministically calculated {name}", unit,
        "Quarterly/Annual", ("Regulatory filing", "NSE/BSE filing", "Audited financial statements"),
        why, (causal,), valuation, "Definitions, consolidation scope and cycle position must be comparable.",
        ("VALIDATED", "TRUSTED"))


def _m(method: str, tier: str, reason: str, required: tuple[str, ...], failure: str) -> ValuationMethodRule:
    return ValuationMethodRule(method, tier, reason, required, (reason,),
        ("Sensitive to normalization and point-in-time assumptions.",), (failure,))


def _model(sector_id: str, name: str, subsector: str, economics: str, kpis: tuple[KPIKnowledge, ...],
           methods: tuple[ValuationMethodRule, ...], drivers: tuple[str, ...], risks: tuple[str, ...],
           scenarios: tuple[str, ...], errors: tuple[str, ...]) -> SectorValuationModel:
    return SectorValuationModel(sector_id, name, subsector, (name,), economics, drivers[:3], drivers[3:6] or drivers[:2],
        "Capital, funding and regulatory constraints are operating inputs, not financing afterthoughts.",
        ("Sector regulator", "Capital or solvency requirements", "PIT disclosure requirements"), kpis, methods,
        drivers, risks, scenarios, scenarios, errors,
        ("Sector regulator", "NSE", "BSE", "Audited annual report"), "2026-08-15", .90)


LENDER_KPIS = (
    _k("aum", "Assets Under Management", "Scale of earning assets", "AUM -> interest income", "Growth and scale"),
    _k("aum_growth", "AUM Growth", "Growth intensity", "AUM growth -> seasoning -> credit cost", "Growth quality"),
    _k("asset_yield", "Yield on Assets", "Asset pricing", "asset yield -> spread", "Sustainable spread"),
    _k("funding_cost", "Cost of Borrowing", "Liability pricing", "funding cost -> spread", "Funding resilience"),
    _k("spread", "Lending Spread", "Core unit economics", "spread -> NII -> ROA", "Earnings power"),
    _k("credit_cost", "Credit Cost", "Loss intensity", "credit cost -> PAT -> ROE", "Cycle normalization"),
    _k("gnpa", "GNPA Ratio", "Recognized stress", "GNPA -> provisions", "Book reliability"),
    _k("roa", "ROA", "Asset returns", "ROA x leverage -> ROE", "P/B support"),
    _k("roe", "ROE", "Equity returns", "ROE -> justified P/B", "Excess returns"),
    _k("leverage", "Leverage", "Return and solvency amplifier", "leverage -> ROE and risk", "Required return"),
    _k("capital_adequacy", "Capital Adequacy", "Growth buffer", "capital -> growth capacity", "Dilution risk"),
    _k("liquidity", "Liquidity Buffer", "Refinancing resilience", "liquidity -> funding access", "Tail risk"),
)

LENDER_METHODS = (
    _m("PRICE_TO_BOOK", "PRIMARY", "Book equity funds regulated lending growth.", ("market_price","book_value_per_share"), "Unreliable provisioning"),
    _m("PRICE_TO_EARNINGS", "PRIMARY_CROSS_CHECK", "Normalized earnings cross-check the credit cycle.", ("market_price","normalized_eps"), "Unnormalized earnings"),
    _m("JUSTIFIED_PB", "SECONDARY", "Links sustainable ROE to required return and growth.", ("roe","growth","cost_of_equity"), "cost of equity <= growth"),
    _m("RESIDUAL_INCOME", "SECONDARY", "Values excess returns on equity capital.", ("book_value","roe","cost_of_equity","growth"), "cost of equity <= growth"),
    _m("EV_EBITDA", "INAPPROPRIATE", "Borrowings are an operating input for lenders.", (), "Always inappropriate as primary lender method"),
)

NBFC_MODEL = _model("FINANCIALS.NBFC", "Non-Bank Financial Companies", "NBFC",
    "Borrowed and equity capital are deployed into credit assets; funding cost, spread, losses and leverage determine returns.",
    LENDER_KPIS, LENDER_METHODS, ("AUM growth","Asset yield","Funding cost","Spread","Credit cost","Operating leverage","ROA","ROE","Leverage","Capital adequacy"),
    ("Refinancing","ALM mismatch","Credit cycle","Concentration","Capital dilution"),
    ("AUM growth","Funding cost","Credit cost","ROA","Leverage"),
    ("Treating NBFC deposits like bank CASA", "Ignoring ALM", "Using EV/EBITDA"))

HFC_MODEL = _model("FINANCIALS.HOUSING_FINANCE", "Housing Finance Companies", "HOUSING_FINANCE",
    "Long-duration mortgages are funded through deposits and wholesale liabilities; spreads, LTV, prepayment and ALM drive returns.",
    LENDER_KPIS + (_k("ltv", "Loan-to-Value", "Collateral protection", "LTV -> loss severity", "Credit risk"),
                   _k("prepayment", "Prepayment Rate", "Asset duration", "prepayment -> reinvestment yield", "Spread persistence")),
    LENDER_METHODS, ("Housing loan growth","Asset yield","Funding cost","Spread","Credit cost","Prepayment","LTV","ROA","ROE"),
    ("Property cycle","ALM mismatch","Refinancing","Prepayment","Borrower concentration"),
    ("Loan growth","Funding cost","Spread","Credit cost","LTV"),
    ("Treating HFCs as generic NBFCs", "Ignoring duration mismatch", "Assuming collateral eliminates loss"))

SFB_MODEL = _model("FINANCIALS.BANKS.SMALL_FINANCE", "Small Finance Banks", "SMALL_FINANCE_BANK",
    "A deposit franchise funds granular but often higher-risk lending; funding maturation and credit normalization drive value.",
    LENDER_KPIS + (_k("casa", "CASA Ratio", "Funding franchise", "CASA -> funding cost", "Multiple durability"),),
    LENDER_METHODS, ("Deposit growth","CASA","Loan growth","Spread","Credit cost","ROA","ROE","Capital adequacy"),
    ("Borrower concentration","Funding transition","Credit volatility","Regulation"),
    ("CASA","Spread","Credit cost","ROA","Capital"), ("Applying mature private-bank assumptions", "Ignoring borrower concentration"))

LIFE_KPIS = (
    _k("ape", "Annualized Premium Equivalent", "New business scale", "APE -> VNB", "Growth", "INR million"),
    _k("vnb", "Value of New Business", "Economic value created", "APE x VNB margin -> VNB", "Value creation", "INR million"),
    _k("vnb_margin", "VNB Margin", "New-business profitability", "product mix -> VNB margin", "P/EV support"),
    _k("embedded_value", "Embedded Value", "Adjusted net worth plus in-force value", "in-force cash flows -> EV", "P/EV denominator", "INR million"),
    _k("persistency", "Persistency", "Policy retention", "persistency -> in-force value", "EV durability"),
    _k("premium_growth", "Premium Growth", "Franchise growth", "premium growth -> future VNB", "Growth"),
    _k("solvency", "Solvency Ratio", "Regulatory capital buffer", "solvency -> growth capacity", "Tail risk"),
    _k("protection_mix", "Protection Mix", "Product economics", "mix -> margin and risk", "Margin quality"),
)

LIFE_MODEL = _model("FINANCIALS.INSURANCE.LIFE", "Life Insurance", "LIFE_INSURANCE",
    "Premiums fund long-duration policy obligations; persistency, product mix and assumptions determine embedded value and new-business value.", LIFE_KPIS,
    (_m("PRICE_TO_EMBEDDED_VALUE","PRIMARY","Embedded value captures net worth and in-force value.",("market_price","embedded_value_per_share"),"Unreliable EV assumptions"),
     _m("PRICE_TO_EARNINGS","CROSS_CHECK","Earnings are a secondary accounting cross-check.",("market_price","normalized_eps"),"Earnings not economically representative"),
     _m("EV_EBITDA","INAPPROPRIATE","Insurance liabilities are operating obligations.",(),"Always inappropriate")),
    ("APE growth","VNB","VNB margin","Persistency","Product mix","Solvency"),
    ("Assumption changes","Persistency","Distribution concentration","Solvency","Regulation"),
    ("APE growth","VNB margin","Persistency","Cost of equity"),
    ("Valuing life insurers on P/E alone", "Ignoring EV assumptions", "Treating premium as revenue"))

GENERAL_KPIS = (
    _k("gwp", "Gross Written Premium", "Underwriting scale", "GWP -> earned premium", "Growth", "INR million"),
    _k("claims_ratio", "Claims Ratio", "Loss burden", "claims ratio -> combined ratio", "Underwriting quality"),
    _k("expense_ratio", "Expense Ratio", "Distribution and operating burden", "expense ratio -> combined ratio", "Efficiency"),
    _k("combined_ratio", "Combined Ratio", "Underwriting profit threshold", "claims + expense -> combined ratio", "Profitability"),
    _k("investment_income", "Investment Income", "Float return", "float x yield -> investment income", "Earnings mix", "INR million"),
    _k("reserve_development", "Reserve Development", "Prior-year estimate quality", "reserve development -> earnings", "Book quality"),
    _k("solvency", "Solvency Ratio", "Regulatory buffer", "solvency -> underwriting capacity", "Risk"),
    _k("roe", "ROE", "Equity return", "underwriting + investment return -> ROE", "P/B support"),
)

INSURANCE_METHODS = (
    _m("PRICE_TO_BOOK","PRIMARY","Book and regulatory capital support underwriting capacity.",("market_price","book_value_per_share"),"Inadequate reserves"),
    _m("PRICE_TO_EARNINGS","CROSS_CHECK","Normalized cycle earnings provide a cross-check.",("market_price","normalized_eps"),"Catastrophe or reserve distortion"),
    _m("EV_EBITDA","INAPPROPRIATE","Claims and reserves are operating obligations.",(),"Always inappropriate"),
)
GENERAL_MODEL = _model("FINANCIALS.INSURANCE.GENERAL", "General Insurance", "GENERAL_INSURANCE",
    "Premium pricing, claims, expenses, reserves and float returns determine underwriting and equity returns.", GENERAL_KPIS, INSURANCE_METHODS,
    ("Premium growth","Pricing","Claims ratio","Expense ratio","Combined ratio","Investment yield","Solvency"),
    ("Catastrophe","Reserve deficiency","Price competition","Regulation"),
    ("Premium growth","Combined ratio","Investment yield","Solvency"), ("Ignoring reserve development", "Treating investment income as underwriting profit"))
HEALTH_MODEL = _model("FINANCIALS.INSURANCE.HEALTH", "Health Insurance", "HEALTH_INSURANCE",
    "Premium pricing, medical inflation, claims frequency, distribution and solvency determine value.", GENERAL_KPIS, INSURANCE_METHODS,
    ("Premium growth","Medical inflation","Claims ratio","Expense ratio","Combined ratio","Solvency"),
    ("Medical inflation","Adverse selection","Regulatory pricing","Distribution cost"),
    ("Medical inflation","Claims ratio","Expense ratio","Solvency"), ("Ignoring medical inflation", "Assuming current claims ratios persist"))

AMC_KPIS = (
    _k("aum", "Assets Under Management", "Fee base", "market return + net flows -> AUM", "Revenue base", "INR million"),
    _k("net_flows", "Net Flows", "Organic franchise growth", "net flows -> AUM", "Durable growth", "INR million"),
    _k("fee_yield", "Fee Yield", "Monetization", "AUM x fee yield -> revenue", "Revenue quality"),
    _k("equity_mix", "Equity AUM Mix", "Fee and market sensitivity", "equity mix -> fee yield", "Margin and beta"),
    _k("operating_margin", "Operating Margin", "Scale economics", "revenue - costs -> margin", "Earnings conversion"),
    _k("retention", "Asset Retention", "Franchise durability", "retention -> net flows", "Multiple durability"),
    _k("roe", "ROE", "Capital-light return", "earnings / equity -> ROE", "Quality"),
    _k("fcf", "Free Cash Flow", "Cash conversion", "earnings -> FCF", "DCF support", "INR million"),
)
OPERATING_METHODS = (
    _m("PRICE_TO_EARNINGS","PRIMARY","Normalized earnings capture capital-light economics.",("market_price","normalized_eps"),"Cyclical peak earnings"),
    _m("EV_EBITDA","CROSS_CHECK","Useful where debt and operating profit are conventional.",("enterprise_value","ebitda"),"Non-comparable accounting"),
    _m("DCF","SECONDARY","Cash flows support intrinsic-value scenarios.",("fcf","discount_rate","terminal_growth"),"Immature or unstable cash flow"),
)
AMC_MODEL = _model("FINANCIALS.ASSET_MANAGEMENT", "Asset Management", "ASSET_MANAGEMENT",
    "Market levels and net flows determine AUM; mix and fee yield determine revenue, while scale drives margins and cash flow.", AMC_KPIS, OPERATING_METHODS,
    ("AUM growth","Net flows","Market appreciation","Fee yield","Equity mix","Operating margin","Retention"),
    ("Market decline","Fee compression","Outflows","Key-person risk","Distribution change"),
    ("Net flows","Market return","Fee yield","Operating margin"), ("Confusing market appreciation with organic flows", "Ignoring fee compression"))

BROKER_KPIS = (
    _k("active_clients", "Active Clients", "Monetizable user base", "clients x revenue/client -> revenue", "Scale"),
    _k("trading_volume", "Trading Volume", "Activity base", "volume x take rate -> brokerage", "Cycle exposure"),
    _k("market_share", "Market Share", "Competitive position", "share -> volume", "Growth durability"),
    _k("revenue_per_client", "Revenue per Client", "Monetization", "revenue / clients", "Unit economics"),
    _k("operating_margin", "Operating Margin", "Operating leverage", "revenue growth -> margin", "Earnings beta"),
    _k("distribution_aum", "Distribution AUM", "Recurring revenue base", "AUM x fee -> revenue", "Diversification", "INR million"),
)
BROKER_MODEL = _model("FINANCIALS.BROKER", "Stock Brokers and Capital Markets", "BROKER",
    "Clients and activity drive transactional revenue; balances and distribution add income, while fixed technology costs create cycle-sensitive operating leverage.", BROKER_KPIS, OPERATING_METHODS,
    ("Active clients","Trading volume","Market share","Revenue per client","Operating leverage","Distribution"),
    ("Market cycle","Pricing pressure","Regulation","Technology outage"),
    ("Trading volume","Market share","Revenue per client","Operating margin"), ("Annualizing peak trading activity", "Ignoring derivatives concentration"))

EXCHANGE_MODEL = _model("FINANCIALS.EXCHANGE_INFRASTRUCTURE", "Exchanges and Market Infrastructure", "EXCHANGE_INFRASTRUCTURE",
    "Network effects and regulatory licenses monetize transactions, data, listings and clearing with high incremental margins.",
    BROKER_KPIS + (_k("data_revenue", "Data Revenue", "Recurring information revenue", "users x data fee -> revenue", "Diversification", "INR million"),
                   _k("cash_conversion", "Cash Conversion", "Earnings quality", "FCF / earnings", "DCF quality")), OPERATING_METHODS,
    ("Trading volume","Market share","Transaction pricing","Data revenue","Operating leverage","Cash conversion"),
    ("Regulation","Volume decline","Technology failure","Competitive venue"),
    ("Volume","Market share","Pricing","Operating margin"), ("Ignoring regulatory price caps", "Assuming network effects are permanent"))

FINTECH_KPIS = (
    _k("tpv", "Total Payment Value", "Transaction base", "transactions x ticket size -> TPV", "Scale", "INR million"),
    _k("tpv_growth", "TPV Growth", "Adoption", "TPV growth -> revenue potential", "Growth"),
    _k("take_rate", "Take Rate", "Monetization", "revenue / TPV", "Revenue quality"),
    _k("gross_margin", "Gross Margin", "Unit economics", "gross profit / revenue", "EV/gross profit"),
    _k("contribution_margin", "Contribution Margin", "Post-variable-cost economics", "contribution / revenue", "Path to profit"),
    _k("retention", "Retention", "Cohort durability", "retention -> LTV", "Growth quality"),
    _k("cash_burn", "Cash Burn", "Funding need", "cash outflow -> runway", "Dilution risk", "INR million"),
)
FINTECH_METHODS = (
    _m("EV_SALES","PRIMARY_WHEN_UNPROFITABLE","Revenue scale is useful only with take-rate and margin context.",("enterprise_value","revenue"),"No credible monetization"),
    _m("EV_GROSS_PROFIT","PRIMARY_CROSS_CHECK","Gross profit controls for pass-through revenue.",("enterprise_value","gross_profit"),"Unreliable gross profit"),
    _m("PRICE_TO_EARNINGS","ONLY_WHEN_PROFITABLE","P/E becomes meaningful after normalized profitability.",("market_price","normalized_eps"),"Negative earnings"),
    _m("DCF","ONLY_WHEN_MATURE","Cash-flow valuation requires credible mature economics.",("fcf","discount_rate","terminal_growth"),"Unstable cash flows"),
)
FINTECH_MODEL = _model("FINANCIALS.FINTECH_PAYMENTS", "FinTech and Payments", "FINTECH_PAYMENTS",
    "Payment volume, take rate and unit economics determine monetization; cash burn and regulation constrain the path to durable free cash flow.", FINTECH_KPIS, FINTECH_METHODS,
    ("TPV growth","Transactions","Take rate","Gross margin","Contribution margin","Retention","Cash burn"),
    ("Regulation","Subsidy dependence","Competition","Cash runway","Fraud"),
    ("TPV growth","Take rate","Contribution margin","Cash burn"), ("Equating TPV with revenue", "Using P/E while loss-making"))

PAYMENTS_BANK_MODEL = _model("FINANCIALS.BANKS.PAYMENTS", "Payments Banks and Banking Platforms", "PAYMENTS_BANK",
    "Payments and restricted banking economics combine transaction monetization, float income, regulation and unit economics.", FINTECH_KPIS, FINTECH_METHODS,
    ("Transactions","TPV","Take rate","Float income","Contribution margin","Capital"),
    ("Regulatory restrictions","Monetization","Cash burn","Fraud"),
    ("TPV","Take rate","Float yield","Contribution margin"), ("Applying commercial-bank P/B automatically", "Ignoring regulatory restrictions"))

DIVERSIFIED_KPIS = (
    _k("segment_value", "Segment Value", "Value by economic business", "segment KPI x segment method -> value", "SOTP", "INR million"),
    _k("net_debt", "Net Debt", "Claim ahead of equity", "gross debt - cash", "Equity bridge", "INR million"),
    _k("cross_holdings", "Cross Holdings", "Non-operating assets", "stake x market value", "SOTP", "INR million"),
    _k("holdco_discount", "Holding Company Discount", "Friction adjustment", "gross SOTP x discount", "Equity value"),
)
DIVERSIFIED_MODEL = _model("FINANCIALS.DIVERSIFIED", "Diversified Financial Services", "DIVERSIFIED_FINANCIALS",
    "Each segment is valued with its own economic method before net debt, cross-holdings and justified holding-company adjustments.", DIVERSIFIED_KPIS,
    (_m("SOTP","PRIMARY","Different financial businesses require segment-specific methods.",("segment_1_value","segment_2_value","segment_3_value","net_debt","holdco_discount"),"Missing segment evidence"),
     _m("BLENDED_MULTIPLE","INAPPROPRIATE","One multiple obscures distinct segment economics.",(),"Always inappropriate without segment proof")),
    ("Segment growth","Segment returns","Capital allocation","Net debt","Cross holdings"),
    ("Double counting","Opaque transfer pricing","Holdco discount","Capital allocation"),
    ("Segment values","Net debt","Holdco discount"), ("Applying one multiple to every segment", "Unexplained holdco discount"))

MODELS = {model.subsector: model for model in (
    SFB_MODEL, PAYMENTS_BANK_MODEL, NBFC_MODEL, HFC_MODEL, LIFE_MODEL, GENERAL_MODEL, HEALTH_MODEL,
    AMC_MODEL, BROKER_MODEL, EXCHANGE_MODEL, FINTECH_MODEL, DIVERSIFIED_MODEL,
)}
