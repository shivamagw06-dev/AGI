"""Immutable alternative-data observation objects."""

from __future__ import annotations

import hashlib
from typing import Any

from knowledge_factory.alternative_data_intelligence.provenance import provenance
from knowledge_factory.alternative_data_intelligence.schema import IADI_VERSION, UNKNOWN


def build_observation(
    *,
    dataset_id: str,
    date: str,
    value: float | int | str,
    available_from: str,
    source: str,
    collector: str,
    confidence: float = 0.8,
    unit: str | None = None,
    value_kind: str | None = None,
    evidence: str | list[str] | None = None,
    notes: str | None = None,
    provider: str | None = None,
    historical_version: str = "v1",
    derived_from: list[str] | None = None,
) -> dict[str, Any]:
    did = str(dataset_id or "").lower()
    if not did:
        raise ValueError("dataset_id required")
    if not date:
        raise ValueError("date required")
    if not available_from:
        raise ValueError("available_from required")
    if not source or source == UNKNOWN:
        raise ValueError("source required")

    # Point-in-time: observation must not be available before period
    if available_from < date:
        raise ValueError("future_leakage: available_from before observation date")

    evid = evidence if isinstance(evidence, list) else ([evidence] if evidence else [])
    fp = f"{did}|{date}|{value}|{available_from}|{historical_version}"
    oid = "OBS-" + hashlib.sha256(fp.encode("utf-8")).hexdigest()[:16].upper()

    return {
        "observation_id": oid,
        "dataset_id": did,
        "date": date,
        "available_from": available_from,
        "observation": {
            "value": value,
            "unit": unit,
            "value_kind": value_kind or "index",
            "status": "known" if value != UNKNOWN else "unknown",
        },
        "source": source,
        "provider": provider,
        "collector": collector,
        "confidence": round(float(confidence), 4),
        "evidence": evid,
        "validation": {"status": "pending", "gates": []},
        "historical_version": historical_version,
        "revision_history": [],
        "provenance": provenance(
            source=source,
            collector=collector,
            confidence=confidence,
            derived_from=derived_from or evid[:1],
        ),
        "notes": notes,
        "version": IADI_VERSION,
        "fabricated": False,
        "immutable": True,
    }
