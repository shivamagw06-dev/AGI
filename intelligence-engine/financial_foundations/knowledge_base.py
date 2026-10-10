"""Financial Foundations Knowledge Base — Modules 1-5 concepts.

Structured concepts (not prose notes) covering: why companies exist, the
accounting equation, double-entry mechanics, chart-of-accounts
classification, and revenue/expense recognition. This is the
declarative half of Phase 1; ``accounting_rules.py`` is the executable
half.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConceptCard:
    key: str
    module: int
    title: str
    definition: str
    business_meaning: str
    common_mistake: str
    example: str


MODULE_1_BIRTH_OF_A_COMPANY: dict[str, ConceptCard] = {
    "why_companies_exist": ConceptCard(
        "why_companies_exist", 1, "Why Companies Exist",
        "A company is a legal entity created to pool capital, limit owner liability, and "
        "conduct business separately from its owners.",
        "Separating the business from its owners lets capital, risk, and management be "
        "structured independently of any one person's life or wealth.",
        "Treating the owner's personal cash and the company's cash as interchangeable — "
        "in accounting they are always separate entities.",
        "A founder investing ₹10,00,000 creates a company distinct from the founder; the "
        "company now owns the cash, and the founder owns equity in the company.",
    ),
    "legal_entity": ConceptCard(
        "legal_entity", 1, "Legal Entity",
        "An organisation recognised by law as having its own rights and obligations, "
        "separate from its owners.",
        "Enables the company to own assets, incur debts, sue and be sued, and continue "
        "beyond any single owner's involvement.",
        "Assuming a sole proprietor and a company are accounted for identically — a "
        "company's books never include the owner's personal assets.",
        "ABC Manufacturing Pvt Ltd can own machinery and owe a bank loan in its own name.",
    ),
    "owners_and_equity": ConceptCard(
        "owners_and_equity", 1, "Owners and Equity",
        "Owners (shareholders) hold Equity — the residual claim on the company after all "
        "liabilities are settled.",
        "Equity is not a fixed number; it grows with reinvested profit (Retained Earnings) "
        "and shrinks with losses or dividends.",
        "Believing Equity is 'owner's cash' sitting somewhere — it is an accounting balance, "
        "not a cash account.",
        "A founder who invests ₹10,00,000 for shares holds Equity of ₹10,00,000 on day one.",
    ),
    "share_capital": ConceptCard(
        "share_capital", 1, "Share Capital",
        "The amount owners have contributed to the company in exchange for ownership shares.",
        "Represents permanent capital that does not need to be repaid — unlike debt.",
        "Confusing Share Capital with Retained Earnings — Share Capital is what owners put "
        "in; Retained Earnings is what the business has since earned and kept.",
        "Founder invests ₹10,00,000 → Share Capital = ₹10,00,000.",
    ),
    "retained_earnings": ConceptCard(
        "retained_earnings", 1, "Retained Earnings",
        "The cumulative Net Income the company has earned since inception, minus all "
        "dividends ever declared — the portion of profit reinvested in the business rather "
        "than distributed to shareholders.",
        "Retained Earnings is an Equity account that grows every period a company is "
        "profitable and shrinks when it declares dividends or posts a loss; it is the "
        "accounting link between the Income Statement and the Balance Sheet — Net Income "
        "flows into Equity through this account at period close, not through Cash directly.",
        "Treating Retained Earnings as a pool of cash sitting in a bank account — it is an "
        "accounting balance representing accumulated claims on the company's assets, not "
        "cash itself; the actual cash may already be invested in machinery, inventory, or "
        "receivables.",
        "A company earns ₹5,00,000 Net Income in Year 1 and declares no dividend: Retained "
        "Earnings rises from ₹0 to ₹5,00,000. If it then pays a ₹1,00,000 dividend in Year 2, "
        "Retained Earnings falls by that ₹1,00,000 even though Year 2's own profit may be higher.",
    ),
    "debt": ConceptCard(
        "debt", 1, "Debt",
        "Capital borrowed from lenders that must be repaid, usually with interest.",
        "Debt is a Liability, not Equity — lenders have a prior claim on assets over "
        "shareholders and are owed a fixed return regardless of company performance.",
        "Recording loan proceeds as revenue or income — borrowed cash is never earned income.",
        "Taking a ₹5,00,000 bank loan increases Cash and Bank Loan (liability) by ₹5,00,000; "
        "it does not touch Revenue.",
    ),
    "accounting_equation": ConceptCard(
        "accounting_equation", 1, "The Accounting Equation",
        "Assets = Liabilities + Equity — this holds after every single transaction, always.",
        "It is the mathematical guarantee that a double-entry ledger is internally "
        "consistent: everything the company owns is claimed by either lenders or owners.",
        "Believing the equation is only checked at year-end — it must hold after EVERY "
        "transaction, not just at reporting dates.",
        "Founder invests ₹10,00,000 cash: Assets (Cash ₹10,00,000) = Liabilities (₹0) + "
        "Equity (Share Capital ₹10,00,000). The equation balances immediately.",
    ),
}

MODULE_2_DOUBLE_ENTRY: dict[str, ConceptCard] = {
    "debit": ConceptCard(
        "debit", 2, "Debit",
        "The left side of a journal entry; increases Assets and Expenses, decreases "
        "Liabilities, Equity, and Revenue.",
        "'Debit' is not inherently good or bad — it simply means 'left side'; its effect "
        "depends entirely on the account type.",
        "Assuming Debit always means 'increase' — it only increases Asset and Expense accounts.",
        "Buying furniture for cash debits Furniture (an asset increases) and credits Cash "
        "(an asset decreases).",
    ),
    "credit": ConceptCard(
        "credit", 2, "Credit",
        "The right side of a journal entry; increases Liabilities, Equity, and Revenue, "
        "decreases Assets and Expenses.",
        "Every transaction's credits must equal its debits — this is what 'balancing' means.",
        "Assuming Credit always means 'decrease' — it increases Liability, Equity, and "
        "Revenue accounts.",
        "A founder's cash investment credits Share Capital (equity increases) and debits "
        "Cash (asset increases).",
    ),
    "journal": ConceptCard(
        "journal", 2, "Journal",
        "The chronological, transaction-by-transaction record of every debit and credit — "
        "the 'book of original entry'.",
        "Every business event is captured here first, before it is organised by account.",
        "Skipping the journal and posting directly to accounts — this loses the "
        "transaction-level audit trail.",
        "Journal entry #1: Debit Cash ₹10,00,000; Credit Share Capital ₹10,00,000.",
    ),
    "ledger": ConceptCard(
        "ledger", 2, "Ledger",
        "The journal's entries reorganised by account, showing each account's running balance.",
        "Answers 'what is the balance of Cash right now?' by summarising every journal "
        "entry that touched Cash.",
        "Confusing the Ledger (organised by account) with the Journal (organised by time) "
        "— they contain the same data, organised differently.",
        "The Cash ledger account shows every debit and credit to Cash, in order, with a "
        "running balance after each.",
    ),
    "trial_balance": ConceptCard(
        "trial_balance", 2, "Trial Balance",
        "A listing of every account's balance at a point in time, proving total debits "
        "equal total credits.",
        "The first checkpoint that the double-entry bookkeeping has been done correctly "
        "before statements are built.",
        "Assuming a balanced Trial Balance means there are no errors — it only proves "
        "debits equal credits, not that the right accounts were used.",
        "If Cash (debit ₹10,00,000) and Share Capital (credit ₹10,00,000) are the only "
        "two balances, the Trial Balance totals ₹10,00,000 = ₹10,00,000.",
    ),
}

MODULE_3_CHART_OF_ACCOUNTS: dict[str, ConceptCard] = {
    "assets": ConceptCard(
        "assets", 3, "Assets",
        "Resources the company owns or controls that are expected to provide future "
        "economic benefit.",
        "Assets are what the business HAS — cash, receivables, inventory, and fixed assets.",
        "Classifying an expense as an asset (or vice versa) to manipulate reported profit "
        "— this is a common source of accounting fraud.",
        "Cash, Accounts Receivable, Inventory, and Machinery are all Assets.",
    ),
    "liabilities": ConceptCard(
        "liabilities", 3, "Liabilities",
        "Obligations the company owes to outside parties, to be settled in the future.",
        "Liabilities are what the business OWES — to suppliers, employees, tax authorities, "
        "and lenders.",
        "Forgetting accrued-but-unpaid obligations (like Salary Payable) — a liability "
        "exists the moment the obligation arises, not when cash is paid.",
        "Accounts Payable, Bank Loan, and Tax Payable are all Liabilities.",
    ),
    "equity_accounts": ConceptCard(
        "equity_accounts", 3, "Equity",
        "The owners' residual claim: Assets minus Liabilities.",
        "Equity grows through owner contributions and retained profit; it shrinks through "
        "losses and dividends.",
        "Treating Equity accounts (Share Capital, Retained Earnings) as cash reserves.",
        "Share Capital and Retained Earnings are both Equity accounts.",
    ),
    "revenue_accounts": ConceptCard(
        "revenue_accounts", 3, "Revenue",
        "Value earned from the company's core operations in the period.",
        "Revenue accounts are 'flow' accounts — they measure this period's activity and "
        "are closed to Retained Earnings at year-end.",
        "Recording a loan or capital contribution as Revenue — only value EARNED from "
        "operations is Revenue.",
        "Product Sales and Service Revenue are Revenue accounts.",
    ),
    "expense_accounts": ConceptCard(
        "expense_accounts", 3, "Expenses",
        "The cost of generating this period's Revenue and running the business.",
        "Expense accounts are also 'flow' accounts, closed to Retained Earnings at year-end.",
        "Recording a fixed-asset purchase as an expense — it should be capitalised as an "
        "Asset and depreciated over time instead.",
        "COGS, Salary Expense, and Interest Expense are Expense accounts.",
    ),
}

MODULE_4_REVENUE_RECOGNITION: dict[str, ConceptCard] = {
    "revenue_is_not_cash": ConceptCard(
        "revenue_is_not_cash", 4, "Revenue Is Not Cash",
        "Revenue is recognised when goods/services are delivered to the customer — the "
        "timing of cash receipt is irrelevant to whether revenue exists.",
        "This separation lets the Income Statement measure economic activity even when "
        "customers pay on credit terms.",
        "Assuming a rising Revenue line means rising Cash — a credit-sale-heavy quarter "
        "can show strong Revenue with weak cash collection.",
        "Selling ₹1,00,000 of goods on credit recognises ₹1,00,000 of Revenue today, even "
        "though Cash does not move.",
    ),
    "credit_vs_cash_sales": ConceptCard(
        "credit_vs_cash_sales", 4, "Credit Sales vs Cash Sales",
        "A credit sale creates an Accounts Receivable asset instead of increasing Cash "
        "immediately; a cash sale increases Cash immediately.",
        "The choice of credit terms affects working capital and cash conversion, not "
        "whether or how much Revenue is recognised.",
        "Believing a credit sale is 'less real' revenue than a cash sale — both are "
        "recognised identically on the Income Statement.",
        "A ₹50,000 cash sale and a ₹50,000 credit sale both add ₹50,000 to Revenue; only "
        "the Balance Sheet account that increases (Cash vs Receivable) differs.",
    ),
    "deferred_unearned_revenue": ConceptCard(
        "deferred_unearned_revenue", 4, "Deferred / Unearned Revenue",
        "Cash received from a customer before the related goods/services are delivered — "
        "recorded as a Liability, not Revenue, until the obligation is fulfilled.",
        "Protects the Income Statement from overstating performance for work not yet done.",
        "Recognising Revenue the moment cash is received, regardless of delivery status.",
        "A customer prepays ₹1,00,000 for a service to be delivered next quarter: Cash "
        "increases ₹1,00,000, Unearned Revenue (liability) increases ₹1,00,000 — Revenue "
        "is ₹0 today.",
    ),
}

MODULE_5_EXPENSE_RECOGNITION: dict[str, ConceptCard] = {
    "expenses_before_payment": ConceptCard(
        "expenses_before_payment", 5, "Expenses Happen Before Payment",
        "Under accrual accounting, an expense is recognised when it is incurred, not when "
        "cash is paid.",
        "This lets the Income Statement match costs to the period that benefited from "
        "them, regardless of payment timing.",
        "Assuming an unpaid bill is not yet an expense — it should be accrued the moment "
        "the obligation exists.",
        "Salary earned by employees this month but paid next month is still this month's "
        "Salary Expense, with Salary Payable recording the obligation.",
    ),
    "matching_principle": ConceptCard(
        "matching_principle", 5, "The Matching Principle",
        "Expenses are recognised in the same period as the Revenue they helped generate.",
        "This is why COGS is recognised only when inventory is sold, not when it is purchased.",
        "Expensing an entire inventory purchase immediately instead of matching cost to "
        "the units actually sold.",
        "Buying ₹50,000 of inventory is not an expense; only the ₹30,000 cost of units "
        "actually sold this period becomes COGS.",
    ),
    "expense_categories": ConceptCard(
        "expense_categories", 5, "Expense Categories",
        "COGS (direct cost of goods sold), SG&A/OpEx (running the business), Marketing, "
        "R&D, Interest (cost of debt), and Tax (government's share of profit).",
        "Separating expense categories lets analysts see where a company's cost structure "
        "actually sits — product cost vs overhead vs financing vs tax.",
        "Lumping all costs into one 'expenses' bucket — this hides margin structure (Gross "
        "Margin vs EBITDA margin vs Net margin) from analysis.",
        "COGS reduces Gross Profit; Salary/Rent/Marketing/R&D reduce EBITDA; Interest "
        "reduces PBT; Tax reduces PAT — each sits at a different point in the waterfall.",
    ),
}


def all_concepts() -> dict[str, ConceptCard]:
    merged: dict[str, ConceptCard] = {}
    for module in (
        MODULE_1_BIRTH_OF_A_COMPANY,
        MODULE_2_DOUBLE_ENTRY,
        MODULE_3_CHART_OF_ACCOUNTS,
        MODULE_4_REVENUE_RECOGNITION,
        MODULE_5_EXPENSE_RECOGNITION,
    ):
        merged.update(module)
    return merged


def get_concept(key: str) -> ConceptCard | None:
    return all_concepts().get(key)


def concepts_by_module(module: int) -> dict[str, ConceptCard]:
    return {k: v for k, v in all_concepts().items() if v.module == module}
