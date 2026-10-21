"""Initial Schema Evolution mappings — IND-AS / NSE taxonomies."""

from __future__ import annotations

from typing import Any

# (label, canonical, standard, taxonomy, taxonomy_version, effective_from, parent)
_SEED: tuple[tuple[str, str, str, str, str, str, str | None], ...] = (
    ("RevenueFromOperations", "revenue", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("Revenue From Operations", "revenue", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("Net Sales", "revenue", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("ProfitAfterTax", "net_income", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("Profit After Tax", "net_income", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("FinanceCosts", "finance_cost", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("Finance Costs", "finance_cost", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("Finance Cost", "finance_cost", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    ("EmployeeBenefitExpense", "employee_cost", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", "operating_expenses"),
    ("CashAndCashEquivalents", "cash", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", "current_assets"),
    ("TradeReceivables", "receivables", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", "current_assets"),
    ("Inventories", "inventory", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", "current_assets"),
    ("NetCashFlowsFromUsedInOperatingActivities", "operating_cash_flow", "IND_AS", "nse_indas_integrated_filing", "2024.1", "2016-04-01", None),
    # IFRS examples for extensibility
    ("Revenue", "revenue", "IFRS", "ifrs_taxonomy", "2024.1", "2018-01-01", None),
    ("ProfitLoss", "net_income", "IFRS", "ifrs_taxonomy", "2024.1", "2018-01-01", None),
)


def seed_mappings() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label, canonical, standard, taxonomy, tax_ver, effective_from, parent in _SEED:
        rows.append(
            {
                "canonical_metric": canonical,
                "label": label,
                "synonyms": [label],
                "reporting_standards": [standard],
                "taxonomy": taxonomy,
                "taxonomy_version": tax_ver,
                "effective_from": effective_from,
                "effective_to": None,
                "status": "active",
                "replaced_by": None,
                "parent_metric": parent,
                "children": [],
            }
        )
    return rows
