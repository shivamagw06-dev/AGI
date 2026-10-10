"""IRE-02 Reason object — structured institutional reasoning (no English)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Reason:
    """One auditable reasoning unit behind a report section conclusion."""

    title: str
    conclusion: str
    confidence: float
    supporting_evidence: tuple[str, ...] = ()
    supporting_points: tuple[str, ...] = ()
    contradicting_points: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()
    section_key: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "conclusion": self.conclusion,
            "confidence": float(self.confidence),
            "supporting_evidence": list(self.supporting_evidence),
            "supporting_points": list(self.supporting_points),
            "contradicting_points": list(self.contradicting_points),
            "unknowns": list(self.unknowns),
            "section_key": self.section_key,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "Reason":
        body = dict(payload or {})

        def _tup(value: Any) -> tuple[str, ...]:
            if value is None:
                return ()
            if isinstance(value, str):
                text = value.strip()
                return (text,) if text else ()
            out: list[str] = []
            for item in value:
                text = str(item or "").strip()
                if text:
                    out.append(text)
            return tuple(out)

        conf = body.get("confidence")
        try:
            confidence = float(conf)
        except (TypeError, ValueError):
            confidence = -1.0
        return cls(
            title=str(body.get("title") or "").strip(),
            conclusion=str(body.get("conclusion") or "").strip(),
            confidence=confidence,
            supporting_evidence=_tup(body.get("supporting_evidence")),
            supporting_points=_tup(body.get("supporting_points")),
            contradicting_points=_tup(body.get("contradicting_points")),
            unknowns=_tup(body.get("unknowns")),
            section_key=str(body.get("section_key") or "").strip(),
        )


@dataclass
class ReasonGraph:
    """Ordered reasons keyed by report section."""

    reasons: list[Reason] = field(default_factory=list)

    def by_section(self) -> dict[str, Reason]:
        return {r.section_key: r for r in self.reasons if r.section_key}

    def to_dict(self) -> dict[str, Any]:
        return {
            "reason_count": len(self.reasons),
            "reasons": [r.to_dict() for r in self.reasons],
        }
