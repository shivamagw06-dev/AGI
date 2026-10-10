"""Corporate finance cause→effect graphs."""

from __future__ import annotations

from academy.schema import CausalModel


def all_causal_models() -> list[CausalModel]:
    return [
        CausalModel(
            model_id="roic_to_intrinsic_value",
            name="ROIC → intrinsic value",
            trigger="ROIC vs WACC",
            direction="mixed",
            chain=["ROIC", "WACC", "Economic Profit", "Intrinsic Value"],
            industries_affected=["Technology", "Manufacturing", "FMCG", "Utilities", "Pharmaceuticals"],
            related_concepts=["roic_wacc_spread", "wacc", "economic_profit", "value_creation"],
        ),
        CausalModel(
            model_id="capital_allocation_to_value",
            name="Capital allocation → intrinsic value",
            trigger="Capital Allocation decision",
            direction="mixed",
            chain=["Capital Allocation", "Free Cash Flow use", "Growth quality", "Intrinsic Value"],
            industries_affected=["Technology", "Telecom", "Infrastructure", "FMCG"],
            related_concepts=["capital_allocation", "organic_reinvestment", "value_creation", "value_destruction"],
        ),
        CausalModel(
            model_id="leverage_to_valuation",
            name="Leverage → valuation",
            trigger="Debt ↑",
            direction="mixed",
            chain=[
                "Debt ↑",
                "Tax shield / equity beta ↑",
                "WACC changes",
                "Distress risk ↑ (if excessive)",
                "Firm Value up or down vs optimum",
            ],
            industries_affected=["Utilities", "Banks", "Retail", "Telecom"],
            related_concepts=["financial_leverage", "wacc", "optimal_capital_structure", "financial_distress"],
        ),
        CausalModel(
            model_id="buyback_value_test",
            name="Buyback price vs intrinsic value",
            trigger="Share buyback",
            direction="mixed",
            chain=[
                "Buyback announced",
                "Price vs Intrinsic Value test",
                "Value accretion if below IV",
                "Value destruction if above IV",
                "EPS may rise either way (illusion risk)",
            ],
            industries_affected=["Technology", "FMCG", "Banks"],
            related_concepts=["share_buybacks", "eps_illusion", "value_creation", "value_destruction"],
        ),
        CausalModel(
            model_id="acquisition_failure_path",
            name="Acquisition overpayment → value destruction",
            trigger="Control premium > PV(synergies)",
            direction="decrease",
            chain=[
                "Acquisition premium",
                "Overpayment",
                "Integration risk",
                "Incremental ROIC < WACC",
                "Value Destruction / Impairment",
            ],
            industries_affected=["Technology", "Pharmaceuticals", "Telecom", "Banks"],
            related_concepts=["acquisition_overpayment", "acquisition_synergies", "integration_risk", "acquisition_quality"],
        ),
        CausalModel(
            model_id="growth_without_returns",
            name="Growth without returns destroys value",
            trigger="Reinvestment with ROIC < WACC",
            direction="decrease",
            chain=[
                "Revenue Growth ↑",
                "Reinvestment ↑",
                "Incremental ROIC < WACC",
                "Economic Profit ↓",
                "Intrinsic Value ↓",
            ],
            industries_affected=["Manufacturing", "Telecom", "Retail", "Infrastructure"],
            related_concepts=["organic_reinvestment", "incremental_roic", "roic_wacc_spread", "value_destruction"],
        ),
    ]
