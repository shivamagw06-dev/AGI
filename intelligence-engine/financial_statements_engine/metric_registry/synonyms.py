"""Versioned synonym map — incoming names → FSE-03 canonical metrics.

Warehouse stores canonical ids only. Synonyms never appear in published facts.
"""

from __future__ import annotations

# synonym / legacy / XBRL local → canonical
SYNONYMS: dict[str, str] = {
    # revenue
    "Revenue": "revenue",
    "revenue_from_operations": "revenue",
    "RevenueFromOperations": "revenue",
    "revenue_from_operations_total": "revenue",
    "total_revenue": "revenue",
    "net_sales": "revenue",
    "Net Sales": "revenue",
    "Sales": "revenue",
    "Revenue From Operations": "revenue",
    # other / total income
    "OtherIncome": "other_income",
    "Other Income": "other_income",
    "TotalIncome": "total_income",
    "Total Income": "total_income",
    # costs
    "CostOfMaterialsConsumed": "cogs",
    "cost_of_goods_sold": "cogs",
    "COGS": "cogs",
    "EmployeeBenefitExpense": "employee_cost",
    "employee_benefit_expense": "employee_cost",
    "employee_cost": "employee_cost",
    "Employee Cost": "employee_cost",
    "operating_expenses": "operating_expenses",
    "expenses": "operating_expenses",
    # profitability
    "EBITDA": "ebitda",
    "DepreciationAndAmortisation": "depreciation",
    "depreciation_and_amortisation": "depreciation",
    "EBIT": "ebit",
    "OperatingProfit": "ebit",
    "FinanceCosts": "finance_cost",
    "finance_costs": "finance_cost",
    "finance_cost": "finance_cost",
    "Finance Cost": "finance_cost",
    "Finance Costs": "finance_cost",
    "InterestExpense": "finance_cost",
    "ProfitBeforeTax": "profit_before_tax",
    "pbt": "profit_before_tax",
    "PBT": "profit_before_tax",
    "TaxExpense": "tax_expense",
    "ProfitAfterTax": "net_income",
    "ProfitForThePeriod": "net_income",
    "pat": "net_income",
    "PAT": "net_income",
    "Net Profit": "net_income",
    "NetProfit": "net_income",
    "Profit After Tax": "net_income",
    "net_profit": "net_income",
    "ProfitAttributableToOwners": "pat_owners",
    "BasicEPS": "eps_basic",
    "DilutedEPS": "eps_diluted",
    # balance
    "CashAndCashEquivalents": "cash",
    "TradeReceivables": "receivables",
    "trade_receivables": "receivables",
    "Inventories": "inventory",
    "CurrentAssets": "current_assets",
    "TotalAssets": "total_assets",
    "CurrentLiabilities": "current_liabilities",
    "TotalLiabilities": "total_liabilities",
    "EquityShareCapital": "share_capital",
    "equity_share_capital": "share_capital",
    "share_capital": "share_capital",
    "Share Capital": "share_capital",
    "RetainedEarnings": "retained_earnings",
    "TotalEquity": "total_equity",
    "NonCurrentAssets": "non_current_assets",
    "NonCurrentLiabilities": "non_current_liabilities",
    "Borrowings": "total_debt",
    "total_borrowings": "total_debt",
    "EquityAttributableToOwners": "equity_owners",
    "OtherEquity": "reserves",
    "FaceValue": "face_value",
    "NumberOfShares": "shares_outstanding",
    "Investments": "investments",
    # cash flow
    "CashFlowsFromUsedInOperatingActivities": "operating_cash_flow",
    "NetCashFlowsFromUsedInOperatingActivities": "operating_cash_flow",
    "CashFlowsFromUsedInInvestingActivities": "investing_cash_flow",
    "CashFlowsFromUsedInFinancingActivities": "financing_cash_flow",
    "PurchaseOfPropertyPlantAndEquipment": "capex",
    "IncreaseDecreaseInCashAndCashEquivalents": "net_cash_change",
    "net_change_in_cash": "net_cash_change",
    "FreeCashFlow": "free_cash_flow",
}


def synonym_table() -> dict[str, str]:
    return dict(SYNONYMS)
