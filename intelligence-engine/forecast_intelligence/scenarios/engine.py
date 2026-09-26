"""Scenario engine — always Bull / Base / Bear / Stress / Recovery."""

from __future__ import annotations

from typing import Any

from forecast_intelligence.assumptions.pack import assumptions_for
from forecast_intelligence.schema import SCENARIO_NAMES


def _impact_block(scenario: str, sector: str) -> dict[str, Any]:
    tone = {
        "bull": "improving",
        "base": "stable",
        "bear": "deteriorating",
        "stress": "severely stressed",
        "recovery": "repairing",
    }[scenario]
    return {
        "business": f"Business trajectory {tone} under {scenario} assumptions ({sector})",
        "financial": f"Financial outcomes {tone}; monitor scenario triggers",
        "valuation": f"Valuation impact {tone} via growth/ROE/spread path — not a price target",
        "portfolio": f"Portfolio behaviour under {scenario}: factor/stress exposure update only",
    }


def build_scenarios(
    profile: dict[str, Any],
    *,
    probabilities: dict[str, Any],
    triggers: dict[str, Any],
    catalysts: dict[str, Any],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    sector = profile.get("sector") or "banks"
    dist = probabilities.get("distribution") or {}
    matrix = (triggers or {}).get("matrix") or {}
    supporting = [e for e in (evidence or {}).get("items") or [] if e.get("kind") in {"profile_prior", "historical_analogue", "causal_soft"}]
    contradicting = [
        {
            "kind": "tail_risk",
            "note": "Stress/bear paths remain plausible; do not collapse to a single forecast",
            "source": "forecast_intelligence.scenarios",
        }
    ]
    out: list[dict[str, Any]] = []
    for name in SCENARIO_NAMES:
        assumptions = assumptions_for(sector, name)
        impact = _impact_block(name, sector)
        out.append(
            {
                "name": name,
                "label": name.replace("_", " ").title() + " Case" if name != "base" else "Base Case",
                "probability": dist.get(name),
                "confidence_note": "Scenario probability is dynamic and evidence-backed",
                "key_assumptions": assumptions,
                "supporting_evidence": supporting[:6],
                "contradicting_evidence": contradicting if name in {"bull", "base"} else supporting[:3],
                "expected_business_impact": impact["business"],
                "expected_financial_impact": impact["financial"],
                "expected_valuation_impact": impact["valuation"],
                "portfolio_impact": impact["portfolio"],
                "triggers": matrix.get(name) or [],
                "linked_catalysts": [
                    c.get("id")
                    for c in (catalysts or {}).get("items") or []
                    if (name == "bull" and c.get("polarity") == "positive")
                    or (name in {"bear", "stress"} and c.get("polarity") == "negative")
                    or (name in {"base", "recovery"})
                ][:6],
                "not_a_price_target": True,
            }
        )
    return out
