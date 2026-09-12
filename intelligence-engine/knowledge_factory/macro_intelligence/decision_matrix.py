"""Macro Decision Matrix — how regimes affect framework selection/confidence.

Knowledge only. Does not change Phases 1–7 planners; enriches consumable knowledge.
"""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence.playbooks.catalog import regime_playbook

# Explicit matrix rows (regime → framework guidance)
_MATRIX: dict[str, dict[str, Any]] = {
    "high_rates_high_inflation": {
        "label": "High-rate, high-inflation",
        "preferred_frameworks": [
            "balance_sheet_strength",
            "roic",
            "cash_flow",
            "residual_income",  # banks
        ],
        "deemphasise_frameworks": [
            "long_duration_growth_assumptions",
            "aggressive_terminal_value_dcf",
        ],
        "confidence_adjustments": {
            "dcf_stable": -0.15,
            "residual_income": 0.10,
            "roic_quality": 0.10,
            "ev_sales_growth": -0.20,
        },
        "component_regimes": ["high_rates", "high_inflation"],
    },
    "low_rates_high_liquidity": {
        "label": "Low-rate, high-liquidity",
        "preferred_frameworks": ["dcf", "growth_oriented_valuation", "ev_sales"],
        "deemphasise_frameworks": ["distress_focused"],
        "confidence_adjustments": {
            "dcf_stable": 0.10,
            "growth": 0.10,
            "distress": -0.15,
        },
        "component_regimes": ["low_rates", "liquidity_expansion"],
    },
    "commodity_boom": {
        "label": "Commodity boom",
        "preferred_frameworks": ["margin_sustainability", "capital_allocation", "cycle_analysis", "midcycle_dcf"],
        "deemphasise_frameworks": ["static_historical_averages_without_cycle_context", "peak_earnings_pe"],
        "confidence_adjustments": {
            "midcycle_dcf": 0.15,
            "peak_earnings_pe": -0.25,
        },
        "component_regimes": ["commodity_boom"],
    },
    "risk_off_contraction": {
        "label": "Risk-off / contraction",
        "preferred_frameworks": ["balance_sheet", "cash_flow", "through_cycle"],
        "deemphasise_frameworks": ["momentum_growth", "peak_cycle_multiples"],
        "confidence_adjustments": {"balance_sheet": 0.15, "growth": -0.20},
        "component_regimes": ["risk_off", "contraction"],
    },
}


def decision_matrix_for_regimes(active_regimes: list[str]) -> dict[str, Any]:
    """Merge matrix rows matching active regimes; always attach playbook frameworks."""
    active = {r.lower().replace(" ", "_") for r in active_regimes}
    matched_rows = []
    preferred: list[str] = []
    deemph: list[str] = []
    conf: dict[str, float] = {}

    for row_id, row in _MATRIX.items():
        comps = set(row.get("component_regimes") or [])
        if comps & active or row_id in active:
            matched_rows.append({"id": row_id, **row})
            preferred.extend(row.get("preferred_frameworks") or [])
            deemph.extend(row.get("deemphasise_frameworks") or [])
            for k, v in (row.get("confidence_adjustments") or {}).items():
                conf[k] = round(conf.get(k, 0.0) + float(v), 4)

    # Enrich from playbooks
    for r in active:
        pb = regime_playbook(r)
        preferred.extend(pb.get("preferred_valuation_frameworks") or [])
        deemph.extend(pb.get("frameworks_to_deemphasise") or [])

    # Dedupe preserve order
    def _dedupe(xs: list[str]) -> list[str]:
        seen = set()
        out = []
        for x in xs:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    return {
        "active_regimes": sorted(active),
        "matched_rows": matched_rows,
        "preferred_frameworks": _dedupe(preferred),
        "deemphasise_frameworks": _dedupe(deemph),
        "confidence_adjustments": conf,
        "architecture_note": "Knowledge only — planners consume; Phases 1–7 unchanged",
        "fabricated": False,
    }


def full_decision_matrix() -> dict[str, Any]:
    return {"rows": _MATRIX, "n": len(_MATRIX)}
