"""Versioned commercial-bank valuation curriculum."""
from __future__ import annotations
from financials_valuation.schema import KPIKnowledge, SectorValuationModel, ValuationMethodRule

def _k(key, name, definition, formula, unit, why, causal, valuation, limitations=""):
    return KPIKnowledge(key, name, definition, formula, unit, "Quarterly/Annual",
        ("RBI", "NSE/BSE filing", "Audited financial statements"), why, tuple(causal), valuation,
        limitations or "Compare definitions and consolidation scope across periods.", ("VALIDATED", "TRUSTED"))

BANK_KPIS = (
 _k("loans", "Advances", "Gross customer lending", "Reported advances", "INR million", "Earning-asset base", ("loans -> interest_income",), "Growth feeds NII but consumes capital"),
 _k("loan_growth", "Loan Growth", "Change in advances", "closing_loans/opening_loans-1", "%", "Growth and underwriting intensity", ("loan_growth -> seasoning -> slippages",), "Only valuable when risk-adjusted ROE exceeds cost of equity"),
 _k("deposits", "Deposits", "Customer funding base", "Reported deposits", "INR million", "Funding capacity", ("deposits -> funding_base",), "Franchise quality affects sustainable multiple"),
 _k("deposit_growth", "Deposit Growth", "Change in deposits", "closing_deposits/opening_deposits-1", "%", "Funding growth versus loans", ("deposit_growth -> funding_mix -> NIM",), "Deposit constraint can cap growth"),
 _k("casa", "CASA Ratio", "Current and savings deposits / deposits", "CASA/deposits", "%", "Low-cost funding proxy", ("CASA -> funding_cost -> NIM",), "Account balances and pricing matter beyond ratio"),
 _k("cost_of_deposits", "Cost of Deposits", "Interest expense on deposits / average deposits", "deposit_interest/average_deposits", "%", "Core funding cost", ("cost_of_deposits -> NIM",), "Repricing lag matters"),
 _k("yield_on_advances", "Yield on Advances", "Loan interest / average advances", "loan_interest/average_advances", "%", "Asset pricing", ("yield_on_advances -> spread",), "Mix and interest reversals distort"),
 _k("nim", "NIM", "NII / average earning assets", "NII/average_earning_assets", "%", "Core spread profitability", ("NIM -> NII -> PAT -> ROA -> ROE",), "Higher sustainable NIM can support P/B"),
 _k("nii_growth", "NII Growth", "Change in net interest income", "closing_NII/opening_NII-1", "%", "Core income growth", ("NII -> operating_profit",), "Separate volume from spread"),
 _k("cost_to_income", "Cost-to-Income", "Operating expenses / operating income", "opex/operating_income", "%", "Operating efficiency", ("cost_to_income -> pre_provision_profit",), "Investment cycles can temporarily elevate cost"),
 _k("gnpa", "GNPA Ratio", "Gross NPA / advances", "gross_NPA/gross_advances", "%", "Recognized asset stress", ("GNPA -> provisions -> credit_cost",), "Backward-looking and recognition-policy sensitive"),
 _k("nnpa", "NNPA Ratio", "Net NPA / net advances", "net_NPA/net_advances", "%", "Unprovided residual stress", ("NNPA -> capital_risk",), "Affected by provision coverage"),
 _k("slippage", "Slippage Ratio", "New NPAs / opening standard loans", "new_NPA/opening_standard_loans", "%", "Forward stress formation", ("slippages -> GNPA",), "Recoveries and upgrades also matter"),
 _k("credit_cost", "Credit Cost", "Loan-loss provisions / average loans", "provisions/average_loans", "%", "Earnings impact of credit risk", ("credit_cost -> PAT -> ROA -> ROE",), "Low current credit cost may be unsustainable"),
 _k("pcr", "Provision Coverage", "Provisions / GNPA", "provisions/GNPA", "%", "Loss absorption buffer", ("PCR -> NNPA",), "Write-offs affect comparability"),
 _k("roa", "ROA", "PAT / average assets", "PAT/average_assets", "%", "Bank operating return", ("ROA -> ROE",), "Leverage converts ROA to ROE"),
 _k("roe", "ROE", "PAT / average equity", "PAT/average_equity", "%", "Return on scarce equity", ("ROE -> justified_PB",), "Use sustainable, normalized ROE"),
 _k("cet1", "CET1", "Core equity / RWA", "CET1_capital/RWA", "%", "Growth and solvency buffer", ("CET1 -> growth_capacity -> dilution_risk",), "Risk weights and regulatory minima change"),
 _k("crar", "CRAR", "Eligible capital / RWA", "regulatory_capital/RWA", "%", "Capital adequacy", ("CRAR -> payout_capacity",), "Composition matters"),
 _k("book_value", "Book Value", "Accounting common equity", "equity/shares", "INR/share", "P/B denominator", ("retained_earnings -> book_value",), "Provisioning quality determines reliability"),
 _k("tangible_book", "Tangible Book", "Equity less goodwill/intangibles", "tangible_equity/shares", "INR/share", "Loss-absorbing tangible capital", ("tangible_book -> P_TBV",), "Requires reliable intangible adjustments"),
 _k("eps", "EPS", "PAT attributable / diluted shares", "PAT/diluted_shares", "INR/share", "P/E denominator", ("PAT -> EPS",), "Normalize one-offs and dilution"),
)

METHODS = (
 ValuationMethodRule("PRICE_TO_BOOK", "PRIMARY", "Equity book is the scarce operating capital for a deposit lender.", ("market_price","book_value_per_share"), ("Links price to regulated equity",), ("Depends on honest provisioning",), ("Distorted book value",)),
 ValuationMethodRule("PRICE_TO_TANGIBLE_BOOK", "PRIMARY", "Cross-checks value against tangible loss-absorbing equity.", ("market_price","tangible_book_value_per_share"), ("Removes goodwill",), ("Intangible classification judgment",), ("Tangible equity unavailable",)),
 ValuationMethodRule("PRICE_TO_EARNINGS", "PRIMARY_CROSS_CHECK", "Tests price against normalized sustainable bank earnings.", ("market_price","normalized_eps"), ("Simple earnings cross-check",), ("Credit cycle distorts earnings",), ("Negative or non-normalized earnings",)),
 ValuationMethodRule("JUSTIFIED_PB", "SECONDARY", "Derives P/B from sustainable ROE, growth and required return.", ("roe","growth","cost_of_equity"), ("Economically interpretable",), ("Highly assumption-sensitive",), ("cost_of_equity <= growth",)),
 ValuationMethodRule("RESIDUAL_INCOME", "SECONDARY", "Values current book plus present value of excess equity returns.", ("book_value","roe","cost_of_equity","growth"), ("Bank-appropriate equity valuation",), ("Terminal assumptions dominate",), ("cost_of_equity <= growth",)),
 ValuationMethodRule("DDM", "CROSS_CHECK", "Useful when payout is observable and sustainable.", ("dividend","cost_of_equity","growth"), ("Direct equity cash return",), ("Poor for constrained or changing payout",), ("Missing sustainable dividend",)),
 ValuationMethodRule("EV_EBITDA", "INAPPROPRIATE", "Debt and interest expense are operating inputs for banks.", (), (), ("Enterprise value is not economically comparable",), ("Always inappropriate as primary bank method",)),
)

BANKING_MODEL = SectorValuationModel(
 "FINANCIALS.BANKS.COMMERCIAL", "Commercial Banks", "COMMERCIAL_BANK",
 ("Private bank", "Public-sector bank", "Universal bank"),
 "Funding and regulated equity are deployed into risk-bearing earning assets; spread, fees, costs and credit losses determine returns.",
 ("Loan growth", "NIM", "Fee income"), ("Funding cost", "Operating cost", "Credit cost"),
 "Deposits and wholesale funding support assets; CET1 and CRAR constrain growth.", ("RBI prudential rules", "CET1/CRAR", "Liquidity requirements", "Asset classification"),
 BANK_KPIS, METHODS, ("Sustainable ROE", "Growth", "Cost of equity", "Asset quality", "Capital headroom"),
 ("Credit-cycle normalization", "Provisioning distortion", "Capital dilution", "Funding pressure", "Regulatory change"),
 ("Loan growth", "Deposit growth", "NIM", "Credit cost", "ROA", "ROE", "CET1", "Cost of equity"),
 ("Deposit growth", "CASA", "NIM", "Slippages", "Credit cost", "ROA", "ROE", "CET1"),
 ("Low P/B means cheap", "High ROE is automatically sustainable", "Low current NPA proves low future risk", "Historical average equals fair value", "EV/EBITDA is meaningful for banks"),
 ("RBI", "NSE", "BSE", "Audited annual report", "Regulatory disclosures"), "2026-08-15", .95,
)
