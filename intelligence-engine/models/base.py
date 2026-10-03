"""Shared FIML interfaces — every domain model implements these methods."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:12]}"


@dataclass
class ModelMeta:
    model_id: str
    domain: str
    version: str
    name: str
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AnalysisResult:
    object_type: str
    object_id: str
    domain: str
    model_version: str
    subject_id: str
    score: float
    label: str
    confidence: float
    summary: str
    outputs: dict[str, Any] = field(default_factory=dict)
    red_flags: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    weaknesses: list[str] = field(default_factory=list)
    evidence_links: list[str] = field(default_factory=list)
    relationships: list[dict[str, Any]] = field(default_factory=list)
    timeline: list[dict[str, Any]] = field(default_factory=list)
    explainability: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class DomainModel(ABC):
    """Reusable institutional domain model — no engine-specific logic."""

    domain: str = "base"
    version: str = "1.0.0"
    name: str = "Base Model"

    def meta(self) -> ModelMeta:
        return ModelMeta(
            model_id=f"fiml.{self.domain}",
            domain=self.domain,
            version=self.version,
            name=self.name,
            description=self.__doc__ or "",
        )

    @abstractmethod
    def analyse(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> AnalysisResult:
        raise NotImplementedError

    def score(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        result = self.analyse(payload, **kwargs)
        return {
            "domain": self.domain,
            "score": result.score,
            "label": result.label,
            "confidence": result.confidence,
            "subject_id": result.subject_id,
            "model_version": self.version,
        }

    def explain(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        result = self.analyse(payload, **kwargs)
        return {
            "domain": self.domain,
            "summary": result.summary,
            "explainability": result.explainability,
            "red_flags": result.red_flags,
            "strengths": result.strengths,
            "weaknesses": result.weaknesses,
            "evidence_links": result.evidence_links,
            "confidence": result.confidence,
        }

    def compare(self, left: dict[str, Any], right: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        a = self.analyse(left, **kwargs)
        b = self.analyse(right, **kwargs)
        return {
            "domain": self.domain,
            "left": {"subject_id": a.subject_id, "score": a.score, "label": a.label},
            "right": {"subject_id": b.subject_id, "score": b.score, "label": b.label},
            "delta_score": round(a.score - b.score, 4),
            "preferred": a.subject_id if a.score >= b.score else b.subject_id,
            "notes": [
                f"{a.subject_id}: {a.summary}",
                f"{b.subject_id}: {b.summary}",
            ],
        }

    def monitor(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        result = self.analyse(payload, **kwargs)
        signals = list(result.outputs.get("monitoring_signals") or [])
        if not signals:
            signals = [f"Watch {self.domain} score drift below {round(result.score - 0.1, 2)}"]
        return {
            "domain": self.domain,
            "subject_id": result.subject_id,
            "current_score": result.score,
            "signals": signals,
            "red_flags": result.red_flags,
        }

    def timeline(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        result = self.analyse(payload, **kwargs)
        return {
            "domain": self.domain,
            "subject_id": result.subject_id,
            "timeline": result.timeline
            or [{"at": result.created_at, "event": "analysis", "score": result.score}],
        }

    def search(self, query: str, *, limit: int = 20, **kwargs: Any) -> dict[str, Any]:
        return {
            "domain": self.domain,
            "query": query,
            "hits": [],
            "note": "Domain search is configuration/index backed; use registry.search for cross-model.",
            "limit": limit,
        }

    def relationships(self, payload: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        result = self.analyse(payload, **kwargs)
        return {
            "domain": self.domain,
            "subject_id": result.subject_id,
            "relationships": result.relationships,
        }


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, float(value)))


def num(payload: dict[str, Any] | None, key: str, default: float = 0.0) -> float:
    if not payload:
        return default
    try:
        val = payload.get(key, default)
        if val is None:
            return default
        return float(val)
    except (TypeError, ValueError):
        return default


def subject_id(payload: dict[str, Any] | None, default: str = "unknown") -> str:
    if not payload:
        return default
    return str(
        payload.get("company_symbol")
        or payload.get("symbol")
        or payload.get("company_id")
        or payload.get("subject_id")
        or payload.get("industry")
        or default
    ).upper()
