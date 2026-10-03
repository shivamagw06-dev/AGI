"""Section A — Accounting (Q1-5).

Every answer is produced by actually running Phase 1's
(``financial_foundations``) deterministic engine — journal entries,
ledger, trial balance, and financial statements — not narrated from
memory.
"""

from __future__ import annotations

from financial_foundations.accounting_rules import build_journal_entry
from financial_foundations.chart_of_accounts import classify
from financial_foundations.journal import Ledger
from financial_foundations.linkage_engine import explain_transaction_linkage
from financial_foundations.statement_builder import build_balance_sheet, build_all_statements
from institutional_accounting_exam.schema import ExamAnswer, ExamItem


def _q1_founder_investment() -> ExamAnswer:
    ledger = Ledger()
    entry = ledger.record("founder_investment", 5_000_000, period=1)
    trial_balance = ledger.trial_balance(through_period=1)
    balance_sheet = build_balance_sheet(ledger, 1)

    cash_ok = balance_sheet["assets"]["current_assets"]["cash"] == 5_000_000
    equity_ok = balance_sheet["equity"]["share_capital"] == 5_000_000
    liabilities_zero = balance_sheet["liabilities"]["total_liabilities"] == 0

    answer = (
        f"Journal Entry: Debit Cash ₹50,00,000; Credit Share Capital ₹50,00,000 (entry {entry.entry_id}, "
        f"balanced: {entry.is_balanced()}).\n"
        f"Ledger: Cash account debited ₹50,00,000; Share Capital account credited ₹50,00,000.\n"
        f"Trial Balance: Cash ₹50,00,000 (debit) = Share Capital ₹50,00,000 (credit) — "
        f"balances: {ledger.trial_balance_is_balanced(through_period=1)}.\n"
        f"Opening Balance Sheet: Assets ₹{balance_sheet['assets']['total_assets']:,.0f} = "
        f"Liabilities ₹{balance_sheet['liabilities']['total_liabilities']:,.0f} + "
        f"Equity ₹{balance_sheet['equity']['total_equity']:,.0f}. "
        f"No liabilities exist because the founder contributed capital, not debt — the accounting "
        f"equation is established at the moment the company is born."
    )
    return ExamAnswer(
        answer_text=answer,
        evidence={"trial_balance": trial_balance, "balance_sheet": balance_sheet},
        accounting_checks={
            "journal_entry_balanced": entry.is_balanced(),
            "trial_balance_balanced": ledger.trial_balance_is_balanced(through_period=1),
            "cash_correct": cash_ok,
            "share_capital_correct": equity_ok,
            "no_liabilities": liabilities_zero,
            "accounting_equation_holds": balance_sheet["accounting_equation"]["balances"],
        },
        interpretation_keypoints_expected=["debit", "credit", "cash", "share capital", "accounting equation", "balance"],
        interpretation_keypoints_matched=[k for k in ["debit", "credit", "cash", "share capital", "accounting equation", "balance"] if k in answer.lower()],
    )


def _q2_machinery_five_years() -> ExamAnswer:
    ledger = Ledger()
    entry = ledger.record("buy_asset_cash", 2_000_000, period=1, asset_account="machinery")
    linkage = explain_transaction_linkage("buy_asset_cash", amount=2_000_000, asset_account="machinery")
    today_bs = build_balance_sheet(ledger, 1)
    today_cash_unchanged_total_assets = today_bs["accounting_equation"]["balances"]

    annual_dep = 400_000  # ₹20L over a 5-year useful life, straight-line
    for year in range(1, 6):
        ledger.record("record_depreciation", annual_dep, period=year, narrative=f"Year {year} depreciation")
        ledger.close_period(year)

    year5_bs = build_balance_sheet(ledger, 5)
    net_ppe_year5 = year5_bs["assets"]["non_current_assets"]["ppe_net"]
    accum_dep_year5 = year5_bs["assets"]["non_current_assets"]["accumulated_depreciation"]
    cash_year5 = year5_bs["assets"]["current_assets"]["cash"]
    cash_year1 = today_bs["assets"]["current_assets"]["cash"]

    answer = (
        f"TODAY: Journal Debit Machinery ₹20,00,000; Credit Cash ₹20,00,000 — {linkage['summary']} "
        f"Balance Sheet: one asset (Cash) exchanges for another (Machinery); total assets unchanged. "
        f"Cash Flow: a ₹20,00,000 Investing outflow.\n"
        f"FIVE YEARS LATER (straight-line over a 5-year life, ₹4,00,000/year): Accumulated Depreciation "
        f"reaches ₹{accum_dep_year5:,.0f} (the full original cost), Net PPE falls to ₹{net_ppe_year5:,.0f} "
        f"— the asset is fully depreciated. Cash does NOT change again from depreciation ({cash_year1:,.0f} "
        f"→ {cash_year5:,.0f}) — the cash outflow already happened today, in Investing activities; each "
        f"year's Depreciation Expense reduces EBIT and PAT with zero further cash effect."
    )
    return ExamAnswer(
        answer_text=answer,
        evidence={"today_balance_sheet": today_bs, "year5_balance_sheet": year5_bs, "linkage": linkage},
        accounting_checks={
            "journal_entry_balanced": entry.is_balanced(),
            "today_equation_holds": today_cash_unchanged_total_assets,
            "year5_equation_holds": year5_bs["accounting_equation"]["balances"],
            "fully_depreciated": abs(net_ppe_year5) < 1e-6,
            "accumulated_depreciation_equals_cost": abs(accum_dep_year5 - 2_000_000) < 1e-6,
            "cash_unchanged_by_depreciation": cash_year1 == cash_year5,
        },
        linkage_checks={
            "no_income_statement_effect_today": not linkage["income_statement_affected_today"],
            "cash_affected_today": linkage["cash_affected_today"],
            "future_ripple_mentions_depreciation": any("depreciat" in s.lower() for s in linkage["future_ripple"]),
        },
        interpretation_keypoints_expected=["investing", "depreciation", "cash", "ebit", "pat", "fully depreciated"],
        interpretation_keypoints_matched=[k for k in ["investing", "depreciation", "cash", "ebit", "pat", "fully depreciated"] if k in answer.lower()],
    )


def _q3_credit_sale_and_collection() -> ExamAnswer:
    ledger = Ledger()
    sale_entry = ledger.record("credit_sale", 1_200_000, period=1)
    sale_stmts = build_all_statements(ledger, 1)

    # Collection at day 90 is still within the same reporting period in this
    # illustration; the ledger is never closed until after both dates so the
    # comparison below reflects Income Statement / Balance Sheet / Cash Flow
    # exactly as of each transaction date.
    collect_entry = ledger.record("collect_receivable", 1_200_000, period=1)
    after_collection_stmts = build_all_statements(ledger, 1)

    sale_linkage = explain_transaction_linkage("credit_sale", amount=1_200_000)
    collect_linkage = explain_transaction_linkage("collect_receivable", amount=1_200_000)

    ar_after_sale = sale_stmts["balance_sheet"]["assets"]["current_assets"]["accounts_receivable"]
    ar_after_collection = after_collection_stmts["balance_sheet"]["assets"]["current_assets"]["accounts_receivable"]
    revenue_after_sale = sale_stmts["income_statement"]["revenue"]
    revenue_after_collection = after_collection_stmts["income_statement"]["revenue"]
    cash_after_sale = sale_stmts["balance_sheet"]["assets"]["current_assets"]["cash"]
    cash_after_collection = after_collection_stmts["balance_sheet"]["assets"]["current_assets"]["cash"]

    answer = (
        f"AT SALE (Day 0): Journal Debit Accounts Receivable ₹12,00,000; Credit Revenue ₹12,00,000. "
        f"Income Statement: Revenue recognised at ₹{revenue_after_sale:,.0f} — {sale_linkage['teaches']} "
        f"Balance Sheet: Accounts Receivable = ₹{ar_after_sale:,.0f}. Cash Flow: no effect (Cash = "
        f"₹{cash_after_sale:,.0f}).\n"
        f"AT COLLECTION (Day 90): Journal Debit Cash ₹12,00,000; Credit Accounts Receivable ₹12,00,000. "
        f"Income Statement: UNCHANGED (Revenue still ₹{revenue_after_collection:,.0f} — {collect_linkage['teaches']}) "
        f"Balance Sheet: Accounts Receivable falls to ₹{ar_after_collection:,.0f}. Cash Flow: an Operating "
        f"inflow of ₹12,00,000 (Cash rises to ₹{cash_after_collection:,.0f})."
    )
    return ExamAnswer(
        answer_text=answer,
        evidence={"sale_statements": sale_stmts, "after_collection_statements": after_collection_stmts},
        accounting_checks={
            "sale_entry_balanced": sale_entry.is_balanced(),
            "collection_entry_balanced": collect_entry.is_balanced(),
            "revenue_unchanged_by_collection": revenue_after_sale == revenue_after_collection,
            "receivable_zeroed_after_collection": abs(ar_after_collection) < 1e-6,
            "cash_only_moves_at_collection": cash_after_sale == 0 and cash_after_collection == 1_200_000,
        },
        linkage_checks={
            "sale_no_cash_effect": not sale_linkage["cash_affected_today"],
            "sale_has_income_statement_effect": sale_linkage["income_statement_affected_today"],
            "collection_no_income_statement_effect": not collect_linkage["income_statement_affected_today"],
            "collection_has_cash_effect": collect_linkage["cash_affected_today"],
        },
        interpretation_keypoints_expected=["receivable", "revenue", "recognised", "operating", "unchanged"],
        interpretation_keypoints_matched=[k for k in ["receivable", "revenue", "recognised", "operating", "unchanged"] if k in answer.lower()],
    )


def _q4_customer_advance() -> ExamAnswer:
    ledger = Ledger()
    entry = ledger.record("deferred_revenue_received", 500_000, period=1)
    stmts = build_all_statements(ledger, 1)
    linkage = explain_transaction_linkage("deferred_revenue_received", amount=500_000)

    revenue = stmts["income_statement"]["revenue"]
    cash = stmts["balance_sheet"]["assets"]["current_assets"]["cash"]
    unearned = stmts["balance_sheet"]["liabilities"]["current_liabilities"]["unearned_revenue"]

    answer = (
        f"Revenue: ₹0 — no revenue is recognised because nothing has been delivered yet; recognising "
        f"revenue on cash receipt alone would violate the revenue recognition principle.\n"
        f"Cash: increases by ₹5,00,000 — the cash was genuinely received today.\n"
        f"Liability: Unearned Revenue increases by ₹{unearned:,.0f} — this represents the company's "
        f"obligation to deliver goods/services in the future; it converts to Revenue only when that "
        f"obligation is fulfilled. {linkage['teaches']}"
    )
    return ExamAnswer(
        answer_text=answer,
        evidence={"statements": stmts, "linkage": linkage},
        accounting_checks={
            "entry_balanced": entry.is_balanced(),
            "revenue_is_zero": revenue == 0,
            "cash_correct": cash == 500_000,
            "unearned_revenue_correct": unearned == 500_000,
        },
        linkage_checks={
            "cash_affected_today": linkage["cash_affected_today"],
            "no_income_statement_effect": not linkage["income_statement_affected_today"],
        },
        interpretation_keypoints_expected=["revenue", "cash", "liability", "unearned", "delivered"],
        interpretation_keypoints_matched=[k for k in ["revenue", "cash", "liability", "unearned", "delivered"] if k in answer.lower()],
    )


def _q5_accrued_salary() -> ExamAnswer:
    ledger = Ledger()
    entry = ledger.record("salary_due", 150_000, period=1)
    stmts = build_all_statements(ledger, 1)
    linkage = explain_transaction_linkage("salary_due", amount=150_000)

    cash = stmts["balance_sheet"]["assets"]["current_assets"]["cash"]
    salary_payable = stmts["balance_sheet"]["liabilities"]["current_liabilities"]["salary_payable"]
    pat = stmts["income_statement"]["pat"]

    answer = (
        f"Journal: Debit Salary Expense ₹1,50,000; Credit Salary Payable ₹1,50,000. Under accrual "
        f"accounting, the expense is recognised the moment the obligation arises (work performed), "
        f"NOT when cash is eventually paid. Income Statement: PAT falls by the full ₹1,50,000 "
        f"(PAT = ₹{pat:,.0f}). Balance Sheet: Salary Payable (a liability) rises to ₹{salary_payable:,.0f}. "
        f"Cash Flow: no effect today (Cash = ₹{cash:,.0f}) — {linkage['teaches']}"
    )
    return ExamAnswer(
        answer_text=answer,
        evidence={"statements": stmts, "linkage": linkage},
        accounting_checks={
            "entry_balanced": entry.is_balanced(),
            "cash_unaffected": cash == 0,
            "salary_payable_correct": salary_payable == 150_000,
            "pat_reduced": pat == -150_000,
        },
        linkage_checks={
            "no_cash_effect_today": not linkage["cash_affected_today"],
            "income_statement_affected_today": linkage["income_statement_affected_today"],
        },
        interpretation_keypoints_expected=["accrual", "expense", "payable", "obligation", "cash"],
        interpretation_keypoints_matched=[k for k in ["accrual", "expense", "payable", "obligation", "cash"] if k in answer.lower()],
    )


SECTION_A_ITEMS: list[ExamItem] = [
    ExamItem("Q1", "A", 1, "Founder invests ₹50 lakh. Construct Journal Entry, Ledger, Trial Balance, Opening Balance Sheet.", 4.0, _q1_founder_investment, "accounting"),
    ExamItem("Q2", "A", 2, "Company purchases machinery for ₹20 lakh cash. Show impact today and five years later.", 4.0, _q2_machinery_five_years, "accounting"),
    ExamItem("Q3", "A", 3, "Company sells ₹12 lakh goods on credit; customer pays after 90 days. Trace both dates.", 4.0, _q3_credit_sale_and_collection, "accounting"),
    ExamItem("Q4", "A", 4, "Company receives ₹5 lakh advance, no goods delivered. Explain Revenue/Cash/Liability.", 4.0, _q4_customer_advance, "accounting"),
    ExamItem("Q5", "A", 5, "Salary expense accrued but unpaid. Explain.", 4.0, _q5_accrued_salary, "accounting"),
]
