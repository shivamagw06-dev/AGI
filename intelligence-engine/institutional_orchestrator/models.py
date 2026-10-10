"""UAG-01 core objects — InstitutionalQuery and InstitutionalResponse."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class ExecutionStep:
    step_id: str
    object_type: str
    provider: str
    purpose: str
    status: str = "planned"  # planned | ok | missing | error | skipped
    latency_ms: float = 0.0
    detail: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "object_type": self.object_type,
            "provider": self.provider,
            "purpose": self.purpose,
            "status": self.status,
            "latency_ms": float(self.latency_ms),
            "detail": self.detail,
        }


@dataclass(frozen=True)
class InstitutionalQuery:
    """Stateless query plan — orchestration metadata only."""

    query_id: str
    question: str
    intent: str
    entities: tuple[str, ...] = ()
    planners: tuple[str, ...] = ()
    required_objects: tuple[str, ...] = ()
    execution_plan: tuple[ExecutionStep, ...] = ()
    diagnostics: Optional[dict[str, Any]] = None
    generated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "question": self.question,
            "intent": self.intent,
            "entities": list(self.entities),
            "planners": list(self.planners),
            "required_objects": list(self.required_objects),
            "execution_plan": [s.to_dict() for s in self.execution_plan],
            "diagnostics": dict(self.diagnostics or {}),
            "generated_at": self.generated_at,
            "llm": False,
            "owns_business_state": False,
        }


@dataclass(frozen=True)
class EvidenceRef:
    object_type: str
    object_id: str
    label: str
    snippet: str = ""
    provider: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "object_type": self.object_type,
            "object_id": self.object_id,
            "label": self.label,
            "snippet": self.snippet,
            "provider": self.provider,
        }


@dataclass(frozen=True)
class InstitutionalResponse:
    """Assembled institutional answer — no new investment recommendations."""

    query_id: str
    question: str
    intent: str
    direct_answer: str
    why: tuple[str, ...] = ()
    supporting_evidence: tuple[EvidenceRef, ...] = ()
    related_risks: tuple[str, ...] = ()
    related_observations: tuple[str, ...] = ()
    committee_history: tuple[str, ...] = ()
    related_portfolio_impacts: tuple[str, ...] = ()
    confidence: int = 0
    evidence_lineage: tuple[str, ...] = ()
    objects_consulted: tuple[str, ...] = ()
    execution_plan: tuple[ExecutionStep, ...] = ()
    missing_objects: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    sections: dict[str, Any] = field(default_factory=dict)
    diagnostics: Optional[dict[str, Any]] = None
    generated_at: str = ""
    llm: bool = False
    generates_recommendations: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "question": self.question,
            "intent": self.intent,
            "direct_answer": self.direct_answer,
            "why": list(self.why),
            "supporting_evidence": [e.to_dict() for e in self.supporting_evidence],
            "related_risks": list(self.related_risks),
            "related_observations": list(self.related_observations),
            "committee_history": list(self.committee_history),
            "related_portfolio_impacts": list(self.related_portfolio_impacts),
            "confidence": int(self.confidence),
            "evidence_lineage": list(self.evidence_lineage),
            "objects_consulted": list(self.objects_consulted),
            "execution_plan": [s.to_dict() for s in self.execution_plan],
            "missing_objects": list(self.missing_objects),
            "warnings": list(self.warnings),
            "sections": dict(self.sections or {}),
            "diagnostics": dict(self.diagnostics or {}),
            "generated_at": self.generated_at,
            "llm": False,
            "generates_recommendations": False,
            "owns_business_state": False,
            "orchestration_only": True,
        }
