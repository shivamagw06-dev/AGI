"""InstitutionalObservation — first-class proactive monitoring object."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class InstitutionalObservation:
    """Immutable, versioned observation of a meaningful institutional change."""

    observation_id: str
    company: str
    timestamp: str
    category: str
    severity: str
    confidence: float
    summary: str
    evidence_snapshot_id: str
    affected_entities: tuple[str, ...] = ()
    affected_reasons: tuple[str, ...] = ()
    affected_decisions: tuple[str, ...] = ()
    affected_forecasts: tuple[str, ...] = ()
    requires_review: bool = False
    recommended_action: str = "Monitor"
    ticker: str = ""
    materiality: str = ""
    decision_changed: bool = False
    previous_decision: str = ""
    current_decision: str = ""
    previous_confidence: int = 0
    current_confidence: int = 0
    re_evaluated: bool = False
    silent: bool = False
    watchlist_priority: bool = False
    lineage: tuple[str, ...] = (
        "Evidence",
        "Observation",
        "Knowledge Graph",
        "Reason",
        "Decision",
        "Calibration",
        "Forecast",
        "Report",
    )
    diagnostics: dict[str, Any] = field(default_factory=dict)
    version: str = ""
    engine_version: str = ""
    hysteresis_version: str = ""
    llm: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "observation_id": self.observation_id,
            "company": self.company,
            "ticker": self.ticker or self.company,
            "timestamp": self.timestamp,
            "category": self.category,
            "severity": self.severity,
            "confidence": float(self.confidence),
            "summary": self.summary,
            "evidence_snapshot_id": self.evidence_snapshot_id,
            "affected_entities": list(self.affected_entities),
            "affected_reasons": list(self.affected_reasons),
            "affected_decisions": list(self.affected_decisions),
            "affected_forecasts": list(self.affected_forecasts),
            "requires_review": bool(self.requires_review),
            "recommended_action": self.recommended_action,
            "materiality": self.materiality,
            "decision_changed": bool(self.decision_changed),
            "previous_decision": self.previous_decision,
            "current_decision": self.current_decision,
            "previous_confidence": self.previous_confidence,
            "current_confidence": self.current_confidence,
            "re_evaluated": bool(self.re_evaluated),
            "silent": bool(self.silent),
            "watchlist_priority": bool(self.watchlist_priority),
            "lineage": list(self.lineage),
            "diagnostics": dict(self.diagnostics or {}),
            "version": self.version,
            "engine_version": self.engine_version,
            "hysteresis_version": self.hysteresis_version,
            "llm": False,
        }
