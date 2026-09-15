"""Sensitivity engine — which variables influence the decision most."""

from __future__ import annotations

from typing import Any, Dict, List, Sequence

from institutional_forecasting.assumptions import ScenarioAssumption
from institutional_forecasting.propagation import propagate, score_delta_from_impacts
from institutional_forecasting.schema import SENSITIVITY_VERSION
from institutional_graph.graph import InstitutionalKnowledgeGraph

# Canonical sensitivity variables for banking single-company scope
SENSITIVITY_VARS = (
    ("nim", "NIM", 0.35),
    ("roe", "ROE", 0.35),
    ("credit_cost", "Credit Cost", 0.35),
    ("rbi_rate", "GDP / Policy Rate", 0.30),  # proxy macro lever in company scope
    ("valuation", "Valuation", 0.30),
    ("profitability", "Profitability", 0.30),
    ("business_quality", "Business Quality", 0.25),
)


def compute_sensitivity(
    graph: InstitutionalKnowledgeGraph,
    *,
    horizon: str = "12M",
    probability: float = 1.0,
) -> dict[str, Any]:
    """
    Institutional sensitivity scorecard.

    Each variable is shocked +magnitude independently; absolute score-delta
    is scaled to a display score (e.g. NIM +21).
    """
    rows: List[dict[str, Any]] = []
    for key, label, mag in SENSITIVITY_VARS:
        # For credit_cost / rbi_rate, positive shock is adverse — still measure influence
        assumption = ScenarioAssumption(
            assumption_id=f"sens-{key}",
            variable=label,
            node_key=key,
            current_value="baseline",
            scenario_value=f"+{mag:.2f} shock",
            direction="positive",
            magnitude=mag,
            confidence=1.0,
            notes="sensitivity probe",
        )
        result = propagate(
            graph,
            [assumption],
            horizon=horizon,
            scenario_id=f"sens-{key}",
            probability=probability,
        )
        delta, components = score_delta_from_impacts(graph, result.node_impacts)
        # Display points: scale |delta| into ~0–25 band with sign of economic influence
        # Credit cost / rate up → negative display when they hurt the decision score
        signed = delta
        display = int(round(signed * 8))  # 0.35 shock → roughly ± few to ±20
        # Prefer component-local contribution when available
        if key in components:
            display = int(round(components[key] * 8))
        rows.append(
            {
                "key": key,
                "variable": label,
                "score": display,
                "score_delta": round(delta, 4),
                "version": SENSITIVITY_VERSION,
            }
        )

    # Sort by absolute influence
    rows.sort(key=lambda r: abs(int(r["score"])), reverse=True)
    return {
        "version": SENSITIVITY_VERSION,
        "rows": rows,
        "scorecard": {r["variable"]: r["score"] for r in rows},
    }


def sensitivity_scorecard_dict(sensitivity: dict[str, Any]) -> dict[str, int]:
    return dict(sensitivity.get("scorecard") or {})
