"""Accounting cause→effect graphs for investor reasoning."""

from __future__ import annotations

from academy.schema import CausalModel


def all_causal_models() -> list[CausalModel]:
    return [
        CausalModel(
            model_id="revenue_to_intrinsic_value",
            name="Revenue → intrinsic value",
            trigger="Revenue recognised",
            direction="mixed",
            chain=[
                "Revenue",
                "Receivables / Deferred Revenue",
                "Working Capital",
                "Operating Cash Flow",
                "Free Cash Flow",
                "Intrinsic Value",
            ],
            industries_affected=["Software", "IT", "Manufacturing", "Retail"],
            related_concepts=["revenue_recognition", "accounts_receivable", "working_capital", "free_cash_flow"],
        ),
        CausalModel(
            model_id="earnings_to_cash_gap",
            name="Earnings without cash conversion",
            trigger="Net Income ↑ while CFO flat",
            direction="decrease",
            chain=[
                "Net Income ↑",
                "Accruals ↑",
                "Receivables/Inventory ↑",
                "Cash Conversion ↓",
                "Earnings Quality ↓",
                "Valuation Multiple ↓",
            ],
            industries_affected=["Manufacturing", "IT", "Capital Goods", "FMCG"],
            related_concepts=["net_income", "accruals", "operating_cash_flow", "earnings_quality"],
        ),
        CausalModel(
            model_id="inventory_to_fcf",
            name="Inventory accumulation → FCF",
            trigger="Inventory ↑ faster than sales",
            direction="decrease",
            chain=[
                "Inventory ↑",
                "Working Capital ↑",
                "Cash Flow ↓",
                "Free Cash Flow ↓",
                "Intrinsic Value pressure",
            ],
            industries_affected=["Manufacturing", "Retail", "Auto", "Steel"],
            related_concepts=["inventory", "working_capital", "free_cash_flow"],
        ),
        CausalModel(
            model_id="aggressive_revenue_to_earnings",
            name="Aggressive revenue recognition → inflated earnings",
            trigger="Revenue pulled forward",
            direction="mixed",
            chain=[
                "Aggressive Revenue Recognition",
                "Receivables ↑",
                "Reported Earnings ↑",
                "Cash lags",
                "Later reversals / write-offs",
                "Thesis broken",
            ],
            industries_affected=["Software", "IT", "Infrastructure", "Capital Goods"],
            related_concepts=["revenue_recognition", "accounts_receivable", "earnings_quality"],
        ),
        CausalModel(
            model_id="goodwill_impairment_path",
            name="Value-destructive M&A → impairment",
            trigger="Acquisition premium without returns",
            direction="decrease",
            chain=[
                "Goodwill ↑",
                "ROIC on acquired capital weak",
                "Impairment testing pressure",
                "Impairment charge",
                "Earnings & credibility ↓",
            ],
            industries_affected=["IT", "Pharmaceuticals", "Telecom", "FMCG"],
            related_concepts=["goodwill", "impairment", "roic", "earnings_quality"],
        ),
        CausalModel(
            model_id="lease_capitalisation_bridge",
            name="Lease adjustment → clean ROIC/leverage",
            trigger="Capitalise operating leases",
            direction="mixed",
            chain=[
                "Operating Lease Commitments",
                "Lease Debt + ROU Asset",
                "EBIT / Invested Capital restated",
                "ROIC & Leverage recalibrated",
                "EV bridge updated",
            ],
            industries_affected=["Retail", "Telecom", "Airlines", "Logistics"],
            related_concepts=["leases", "ebit", "roic"],
        ),
    ]
