"""Standard retrieval interface for Ask AGI knowledge sources."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class EvidenceItem:
    source: str
    entity: str
    summary: str
    confidence: float = 0.6
    timestamp: str | None = None
    score: float = 0.0
    freshness: str = "unknown"
    reason: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    path: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "entity": self.entity,
            "summary": self.summary,
            "confidence": self.confidence,
            "timestamp": self.timestamp,
            "retrieval_score": self.score,
            "freshness": self.freshness,
            "reason": self.reason,
            "metrics": self.metrics,
            "path": self.path,
            "fabricated": False,
        }


class IntelligenceSource(Protocol):
    source_id: str

    def search(self, query: str, *, ticker: str | None = None) -> list[EvidenceItem]:
        ...

    def last_updated(self) -> str | None:
        ...
