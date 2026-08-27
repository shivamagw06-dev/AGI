"""Sector KPI libraries — specialised peer metrics by industry archetype."""

from __future__ import annotations

from typing import Any

SECTOR_KPIS: dict[str, list[str]] = {
    "banks": [
        "CASA",
        "Deposit_Beta",
        "NIM",
        "Credit_Cost",
        "GNPA",
        "NNPA",
        "Provision_Coverage",
        "CET1",
        "Deposit_Growth",
        "Loan_Growth",
        "Cost_of_Funds",
        "ROE",
        "ROA",
    ],
    "fmcg": [
        "Market_Share",
        "Volume_Growth",
        "Pricing",
        "Gross_Margin",
        "Operating_Margin",
        "Working_Capital_Days",
        "ROIC",
        "Cash_Conversion",
        "Distribution_Reach",
    ],
    "it_services": [
        "Utilisation",
        "Attrition",
        "Deal_Wins",
        "Pricing",
        "Cash_Conversion",
        "EBIT_Margin",
        "Revenue_Growth",
        "ROIC",
        "FCF_Conversion",
    ],
    "consumer_internet": [
        "Take_Rate",
        "Contribution_Margin",
        "CAC",
        "LTV",
        "Retention",
        "DAU",
        "MAU",
        "Order_Density",
        "Unit_Economics",
    ],
    "industrials": [
        "Capacity_Utilisation",
        "Order_Book",
        "Execution",
        "Backlog",
        "ROIC",
        "Working_Capital",
    ],
    "auto": [
        "Market_Share",
        "Realisations",
        "EV_Mix",
        "Inventory",
        "Operating_Margin",
    ],
    "healthcare": [
        "Occupancy",
        "ARPOB",
        "Case_Mix",
        "Realisation",
        "EBITDA_Margin",
    ],
}

FINANCIAL_BENCHMARKS = [
    "Revenue_Growth",
    "Operating_Margin",
    "EBIT_Margin",
    "Net_Margin",
    "ROE",
    "ROA",
    "ROIC",
    "Cash_Conversion",
    "Working_Capital",
    "Debt_Equity",
    "Net_Debt",
    "Interest_Coverage",
    "Free_Cash_Flow",
    "Dividend_Payout",
]

VALUATION_BENCHMARKS = [
    "PE",
    "Forward_PE",
    "PB",
    "PS",
    "EV_EBITDA",
    "EV_Sales",
    "PEG",
    "Dividend_Yield",
    "PE_5Y_avg",
    "PB_5Y_avg",
    "Premium_vs_History",
    "Premium_vs_Peers",
]


def kpis_for_sector(sector: str) -> list[str]:
    return list(SECTOR_KPIS.get(sector, FINANCIAL_BENCHMARKS[:8]))


def sector_model(sector: str) -> dict[str, Any]:
    return {
        "sector": sector,
        "kpis": kpis_for_sector(sector),
        "financial_benchmarks": FINANCIAL_BENCHMARKS,
        "valuation_benchmarks": VALUATION_BENCHMARKS,
    }
