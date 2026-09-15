"""Evidence graph edges."""

from __future__ import annotations

from typing import Any


def edge(
    source_id: str,
    target_id: str,
    *,
    relationship: str,
    weight: float = 0.7,
    confidence: float = 0.7,
    available_from: str | None = None,
    evidence_strength: float | None = None,
    order: int | None = None,
) -> dict[str, Any]:
    return {
        "source": source_id,
        "target": target_id,
        "relationship": relationship,
        "weight": float(weight),
        "confidence": float(confidence),
        "available_from": available_from,
        "evidence_strength": evidence_strength,
        "order": order,
        "fabricated": False,
    }
