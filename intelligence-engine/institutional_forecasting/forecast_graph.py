"""Forecast graph — ForecastNode / ForecastEdge / ForecastImpact."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List


@dataclass(frozen=True)
class ForecastNode:
    id: str
    label: str
    node_type: str
    shock: float
    impact: float
    horizon: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "type": self.node_type,
            "shock": float(self.shock),
            "impact": float(self.impact),
            "horizon": self.horizon,
            "confidence": float(self.confidence),
        }


@dataclass(frozen=True)
class ForecastEdge:
    id: str
    source_id: str
    target_id: str
    direction: str
    magnitude: float
    probability: float
    confidence: float
    time_horizon: str
    label: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "direction": self.direction,
            "magnitude": float(self.magnitude),
            "probability": float(self.probability),
            "confidence": float(self.confidence),
            "time_horizon": self.time_horizon,
            "label": self.label,
        }


@dataclass(frozen=True)
class ForecastImpact:
    node_id: str
    label: str
    impact: float
    path: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "label": self.label,
            "impact": float(self.impact),
            "path": list(self.path),
        }


@dataclass
class ForecastGraph:
    scenario_id: str
    horizon: str
    nodes: List[ForecastNode] = field(default_factory=list)
    edges: List[ForecastEdge] = field(default_factory=list)
    impacts: List[ForecastImpact] = field(default_factory=list)
    version: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "horizon": self.horizon,
            "version": self.version,
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
            "impacts": [i.to_dict() for i in self.impacts],
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
        }
