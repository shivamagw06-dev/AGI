"""Soft consumption views — engines consume knowledge objects without redesign.

Locked engines are not modified. Academy framework pattern unchanged.
"""

from __future__ import annotations

from typing import Any

from academy.accounting.earnings_quality import score_earnings_quality
from academy.accounting.red_flags import score_red_flags
from academy.catalog import all_causal_models, all_mental_models, knowledge_by_id, teach
from academy.graph import concept_neighborhood


def _bundle_concepts(ids: list[str]) -> list[dict[str, Any]]:
    kb = knowledge_by_id()
    out = []
    for cid in ids:
        ko = kb.get(cid)
        if ko:
            out.append(ko.to_dict())
    return out


def for_kf(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    p = payload or {}
    focus = p.get("concepts") or [
        "gdp",
        "inflation",
        "earnings_quality",
        "free_cash_flow",
        "wacc",
        "capital_allocation",
        "roic_wacc_spread",
        "value_creation",
    ]
    return {
        "consumer": "KF",
        "usage": "Store canonical economics + accounting + corporate finance knowledge objects",
        "knowledge_objects": _bundle_concepts(list(focus)),
        "mental_models": [m.to_dict() for m in all_mental_models()],
    }


def for_kcv(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    from academy.quality import review_corpus

    review = review_corpus()
    return {
        "consumer": "KCV",
        "usage": "Only publish Academy objects that pass quality review",
        "quality": {"passed": review["passed"], "publishable": review["publishable"], "rejected": review["rejected"]},
        "objects": _bundle_concepts(
            ["inflation", "gdp", "earnings_quality", "accruals", "free_cash_flow", "revenue_recognition"]
        ),
    }


def for_eve(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """EVE: accounting consistency + capital-structure relationship checks."""
    p = payload or {}
    eq = score_earnings_quality(p)
    flags = score_red_flags(p)
    return {
        "consumer": "EVE",
        "usage": "Verify accounting consistency, detect anomalies, and validate capital-structure relationships",
        "earnings_quality": eq,
        "red_flags": flags,
        "concepts": _bundle_concepts(
            [
                "earnings_quality",
                "accruals",
                "restatements",
                "revenue_recognition",
                "financial_leverage",
                "optimal_capital_structure",
                "wacc",
            ]
        ),
        "capital_structure_checks": {
            "leverage_vs_optimal": p.get("leverage_vs_optimal"),
            "interest_coverage": p.get("interest_coverage"),
            "note": "Flag inconsistency when leverage rises while coverage and ROIC–WACC spread deteriorate",
        },
        "anomaly": (not flags.get("clean")) or eq.get("label") == "low",
    }


def for_iie(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    p = payload or {}
    cid = str(p.get("concept_id") or "capital_allocation")
    ko = knowledge_by_id().get(cid)
    eq = score_earnings_quality(p)
    return {
        "consumer": "IIE",
        "concept_id": cid,
        "industry_impact": ko.industry_impact if ko else {},
        "company_impact": ko.company_impact if ko else {},
        "investment_impact": ko.investment_impact if ko else [],
        "decision_framework": ko.decision_framework if ko else [],
        "management_decisions": ko.management_decisions if ko else [],
        "earnings_quality": eq,
        "management_quality": {
            "capital_allocation": _bundle_concepts(["capital_allocation", "roic_wacc_spread", "acquisition_quality", "share_buybacks"]),
            "note": "Score management by incremental ROIC vs WACC and payout/deal discipline",
        },
        "business_quality_note": "Haircut business quality when earnings quality is low or ROIC < WACC on growth",
        "causal_models": [c.to_dict() for c in all_causal_models() if cid in c.related_concepts],
    }


def for_ve(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    p = payload or {}
    ids = p.get("concepts") or [
        "free_cash_flow",
        "earnings_quality",
        "wacc",
        "cost_of_equity",
        "roic_wacc_spread",
        "economic_profit",
        "share_buybacks",
        "leases",
    ]
    guidance = []
    kb = knowledge_by_id()
    for cid in ids:
        ko = kb.get(cid)
        if ko:
            guidance.append(
                {
                    "concept_id": cid,
                    "valuation_impact": ko.valuation_impact,
                    "investment_impact": ko.investment_impact,
                    "red_flags": ko.red_flags,
                }
            )
    eq = score_earnings_quality(p)
    return {
        "consumer": "VE",
        "note": "Academy advises WACC, terminal fade (ROIC→WACC), and cash-flow selection; VE values",
        "preferred_cash_flow": "FCFF from clean EBIT(1-t) after WC and capex — not raw EBITDA",
        "wacc_guidance": _bundle_concepts(["wacc", "cost_of_equity", "cost_of_debt", "beta", "equity_risk_premium"]),
        "terminal_guidance": "Fade ROIC toward WACC; g < WACC; growth only if incremental ROIC supports it",
        "earnings_quality": eq,
        "guidance": guidance,
    }


def for_fle(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    p = payload or {}
    ids = p.get("concepts") or [
        "gdp",
        "revenue_recognition",
        "working_capital",
        "free_cash_flow",
        "organic_reinvestment",
        "incremental_roic",
        "wacc",
        "capital_allocation",
    ]
    kb = knowledge_by_id()
    drivers = []
    for cid in ids:
        ko = kb.get(cid)
        if ko:
            drivers.append({"concept_id": cid, "forecast_impact": ko.forecast_impact, "effects": ko.effects})
    return {
        "consumer": "FLE",
        "usage": "Forecast reinvestment, incremental ROIC, financing, and payout — not revenue alone",
        "drivers": drivers,
        "earnings_quality": score_earnings_quality(p),
        "example_chain": next(c.to_dict() for c in all_causal_models() if c.model_id == "capital_allocation_to_value"),
    }


def for_irp(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    p = payload or {}
    cid = str(p.get("concept_id") or "value_creation")
    return {
        "consumer": "IRP",
        "teaching": teach(cid),
        "neighborhood": concept_neighborhood(cid),
        "earnings_quality": score_earnings_quality(p),
        "value_creation_frame": _bundle_concepts(["roic_wacc_spread", "economic_profit", "capital_allocation", "wacc"]),
        "usage": "Explain value creation with corporate-finance principles in reasoning traces",
    }


def for_fiml(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    p = payload or {}
    return {
        "consumer": "FIML",
        "usage": "Consume Academy economics + accounting concepts as curriculum substrate",
        "economics_concepts": _bundle_concepts(
            p.get("economics_concepts")
            or ["gdp", "inflation", "monetary_policy", "aggregate_demand", "exchange_rates"]
        ),
        "accounting_concepts": _bundle_concepts(
            p.get("accounting_concepts")
            or ["earnings_quality", "free_cash_flow", "working_capital", "revenue_recognition", "roic"]
        ),
        "corporate_finance_concepts": _bundle_concepts(
            p.get("corporate_finance_concepts")
            or ["wacc", "capital_allocation", "roic_wacc_spread", "share_buybacks", "acquisition_quality"]
        ),
        "causal_models": [c.to_dict() for c in all_causal_models()],
        "earnings_quality": score_earnings_quality(p),
    }


CONSUMER_MAP = {
    "kf": for_kf,
    "kcv": for_kcv,
    "kc": for_kcv,
    "eve": for_eve,
    "iie": for_iie,
    "ve": for_ve,
    "fle": for_fle,
    "irp": for_irp,
    "fiml": for_fiml,
}


def for_engine(engine: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    key = (engine or "").lower().strip()
    fn = CONSUMER_MAP.get(key)
    if not fn:
        raise KeyError(f"Unknown Academy consumer: {engine}")
    return fn(payload or {})
