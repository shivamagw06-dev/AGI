"""Financial Statement Builder — Module 6 (Income Statement), 7 (Balance
Sheet), 8 (Cash Flow Statement).

Builds all three statements from a Ledger. The Cash Flow Statement is
computed TWICE — once directly from actual cash postings, and once via
the indirect method (PAT + adjustments) — and the two must reconcile.
That reconciliation is the proof that "PAT ≠ Cash Flow" is understood
mechanically, not just recited.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from financial_foundations.chart_of_accounts import CHART_OF_ACCOUNTS
from financial_foundations.journal import Ledger
from financial_foundations.schema import AccountType, CashFlowSection, Side
from financial_foundations.statement_concepts import get_concept

# Which transaction types touch Cash, and which CF section they belong to.
# (Only transaction types whose ``build`` rule can post to "cash" need an
# entry here — everything else never appears in a cash-flow reconciliation.)
CASH_FLOW_CLASSIFICATION: dict[str, CashFlowSection] = {
    "founder_investment": CashFlowSection.FINANCING,
    "issue_shares": CashFlowSection.FINANCING,
    "take_loan": CashFlowSection.FINANCING,
    "repay_debt": CashFlowSection.FINANCING,
    "pay_dividend": CashFlowSection.FINANCING,
    "buy_asset_cash": CashFlowSection.INVESTING,
    "cash_sale": CashFlowSection.OPERATING,
    "collect_receivable": CashFlowSection.OPERATING,
    "deferred_revenue_received": CashFlowSection.OPERATING,
    "purchase_inventory_cash": CashFlowSection.OPERATING,
    "pay_payable": CashFlowSection.OPERATING,
    "pay_salary_payable": CashFlowSection.OPERATING,
    "pay_expense_cash": CashFlowSection.OPERATING,
    "pay_interest": CashFlowSection.OPERATING,
    "pay_tax": CashFlowSection.OPERATING,
    "prepay_expense": CashFlowSection.OPERATING,
}

# Working-capital accounts tracked for the indirect-method reconciliation.
_WC_ASSET_ACCOUNTS = ("accounts_receivable", "inventory", "prepaid_expenses")
_WC_LIABILITY_ACCOUNTS = (
    "accounts_payable",
    "salary_payable",
    "interest_payable",
    "tax_payable",
    "unearned_revenue",
)


@dataclass
class StatementLine:
    key: str
    label: str
    value: float
    definition: str = ""
    business_meaning: str = ""


def _line(key: str, label: str, value: float) -> StatementLine:
    concept = get_concept(key)
    return StatementLine(
        key=key,
        label=label,
        value=round(value, 2),
        definition=concept.definition if concept else "",
        business_meaning=concept.business_meaning if concept else "",
    )


# ---------------------------------------------------------------------------
# Module 6 — Income Statement
# ---------------------------------------------------------------------------
def build_income_statement(ledger: Ledger, period: int) -> dict[str, Any]:
    def bal(code: str) -> float:
        return ledger.balance(code, period=period)

    revenue = round(bal("product_sales") + bal("service_revenue"), 2)
    cogs = round(bal("cogs"), 2)
    gross_profit = round(revenue - cogs, 2)
    opex = round(
        bal("salary_expense")
        + bal("rent_expense")
        + bal("marketing_expense")
        + bal("rd_expense")
        + bal("bad_debt_expense"),
        2,
    )
    ebitda = round(gross_profit - opex, 2)
    depreciation = round(bal("depreciation_expense"), 2)
    ebit = round(ebitda - depreciation, 2)
    interest = round(bal("interest_expense"), 2)
    pbt = round(ebit - interest, 2)
    tax = round(bal("tax_expense"), 2)
    pat = round(pbt - tax, 2)

    lines = [
        _line("revenue", "Revenue", revenue),
        _line("cogs", "Cost of Goods Sold", cogs),
        _line("gross_profit", "Gross Profit", gross_profit),
        _line("operating_expense", "Operating Expenses", opex),
        _line("ebitda", "EBITDA", ebitda),
        _line("depreciation", "Depreciation", depreciation),
        _line("ebit", "EBIT", ebit),
        _line("interest", "Interest Expense", interest),
        _line("pbt", "Profit Before Tax (PBT)", pbt),
        _line("tax", "Tax Expense", tax),
        _line("pat", "Profit After Tax (PAT)", pat),
    ]
    return {
        "statement": "income_statement",
        "period": period,
        "lines": [l.__dict__ for l in lines],
        "revenue": revenue,
        "gross_profit": gross_profit,
        "ebitda": ebitda,
        "ebit": ebit,
        "pbt": pbt,
        "pat": pat,
        "construction_order": [
            "revenue", "cogs", "gross_profit", "operating_expense", "ebitda",
            "depreciation", "ebit", "interest", "pbt", "tax", "pat",
        ],
    }


# ---------------------------------------------------------------------------
# Module 7 — Balance Sheet
# ---------------------------------------------------------------------------
def build_balance_sheet(ledger: Ledger, through_period: int) -> dict[str, Any]:
    def bal(code: str) -> float:
        return ledger.balance(code, through_period=through_period)

    cash = bal("cash")
    ar = bal("accounts_receivable")
    inventory = bal("inventory")
    prepaid = bal("prepaid_expenses")
    current_assets = round(cash + ar + inventory + prepaid, 2)

    ppe_gross = round(bal("land") + bal("machinery") + bal("furniture"), 2)
    accum_dep = bal("accumulated_depreciation")
    ppe_net = round(ppe_gross - accum_dep, 2)

    total_assets = round(current_assets + ppe_net, 2)

    ap = bal("accounts_payable")
    salary_payable = bal("salary_payable")
    interest_payable = bal("interest_payable")
    tax_payable = bal("tax_payable")
    unearned = bal("unearned_revenue")
    dividends_payable = bal("dividends_payable")
    current_liabilities = round(
        ap + salary_payable + interest_payable + tax_payable + unearned + dividends_payable, 2
    )

    long_term_liabilities = round(bal("bank_loan"), 2)
    total_liabilities = round(current_liabilities + long_term_liabilities, 2)

    share_capital = bal("share_capital")
    retained_earnings = bal("retained_earnings")
    total_equity = round(share_capital + retained_earnings, 2)

    liabilities_plus_equity = round(total_liabilities + total_equity, 2)
    balances = abs(total_assets - liabilities_plus_equity) < 0.01

    return {
        "statement": "balance_sheet",
        "through_period": through_period,
        "assets": {
            "current_assets": {
                "cash": cash, "accounts_receivable": ar, "inventory": inventory,
                "prepaid_expenses": prepaid, "total": current_assets,
            },
            "non_current_assets": {
                "ppe_gross": ppe_gross, "accumulated_depreciation": accum_dep,
                "ppe_net": ppe_net, "total": ppe_net,
            },
            "total_assets": total_assets,
        },
        "liabilities": {
            "current_liabilities": {
                "accounts_payable": ap, "salary_payable": salary_payable,
                "interest_payable": interest_payable, "tax_payable": tax_payable,
                "unearned_revenue": unearned, "dividends_payable": dividends_payable,
                "total": current_liabilities,
            },
            "long_term_liabilities": {"bank_loan": long_term_liabilities, "total": long_term_liabilities},
            "total_liabilities": total_liabilities,
        },
        "equity": {
            "share_capital": share_capital,
            "retained_earnings": retained_earnings,
            "total_equity": total_equity,
        },
        "accounting_equation": {
            "total_assets": total_assets,
            "total_liabilities_plus_equity": liabilities_plus_equity,
            "balances": balances,
        },
    }


# ---------------------------------------------------------------------------
# Module 8 — Cash Flow Statement (direct reconciliation + indirect method)
# ---------------------------------------------------------------------------
def _direct_cash_flow(ledger: Ledger, period: int) -> dict[str, Any]:
    sections: dict[CashFlowSection, float] = {
        CashFlowSection.OPERATING: 0.0,
        CashFlowSection.INVESTING: 0.0,
        CashFlowSection.FINANCING: 0.0,
    }
    detail: dict[str, list[dict[str, Any]]] = {
        CashFlowSection.OPERATING.value: [],
        CashFlowSection.INVESTING.value: [],
        CashFlowSection.FINANCING.value: [],
    }
    for entry in ledger.period_entries(period, include_closing=False):
        section = CASH_FLOW_CLASSIFICATION.get(entry.transaction_type)
        if section is None:
            continue
        for p in entry.postings:
            if p.account_code != "cash":
                continue
            signed = p.amount if p.side == Side.DEBIT else -p.amount
            sections[section] += signed
            detail[section.value].append(
                {"transaction_type": entry.transaction_type, "narrative": entry.narrative, "amount": round(signed, 2)}
            )
    return {
        "operating": round(sections[CashFlowSection.OPERATING], 2),
        "investing": round(sections[CashFlowSection.INVESTING], 2),
        "financing": round(sections[CashFlowSection.FINANCING], 2),
        "net_change_in_cash": round(sum(sections.values()), 2),
        "detail": detail,
    }


def _indirect_operating_cash_flow(ledger: Ledger, period: int, pat: float) -> dict[str, Any]:
    def delta(code: str) -> float:
        end = ledger.balance(code, through_period=period)
        start = ledger.balance(code, through_period=period - 1) if period > 1 else 0.0
        return round(end - start, 2)

    depreciation = ledger.balance("depreciation_expense", period=period)
    adjustments: list[dict[str, Any]] = [
        {"item": "Depreciation (non-cash add-back)", "amount": round(depreciation, 2)}
    ]
    wc_total = 0.0
    for code in _WC_ASSET_ACCOUNTS:
        d = delta(code)
        adj = -d  # an increase in an operating asset consumes cash
        wc_total += adj
        if abs(d) > 1e-9:
            acc_name = CHART_OF_ACCOUNTS[code].name
            direction = "increase" if d > 0 else "decrease"
            adjustments.append(
                {"item": f"{direction.capitalize()} in {acc_name}", "amount": round(adj, 2)}
            )
    for code in _WC_LIABILITY_ACCOUNTS:
        d = delta(code)
        adj = d  # an increase in an operating liability conserves cash
        wc_total += adj
        if abs(d) > 1e-9:
            acc_name = CHART_OF_ACCOUNTS[code].name
            direction = "increase" if d > 0 else "decrease"
            adjustments.append(
                {"item": f"{direction.capitalize()} in {acc_name}", "amount": round(adj, 2)}
            )
    operating_cf = round(pat + depreciation + wc_total, 2)
    return {"operating_cf_indirect": operating_cf, "adjustments": adjustments}


def build_cash_flow_statement(ledger: Ledger, period: int) -> dict[str, Any]:
    direct = _direct_cash_flow(ledger, period)
    pat = ledger.period_net_income(period)
    indirect = _indirect_operating_cash_flow(ledger, period, pat)

    reconciles = abs(direct["operating"] - indirect["operating_cf_indirect"]) < 0.01
    opening_cash = ledger.balance("cash", through_period=period - 1) if period > 1 else 0.0
    closing_cash = ledger.balance("cash", through_period=period)
    actual_change = round(closing_cash - opening_cash, 2)

    return {
        "statement": "cash_flow_statement",
        "period": period,
        "pat_starting_point": pat,
        "operating": {
            "direct": direct["operating"],
            "indirect": indirect["operating_cf_indirect"],
            "reconciles": reconciles,
            "adjustments": indirect["adjustments"],
            "definition": get_concept("operating_cash_flow").definition,
        },
        "investing": {
            "amount": direct["investing"],
            "detail": direct["detail"][CashFlowSection.INVESTING.value],
            "definition": get_concept("investing_cash_flow").definition,
        },
        "financing": {
            "amount": direct["financing"],
            "detail": direct["detail"][CashFlowSection.FINANCING.value],
            "definition": get_concept("financing_cash_flow").definition,
        },
        "net_change_in_cash": direct["net_change_in_cash"],
        "opening_cash": round(opening_cash, 2),
        "closing_cash": round(closing_cash, 2),
        "reconciles_to_actual_cash_movement": abs(direct["net_change_in_cash"] - actual_change) < 0.01,
        "pat_vs_operating_cash_flow_gap": round(direct["operating"] - pat, 2),
    }


def build_all_statements(ledger: Ledger, period: int) -> dict[str, Any]:
    """Convenience: build IS, BS, CF for one period in construction order."""
    income_statement = build_income_statement(ledger, period)
    balance_sheet = build_balance_sheet(ledger, period)
    cash_flow_statement = build_cash_flow_statement(ledger, period)
    return {
        "period": period,
        "income_statement": income_statement,
        "balance_sheet": balance_sheet,
        "cash_flow_statement": cash_flow_statement,
        "trial_balance_balances": ledger.trial_balance_is_balanced(through_period=period),
    }
