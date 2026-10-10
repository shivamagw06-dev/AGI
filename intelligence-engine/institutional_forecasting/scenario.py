"""ForecastScenario — immutable, versioned future-state object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from institutional_forecasting.assumptions import ScenarioAssumption
from institutional_forecasting.schema import DEFAULT_HORIZON, FG_VERSION, SCENARIO_ENGINE_VERSION


@dataclass(frozen=True)
class ForecastScenario:
    """Deterministic scenario result — never mutates the live decision in place."""

    scenario_id: str
    scenario_name: str
    horizon: str = DEFAULT_HORIZON
    probability: float = 0.0
    assumptions: tuple[ScenarioAssumption, ...] = ()
    changed_nodes: tuple[dict[str, Any], ...] = ()
    propagated_impacts: tuple[dict[str, Any], ...] = ()
    resulting_decision: Optional[str] = None
    resulting_confidence: Optional[int] = None
    resulting_conviction: str = ""
    base_decision: str = ""
    base_confidence: int = 0
    decision_changed: bool = False
    confidence_delta: int = 0
    score_delta: float = 0.0
    resulting_score: int = 0
    base_score: int = 0
    reason_changes: tuple[str, ...] = ()
    graph_changes: tuple[str, ...] = ()
    calibration_summary: dict[str, Any] = field(default_factory=dict)
    forecast_graph: dict[str, Any] = field(default_factory=dict)
    sensitivity: dict[str, Any] = field(default_factory=dict)
    diagnostics: dict[str, Any] = field(default_factory=dict)
    lineage: tuple[str, ...] = (
        "Evidence",
        "Knowledge Graph",
        "Scenario",
        "Propagation",
        "Inference",
        "Decision",
        "Calibration",
        "Report",
    )
    version: str = FG_VERSION
    engine_version: str = SCENARIO_ENGINE_VERSION
    ticker: str = ""
    generated_at: str = ""
    llm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "horizon": self.horizon,
            "probability": float(self.probability),
            "assumptions": [a.to_dict() for a in self.assumptions],
            "changed_nodes": [dict(x) for x in self.changed_nodes],
            "propagated_impacts": [dict(x) for x in self.propagated_impacts],
            "resulting_decision": self.resulting_decision,
            "resulting_confidence": self.resulting_confidence,
            "resulting_conviction": self.resulting_conviction,
            "base_decision": self.base_decision,
            "base_confidence": self.base_confidence,
            "decision_changed": self.decision_changed,
            "confidence_delta": self.confidence_delta,
            "score_delta": self.score_delta,
            "resulting_score": self.resulting_score,
            "base_score": self.base_score,
            "reason_changes": list(self.reason_changes),
            "graph_changes": list(self.graph_changes),
            "calibration_summary": dict(self.calibration_summary or {}),
            "forecast_graph": dict(self.forecast_graph or {}),
            "sensitivity": dict(self.sensitivity or {}),
            "diagnostics": dict(self.diagnostics or {}),
            "lineage": list(self.lineage),
            "version": self.version,
            "engine_version": self.engine_version,
            "ticker": self.ticker,
            "generated_at": self.generated_at,
            "llm": False,
        }
