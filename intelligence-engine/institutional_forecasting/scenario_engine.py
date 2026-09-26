"""FG-01 scenario engine — public API: run_scenario(graph, assumptions)."""

from __future__ import annotations

import hashlib
from typing import Any, Optional, Sequence

from institutional_decision.decision_engine import _recommendation_from_score
from institutional_decision.models import InstitutionalDecision
from institutional_forecasting.assumptions import ScenarioAssumption, banking_preset_assumptions
from institutional_forecasting.probability import probability_for, validate_probability
from institutional_forecasting.propagation import propagate, score_delta_from_impacts
from institutional_forecasting.scenario import ForecastScenario
from institutional_forecasting.schema import (
    DEFAULT_HORIZON,
    FG_VERSION,
    PROPAGATION_VERSION,
    SCENARIO_ENGINE_VERSION,
)
from institutional_forecasting.sensitivity import compute_sensitivity
from institutional_graph.graph import InstitutionalKnowledgeGraph

try:
    from financial_statements_engine.util import now_iso
except Exception:  # noqa: BLE001
    from datetime import datetime, timezone

    def now_iso() -> str:  # type: ignore[misc]
        return datetime.now(timezone.utc).isoformat()


def _scenario_id(ticker: str, name: str, assumptions: Sequence[ScenarioAssumption]) -> str:
    raw = "|".join(
        f"{a.node_key}:{a.magnitude}:{a.scenario_value}" for a in assumptions
    )
    digest = hashlib.sha256(f"{ticker}|{name}|{raw}".encode()).hexdigest()[:12]
    return f"fg-{ticker.lower()}-{name}-{digest}"


def _confidence_for_scenario(
    base_confidence: int,
    score_delta: float,
    decision_changed: bool,
) -> int:
    """Deterministic confidence adjustment — not ML."""
    conf = int(base_confidence)
    conf += int(round(score_delta * 3))
    if decision_changed:
        conf -= 2
    return max(35, min(92, conf))


def _reason_changes(
    base_rec: str,
    new_rec: str,
    components: dict[str, float],
) -> tuple[str, ...]:
    changes: list[str] = []
    if base_rec != new_rec:
        changes.append(f"recommendation {base_rec} → {new_rec}")
    for key, val in sorted(components.items(), key=lambda x: -abs(x[1])):
        if abs(val) < 0.05:
            continue
        direction = "improves" if val > 0 else "deteriorates"
        changes.append(f"{key} {direction} ({val:+.2f})")
    return tuple(changes[:12])


def run_scenario(
    graph: InstitutionalKnowledgeGraph,
    assumptions: Sequence[ScenarioAssumption] | None = None,
    *,
    decision: InstitutionalDecision | None = None,
    scenario_name: str = "custom",
    horizon: str = DEFAULT_HORIZON,
    probability: float | None = None,
    probability_distribution: dict[str, float] | None = None,
    include_sensitivity: bool = True,
) -> ForecastScenario:
    """
    Public API.

    run_scenario(graph, assumptions) → ForecastScenario
      → updated knowledge impacts
      → updated decision (scenario-local; live decision unchanged)
    """
    name = str(scenario_name or "custom").strip().lower()
    assump = tuple(assumptions or ())
    if not assump:
        assump = banking_preset_assumptions(name)

    prob = (
        float(probability)
        if probability is not None
        else probability_for(name, probability_distribution)
    )

    sid = _scenario_id(graph.ticker, name, assump)
    prop = propagate(
        graph,
        assump,
        horizon=horizon,
        scenario_id=sid,
        probability=prob,
    )
    score_delta, components = score_delta_from_impacts(graph, prop.node_impacts)

    base_rec = ""
    base_conf = 0
    base_score = 0
    if decision is not None:
        base_rec = str(decision.recommendation or "").upper()
        base_conf = int(decision.confidence)
        base_score = int(decision.score)
    else:
        # Fall back to decision node attributes
        dnode = graph.get(graph.decision_node_id) if graph.decision_node_id else None
        if dnode:
            base_rec = str((dnode.attributes or {}).get("recommendation") or "HOLD").upper()
            base_conf = int(round(float(dnode.confidence) * 100)) if dnode.confidence <= 1 else int(dnode.confidence)
            base_score = int((dnode.attributes or {}).get("score") or 0)

    resulting_score = int(round(base_score + score_delta))
    # Clamp to institutional score band roughly used by IDS
    resulting_score = max(-3, min(10, resulting_score))
    new_rec, new_conv = _recommendation_from_score(resulting_score)
    decision_changed = bool(base_rec and new_rec != base_rec)
    new_conf = _confidence_for_scenario(base_conf or 70, score_delta, decision_changed)

    sensitivity: dict[str, Any] = {}
    if include_sensitivity:
        sensitivity = compute_sensitivity(graph, horizon=horizon, probability=1.0)

    diagnostics = {
        "scenario_engine_version": SCENARIO_ENGINE_VERSION,
        "propagation_version": PROPAGATION_VERSION,
        "propagation_time_ms": round(prop.elapsed_ms, 4),
        "affected_nodes": len(prop.changed_nodes),
        "assumption_count": len(assump),
        "probability": prob,
        "score_delta": score_delta,
        "components": components,
        "decision_changed": decision_changed,
        "confidence_delta": new_conf - (base_conf or 0),
    }

    calibration_summary = {
        "base_confidence": base_conf,
        "resulting_confidence": new_conf,
        "confidence_delta": new_conf - (base_conf or 0),
        "note": "Scenario confidence is deterministically adjusted from calibrated base — not ML",
    }

    return ForecastScenario(
        scenario_id=sid,
        scenario_name=name,
        horizon=horizon,
        probability=prob,
        assumptions=assump,
        changed_nodes=tuple(prop.changed_nodes),
        propagated_impacts=tuple(prop.propagated_impacts),
        resulting_decision=new_rec,
        resulting_confidence=new_conf,
        resulting_conviction=new_conv,
        base_decision=base_rec,
        base_confidence=base_conf,
        decision_changed=decision_changed,
        confidence_delta=new_conf - (base_conf or 0),
        score_delta=float(score_delta),
        resulting_score=resulting_score,
        base_score=base_score,
        reason_changes=_reason_changes(base_rec, new_rec, components),
        graph_changes=tuple(prop.graph_changes),
        calibration_summary=calibration_summary,
        forecast_graph=prop.forecast_graph.to_dict(),
        sensitivity=sensitivity,
        diagnostics=diagnostics,
        version=FG_VERSION,
        engine_version=SCENARIO_ENGINE_VERSION,
        ticker=graph.ticker,
        generated_at=now_iso(),
        llm=False,
    )
