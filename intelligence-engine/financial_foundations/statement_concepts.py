"""Module 6/7/8 — line-item concepts for the Financial Education Layer.

Every Income Statement / Balance Sheet / Cash Flow line gets a
definition, formula, business meaning, and common mistake — not just a
label. This is what `education.py` serves back to a learner or to Ask.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptCard:
    key: str
    title: str
    definition: str
    formula: str
    business_meaning: str
    common_mistake: str
    example: str


INCOME_STATEMENT_CONCEPTS: dict[str, ConceptCard] = {
    "revenue": ConceptCard(
        "revenue", "Revenue",
        "The value of goods/services delivered to customers in the period.",
        "Revenue = Σ(units delivered × price) recognised on delivery, regardless of cash timing.",
        "The top line — the size of the business's economic activity this period.",
        "Confusing revenue with cash collected; a credit sale is still revenue.",
        "Selling ₹1,00,000 of goods on credit is ₹1,00,000 of revenue today, even though "
        "cash has not moved.",
    ),
    "cogs": ConceptCard(
        "cogs", "Cost of Goods Sold (COGS)",
        "The direct cost of the inventory/services sold in the period.",
        "COGS = Opening Inventory + Purchases − Closing Inventory.",
        "Matches the cost of what was sold against the revenue it generated (matching principle).",
        "Expensing the full cost of inventory purchased, rather than only the cost of what was sold.",
        "Buying ₹50,000 of inventory is not COGS; COGS is only recognised when that inventory is sold.",
    ),
    "gross_profit": ConceptCard(
        "gross_profit", "Gross Profit",
        "Revenue remaining after covering the direct cost of goods sold.",
        "Gross Profit = Revenue − COGS.",
        "Measures pricing power and product-level economics before overhead.",
        "Treating Gross Profit as free cash — operating expenses and financing costs still remain.",
        "Revenue ₹10,00,000, COGS ₹6,00,000 → Gross Profit ₹4,00,000 (40% gross margin).",
    ),
    "operating_expense": ConceptCard(
        "operating_expense", "Operating Expenses (OpEx)",
        "Costs of running the business excluding COGS — salaries, rent, marketing, R&D.",
        "OpEx = Salary + Rent + Marketing + R&D + other SG&A.",
        "Reflects the cost of the organisation needed to sell and support the product.",
        "Capitalising what should be expensed (or vice versa) to flatter near-term profit.",
        "Salary Expense of ₹2,00,000 and Rent of ₹50,000 are both OpEx, reducing EBITDA.",
    ),
    "ebitda": ConceptCard(
        "ebitda", "EBITDA",
        "Operating earnings before depreciation, amortisation, interest and tax.",
        "EBITDA = Gross Profit − Operating Expenses (= Revenue − COGS − OpEx).",
        "Measures core operating profitability before financing structure and accounting "
        "policy choices (depreciation method, tax jurisdiction, capital structure).",
        "Treating EBITDA as equivalent to cash flow — it ignores working capital and capex.",
        "Gross Profit ₹4,00,000 − OpEx ₹2,50,000 = EBITDA ₹1,50,000.",
    ),
    "depreciation": ConceptCard(
        "depreciation", "Depreciation",
        "The non-cash allocation of a fixed asset's cost over its useful life.",
        "Depreciation = (Cost − Salvage Value) / Useful Life (straight-line, simplest method).",
        "Spreads the cost of long-lived assets over the periods that benefit from them, "
        "instead of expensing the full cost when purchased.",
        "Believing depreciation reduces cash — it reduces PAT but is added back in the Cash Flow Statement.",
        "A ₹5,00,000 machine with a 5-year life depreciates ₹1,00,000 per year — this reduces "
        "EBIT and PAT but never touches Cash directly.",
    ),
    "ebit": ConceptCard(
        "ebit", "EBIT (Operating Profit)",
        "Earnings before interest and tax — profit from operations after depreciation.",
        "EBIT = EBITDA − Depreciation (and Amortisation).",
        "The cleanest measure of how profitable the underlying business is, before capital "
        "structure (debt) and tax jurisdiction distort the picture.",
        "Comparing EBIT across companies with very different depreciation policies without adjusting.",
        "EBITDA ₹1,50,000 − Depreciation ₹1,00,000 = EBIT ₹50,000.",
    ),
    "interest": ConceptCard(
        "interest", "Interest Expense",
        "The cost of servicing borrowed capital for the period.",
        "Interest Expense ≈ Average Debt Balance × Interest Rate.",
        "Shows how capital structure (how much debt the company carries) affects profit "
        "available to shareholders.",
        "Ignoring interest when comparing companies with very different leverage.",
        "A ₹10,00,000 loan at 10% costs roughly ₹1,00,000 of Interest Expense per year.",
    ),
    "pbt": ConceptCard(
        "pbt", "Profit Before Tax (PBT)",
        "Profit after all operating and financing costs, before the tax charge.",
        "PBT = EBIT − Interest Expense (+ other non-operating items).",
        "The taxable base from which the government's share is calculated.",
        "Forgetting non-operating items (e.g. one-off gains/losses) that also sit above PBT.",
        "EBIT ₹50,000 − Interest ₹10,000 = PBT ₹40,000.",
    ),
    "tax": ConceptCard(
        "tax", "Tax Expense",
        "The income tax charge on this period's pre-tax profit.",
        "Tax Expense = PBT × effective tax rate.",
        "The government's claim on profit before shareholders receive their share.",
        "Confusing the statutory tax rate with the effective tax rate (which reflects "
        "deductions, credits, and deferred tax).",
        "PBT ₹40,000 at a 25% effective rate → Tax Expense ₹10,000.",
    ),
    "pat": ConceptCard(
        "pat", "Profit After Tax (PAT / Net Income)",
        "The bottom line — profit belonging to shareholders after every cost, including tax.",
        "PAT = PBT − Tax Expense.",
        "The starting point for Retained Earnings and for the indirect Cash Flow Statement — "
        "but PAT is an accounting number, not a cash number.",
        "Assuming PAT equals the cash generated by the business — depreciation, working "
        "capital, and non-cash items all cause PAT and Operating Cash Flow to diverge.",
        "PBT ₹40,000 − Tax ₹10,000 = PAT ₹30,000. This ₹30,000 flows into Retained Earnings "
        "at year-end close, not directly into Cash.",
    ),
}

BALANCE_SHEET_CONCEPTS: dict[str, ConceptCard] = {
    "current_assets": ConceptCard(
        "current_assets", "Current Assets",
        "Assets expected to convert to cash or be used within one year.",
        "Current Assets = Cash + Accounts Receivable + Inventory + Prepaid Expenses.",
        "Measures near-term liquidity available to run the business.",
        "Treating Inventory as equivalent to Cash — it must first be sold and collected.",
        "Cash ₹2,00,000 + Receivables ₹50,000 + Inventory ₹1,00,000 = Current Assets ₹3,50,000.",
    ),
    "non_current_assets": ConceptCard(
        "non_current_assets", "Non-current Assets (Net PPE)",
        "Long-lived productive assets, net of accumulated depreciation.",
        "Net PPE = Land + Machinery + Furniture − Accumulated Depreciation.",
        "The productive capacity the business has invested in for the long term.",
        "Reporting PPE at gross cost without netting off Accumulated Depreciation.",
        "Machinery ₹5,00,000 − Accumulated Depreciation ₹1,00,000 = Net PPE ₹4,00,000.",
    ),
    "current_liabilities": ConceptCard(
        "current_liabilities", "Current Liabilities",
        "Obligations due within one year.",
        "Current Liabilities = Accounts Payable + Salary/Interest/Tax Payable + Unearned Revenue.",
        "Shows near-term claims on the business's cash and resources.",
        "Ignoring Unearned Revenue as a liability because cash was already received.",
        "Payables ₹80,000 + Salary Payable ₹20,000 = Current Liabilities ₹1,00,000.",
    ),
    "long_term_liabilities": ConceptCard(
        "long_term_liabilities", "Long-term Liabilities",
        "Obligations due beyond one year, typically borrowed capital.",
        "Long-term Liabilities = Bank Loan (non-current portion) + other long-term debt.",
        "Reflects the company's structural leverage and future repayment obligations.",
        "Treating all debt as equally risky regardless of maturity or covenant structure.",
        "A ₹5,00,000 bank loan repayable over 5 years sits in Long-term Liabilities.",
    ),
    "equity": ConceptCard(
        "equity", "Shareholders' Equity",
        "The owners' residual claim on the business after all liabilities are settled.",
        "Equity = Share Capital + Retained Earnings (+ Reserves).",
        "Represents accumulated owner investment plus reinvested profit.",
        "Assuming Retained Earnings is cash sitting in the bank — it is an accounting "
        "balance, not a cash reserve.",
        "Share Capital ₹10,00,000 + Retained Earnings ₹30,000 = Equity ₹10,30,000.",
    ),
    "accounting_equation": ConceptCard(
        "accounting_equation", "Accounting Equation",
        "The identity that always holds for a double-entry ledger.",
        "Assets = Liabilities + Equity.",
        "Every transaction preserves this balance — it is the mathematical proof that the "
        "books are internally consistent.",
        "Believing the equation can be temporarily out of balance — a true double-entry "
        "ledger never allows this.",
        "If Assets = ₹11,30,000 and Liabilities = ₹1,00,000, Equity must be exactly ₹10,30,000.",
    ),
}

CASH_FLOW_CONCEPTS: dict[str, ConceptCard] = {
    "operating_cash_flow": ConceptCard(
        "operating_cash_flow", "Operating Cash Flow",
        "Cash generated (or used) by the core business, adjusted from PAT for non-cash "
        "items and working-capital movements.",
        "Operating CF = PAT + Depreciation ± Δ Working Capital (indirect method).",
        "Shows whether the business's day-to-day operations actually generate cash, "
        "independent of accounting profit.",
        "Assuming Operating Cash Flow always tracks PAT — rising receivables or inventory "
        "can make Operating CF fall even while PAT rises.",
        "PAT ₹30,000 + Depreciation ₹1,00,000 − Increase in Receivables ₹20,000 = "
        "Operating CF ₹1,10,000.",
    ),
    "investing_cash_flow": ConceptCard(
        "investing_cash_flow", "Investing Cash Flow",
        "Cash used to acquire, or received from disposing of, long-term assets.",
        "Investing CF = − Capex + Proceeds from asset sales + other investment flows.",
        "Shows how much the business is reinvesting in its future productive capacity.",
        "Confusing depreciation (an Income Statement non-cash charge) with capex (an "
        "actual cash outflow reported here).",
        "Buying ₹5,00,000 of machinery for cash is a −₹5,00,000 Investing outflow, unrelated "
        "to that period's Depreciation Expense.",
    ),
    "financing_cash_flow": ConceptCard(
        "financing_cash_flow", "Financing Cash Flow",
        "Cash flows between the business and its capital providers — lenders and shareholders.",
        "Financing CF = Debt raised − Debt repaid + Equity raised − Dividends paid.",
        "Shows how the business is funding itself and returning capital to investors.",
        "Recording loan proceeds as revenue — borrowed cash is a financing inflow, never income.",
        "Taking a ₹5,00,000 bank loan is a +₹5,00,000 Financing inflow, with zero Income "
        "Statement effect.",
    ),
    "working_capital": ConceptCard(
        "working_capital", "Working Capital",
        "The capital tied up in the operating cycle — funding receivables and inventory "
        "net of payables.",
        "Working Capital = (Accounts Receivable + Inventory) − Accounts Payable.",
        "A growing business often needs MORE working capital even while profitable — this "
        "is why PAT can rise while Operating Cash Flow falls.",
        "Believing that growth is automatically cash-generative — often the opposite is true "
        "for working-capital-intensive businesses.",
        "If Receivables and Inventory grow faster than Payables, cash gets trapped in the "
        "operating cycle even as PAT rises.",
    ),
}


def all_concepts() -> dict[str, ConceptCard]:
    merged: dict[str, ConceptCard] = {}
    merged.update(INCOME_STATEMENT_CONCEPTS)
    merged.update(BALANCE_SHEET_CONCEPTS)
    merged.update(CASH_FLOW_CONCEPTS)
    return merged


def get_concept(key: str) -> ConceptCard | None:
    return all_concepts().get(key)
