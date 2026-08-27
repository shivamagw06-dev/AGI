"""Dynamic confidence engine — configurable inputs, no hallucinated certainty."""

from __future__ import annotations

import datetime as _dt
from typing import Iterable

from app.eve.models import EvidenceObject
from app.eve.sources import reliability_for


def score_confidence(
    *,
    source_reliability: float,
    supporting_sources: int = 1,
    document_freshness: float = 0.8,
    consistency: float = 0.7,
    historical_stability: float = 0.7,
    parser_confidence: float = 0.7,
    extraction_quality: float = 0.7,
    recency: float = 0.8,
    human_verification: float = 0.0,
) -> float:
    score = (
        0.22 * _clamp(source_reliability)
        + 0.14 * min(1.0, supporting_sources / 3.0)
        + 0.12 * _clamp(document_freshness)
        + 0.12 * _clamp(consistency)
        + 0.10 * _clamp(historical_stability)
        + 0.10 * _clamp(parser_confidence)
        + 0.08 * _clamp(extraction_quality)
        + 0.08 * _clamp(recency)
        + 0.04 * _clamp(human_verification)
    )
    return round(max(0.05, min(0.995, score)), 4)


def freshness_from_timestamp(ts: str | None, *, half_life_days: float = 120.0) -> float:
    if not ts:
        return 0.35
    try:
        dt = _dt.datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except ValueError:
        return 0.35
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    age = max(0.0, (_dt.datetime.now(_dt.timezone.utc) - dt).total_seconds() / 86400.0)
    import math

    return round(max(0.05, min(1.0, math.exp(-age / max(1.0, half_life_days)))), 4)


def confidence_for_evidence(
    evidence: EvidenceObject,
    *,
    peers: Iterable[EvidenceObject] = (),
    source_category: str = "",
) -> float:
    peers = list(peers)
    supporting = 1 + sum(
        1
        for p in peers
        if p.evidence_id != evidence.evidence_id
        and not p.soft_deleted
        and p.fact_key == evidence.fact_key
        and p.company_id == evidence.company_id
    )
    # consistency: fraction of peers with similar confidence band / non-conflict status
    consistent = sum(1 for p in peers if p.verification_status != "conflicted")
    consistency = (consistent / len(peers)) if peers else 0.75
    # prefer explicit source reliability via category
    rel = reliability_for(source_category or evidence.provenance.source_name or "unknown")
    # if supporting_source_ids populated, bump
    supporting = max(supporting, len(evidence.supporting_source_ids) or 1)
    fresh = freshness_from_timestamp(evidence.last_confirmed_at or evidence.created_at)
    return score_confidence(
        source_reliability=rel,
        supporting_sources=supporting,
        document_freshness=fresh,
        consistency=consistency,
        historical_stability=0.75 if evidence.verification_status != "conflicted" else 0.4,
        parser_confidence=float(evidence.parser_confidence or 0.7),
        extraction_quality=float(evidence.extraction_quality or 0.7),
        recency=fresh,
        human_verification=1.0 if evidence.verification_status == "verified" and "human" in (evidence.metadata or {}) else 0.0,
    )


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))
