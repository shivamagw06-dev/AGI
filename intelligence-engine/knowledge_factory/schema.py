"""Knowledge Factory schemas — validated institutional knowledge envelopes."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

KF_SCHEMA_VERSION = "kf-schema-v1.0.0"
ALLOWED_SOURCES = (
    "yahoo",
    "groww",
    "nse",
    "bse",
    "rbi",
    "fred",
    "world_bank",
    "imf",
    "fixture",
    "derived",
)


@dataclass
class Provenance:
    source: str
    collected_at: str
    method: str = "collect"
    raw_ref: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class QualityEnvelope:
    entity: str | None
    timestamp: str
    source: str
    freshness_hours: float | None
    coverage: float
    quality: float
    provenance: dict[str, Any]
    rejected: bool = False
    reject_reasons: list[str] = field(default_factory=list)
    version: str = KF_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def dataset_envelope(
    *,
    kind: str,
    entity: str | None,
    source: str,
    timestamp: str,
    payload: dict[str, Any],
    freshness_hours: float | None = 0.0,
    coverage: float = 1.0,
    quality: float = 90.0,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "kind": kind,
        "entity": entity,
        "source": source,
        "timestamp": timestamp,
        "freshness_hours": freshness_hours,
        "coverage": coverage,
        "quality": quality,
        "provenance": provenance
        or {
            "source": source,
            "collected_at": timestamp,
            "method": "collect",
        },
        "payload": payload,
        "schema_version": KF_SCHEMA_VERSION,
    }
