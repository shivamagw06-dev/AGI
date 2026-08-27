"""Confidence scoring for ERE candidates."""

from __future__ import annotations

from typing import Any

from entity_resolution.schema import CONFIDENCE_THRESHOLD


def score_match(*, alias: str, entity: dict[str, Any], matched_on: str, source: str) -> float:
    """Score 0..1 for a candidate match. Never inflate ambiguous stems."""
    name = str(entity.get("canonical_name") or "").lower()
    ticker = str(entity.get("ticker") or "").lower()
    aliases = [str(a).lower() for a in (entity.get("aliases") or [])]
    a = (alias or "").lower().strip()

    score = 0.55
    if a == ticker and ticker:
        score = 0.995
    elif a == name:
        score = 0.99
    elif a in aliases:
        # longer alias → higher confidence
        score = 0.92 + min(0.07, len(a) / 100)
    elif matched_on == "ikg_id":
        score = 0.97
    elif matched_on == "ikg_alias":
        score = 0.93

    if source == "ikg":
        score = min(0.999, score + 0.02)
    # Historical entities remain resolvable when the alias uniquely names them
    if entity.get("status") == "historical" and a not in aliases and a != name and a != ticker:
        score = min(score, 0.8)
    # Short tokens are weaker unless they are an exact registered alias/ticker
    if len(a) <= 3 and a != ticker and a not in aliases and a != name:
        score = min(score, 0.7)
    return round(min(0.999, max(0.01, score)), 4)


def needs_clarification(confidence: float, candidate_count: int) -> bool:
    if candidate_count > 1:
        return True
    return float(confidence or 0) < CONFIDENCE_THRESHOLD


def threshold() -> float:
    return CONFIDENCE_THRESHOLD
