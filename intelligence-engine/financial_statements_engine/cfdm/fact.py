"""Financial Fact — core CFDM entity (FSE-03 §8)."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from financial_statements_engine.cfdm.evidence_ref import build_evidence_ref
from financial_statements_engine.cfdm.schema import FACT_STATUSES, VALIDATION_STATUSES
from financial_statements_engine.metric_registry.service import (
    MetricRegistryError,
    assert_canonical,
    to_normalized_value,
    validate_scale,
)
from financial_statements_engine.util import now_iso


def fact_identity(
    *,
    company_id: str,
    period_id: str,
    statement_type: str,
    metric: str,
    consolidation_type: str = "unknown",
) -> str:
    return "|".join([company_id, period_id, statement_type, metric, consolidation_type])


def fact_id_for(identity: str, version: int) -> str:
    digest = hashlib.sha256(f"{identity}|v{version}".encode("utf-8")).hexdigest()[:24]
    return f"fact:{digest}"


def build_fact(
    *,
    company_id: str,
    period_id: str,
    statement_type: str,
    metric: str,
    reported_value: float | int | None,
    currency: str = "INR",
    unit: str | None = None,
    scale: str = "crores",
    source: str,
    evidence_id: str | None = None,
    evidence: dict[str, Any] | None = None,
    confidence: float = 0.0,
    version: int = 1,
    previous_version: int | None = None,
    change_reason: str | None = None,
    effective_date: str | None = None,
    status: str = "draft",
    consolidation_type: str = "unknown",
    validation_status: str = "pending",
    validation_score: float | None = None,
    validation_engine_version: str | None = None,
    normalized_value: float | None = None,
    source_document: str | None = None,
    parser_version: str | None = None,
    collector_version: str | None = None,
) -> dict[str, Any]:
    """Build a Financial Fact. ``metric`` must be canonical (Metric Registry)."""
    try:
        metric = assert_canonical(metric)
    except MetricRegistryError as exc:
        raise ValueError(str(exc)) from exc

    if status not in FACT_STATUSES:
        raise ValueError(f"invalid fact status: {status}")
    if validation_status not in VALIDATION_STATUSES:
        raise ValueError(f"invalid validation_status: {validation_status}")
    if not validate_scale(scale) and status == "published":
        raise ValueError(f"invalid_scale_for_publish: {scale}")

    ev = evidence
    if ev is None and evidence_id:
        ev = build_evidence_ref(
            evidence_id=evidence_id,
            source=source,
            source_document=source_document,
            parser_version=parser_version,
            collector_version=collector_version,
            confidence=confidence,
        )
    if status == "published" and (not ev or not ev.get("evidence_id")):
        raise ValueError("published_fact_requires_evidence_id")

    if normalized_value is None:
        normalized_value = to_normalized_value(
            reported_value if isinstance(reported_value, (int, float)) else None,
            scale,
        )

    identity = fact_identity(
        company_id=company_id,
        period_id=period_id,
        statement_type=statement_type,
        metric=metric,
        consolidation_type=consolidation_type,
    )
    ts = now_iso()
    return {
        "fact_id": fact_id_for(identity, version),
        "identity": identity,
        "company_id": company_id,
        "period_id": period_id,
        "statement_type": statement_type,
        "metric": metric,
        "reported_value": reported_value,
        "normalized_value": normalized_value,
        "currency": currency,
        "unit": unit or scale,
        "scale": scale,
        "source": source,
        "confidence": confidence,
        "version": int(version),
        "previous_version": previous_version,
        "change_reason": change_reason,
        "effective_date": effective_date,
        "status": status,
        "validation_status": validation_status,
        "validation_score": validation_score,
        "validation_timestamp": ts if validation_status != "pending" else None,
        "validation_engine_version": validation_engine_version,
        "evidence": ev,
        "consolidation_type": consolidation_type,
        "created_at": ts,
        "updated_at": ts,
        "object": "financial_fact",
        "immutable": status in ("published", "superseded"),
    }


def facts_fingerprint(facts: list[dict[str, Any]]) -> str:
    payload = [
        {
            "metric": f.get("metric"),
            "normalized_value": f.get("normalized_value"),
            "version": f.get("version"),
            "period_id": f.get("period_id"),
        }
        for f in sorted(facts, key=lambda x: str(x.get("metric")))
    ]
    return hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode("utf-8")).hexdigest()[:20]
