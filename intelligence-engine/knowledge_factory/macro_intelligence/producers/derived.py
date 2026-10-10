"""Named macro derived producers — thin knowledge wrappers (no new reasoning engines)."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence.decision_matrix import decision_matrix_for_regimes
from knowledge_factory.macro_intelligence.fixtures.seed_macro import historical_macro_records, snapshot_as_of
from knowledge_factory.macro_intelligence.producers.impacts import relationship, sectors_for_driver, shock_impact
from knowledge_factory.macro_intelligence.producers.regime import classify_as_of, classify_current
from knowledge_factory.macro_intelligence.producers.similarity import similar_regimes


def macro_regime_producer(*, as_of: str | None = None) -> dict[str, Any]:
    return classify_as_of(as_of) if as_of else classify_current()


def macro_cycle_producer(*, as_of: str | None = None) -> dict[str, Any]:
    cls = macro_regime_producer(as_of=as_of)
    cycle = [
        r
        for r in (cls.get("active_regimes") or [])
        if r in {"expansion", "peak", "contraction", "recovery"}
    ]
    return {
        "producer": "macro_cycle",
        "cycle_regimes": cycle,
        "primary_regime": cls.get("primary_regime"),
        "as_of": cls.get("as_of"),
        "knowledge_only": True,
        "fabricated": False,
    }


def macro_risk_producer(*, as_of: str | None = None) -> dict[str, Any]:
    cls = macro_regime_producer(as_of=as_of)
    risks = [
        r
        for r in (cls.get("active_regimes") or [])
        if r
        in {
            "high_inflation",
            "high_rates",
            "yield_curve_inversion",
            "credit_contraction",
            "liquidity_tightening",
            "commodity_bust",
            "risk_off",
            "contraction",
        }
    ]
    return {
        "producer": "macro_risk",
        "elevated_risks": risks,
        "decision_matrix": cls.get("decision_matrix") or decision_matrix_for_regimes(cls.get("active_regimes") or []),
        "knowledge_only": True,
        "fabricated": False,
    }


def macro_valuation_producer(*, as_of: str | None = None) -> dict[str, Any]:
    cls = macro_regime_producer(as_of=as_of)
    matrix = cls.get("decision_matrix") or decision_matrix_for_regimes(cls.get("active_regimes") or [])
    return {
        "producer": "macro_valuation",
        "preferred_frameworks": matrix.get("preferred_frameworks") or [],
        "deemphasise_frameworks": matrix.get("deemphasise_frameworks") or [],
        "confidence_adjustments": matrix.get("confidence_adjustments") or {},
        "knowledge_only": True,
        "architecture_note": "Knowledge for existing framework selection; Phases 1–7 unchanged",
        "fabricated": False,
    }


def macro_sector_producer() -> dict[str, Any]:
    from knowledge_factory.macro_intelligence.links.sector import compile_sector_links

    return {"producer": "macro_sector", **compile_sector_links(), "knowledge_only": True}


def macro_company_producer() -> dict[str, Any]:
    from knowledge_factory.macro_intelligence.links.company import compile_company_links

    return {"producer": "macro_company", **compile_company_links(), "knowledge_only": True}


def macro_correlation_producer() -> dict[str, Any]:
    edges = []
    for macro, sector in (
        ("interest_rates", "banks"),
        ("interest_rates", "real_estate"),
        ("oil", "oil_gas"),
        ("oil", "logistics"),
        ("inflation", "fmcg"),
        ("usd", "it_services"),
    ):
        edges.append(relationship(macro, sector))
    return {
        "producer": "macro_correlation",
        "edges": edges,
        "n": len(edges),
        "knowledge_only": True,
        "fabricated": False,
    }


def macro_sensitivity_producer(*, macro: str = "interest_rates") -> dict[str, Any]:
    return {
        "producer": "macro_sensitivity",
        "benefit": sectors_for_driver(macro, direction=1),
        "hurt": sectors_for_driver(macro, direction=-1),
        "knowledge_only": True,
    }


def macro_trend_producer(*, macro_id: str = "interest_rates", as_of: str | None = None) -> dict[str, Any]:
    rows = list(historical_macro_records().get(macro_id) or [])
    if as_of:
        from knowledge_factory.macro_intelligence.store import filter_pit

        rows = filter_pit(rows, as_of)
    if len(rows) < 2:
        return {
            "producer": "macro_trend",
            "macro_id": macro_id,
            "insufficient": True,
            "reason": "macro_history_unavailable",
            "fabricated": False,
        }
    latest = float(rows[-1]["value"])
    prior = float(rows[-2]["value"])
    return {
        "producer": "macro_trend",
        "macro_id": macro_id,
        "latest": latest,
        "prior": prior,
        "delta": round(latest - prior, 6),
        "direction": "up" if latest > prior else "down" if latest < prior else "flat",
        "insufficient": False,
        "fabricated": False,
    }


def macro_similarity_producer(*, top_n: int = 3) -> dict[str, Any]:
    return {"producer": "macro_similarity", **similar_regimes(top_n=top_n)}


def macro_forecast_context_producer(*, as_of: str | None = None) -> dict[str, Any]:
    """Context pack for existing planners — not a new forecast engine."""
    snap = snapshot_as_of(as_of or "2026-03-31")
    cls = macro_regime_producer(as_of=as_of)
    val = macro_valuation_producer(as_of=as_of)
    return {
        "producer": "macro_forecast_context",
        "snapshot": snap,
        "regime": cls,
        "valuation_context": val,
        "oil_shock_reference": shock_impact("oil", 0.30),
        "knowledge_only": True,
        "not_a_forecast_engine": True,
        "fabricated": False,
    }
