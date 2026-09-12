"""Provenance for IIVI fields and objects."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_factory.industry_intelligence.schema import IIVI_VERSION, UNKNOWN


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def provenance(
    *,
    source: str,
    collector: str,
    confidence: float = 0.8,
    derived_from: list[str] | str | None = None,
    retrieved_at: str | None = None,
    validated_at: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    if isinstance(derived_from, str):
        derived_from = [derived_from]
    ts = retrieved_at or _now()
    return {
        "source": source,
        "retrieved_at": ts,
        "validated_at": validated_at or ts,
        "collector": collector,
        "confidence": round(float(confidence), 4),
        "derived_from": list(derived_from or []),
        "version": version or IIVI_VERSION,
        "fabricated": False,
    }


def field(value: Any, *, source: str, collector: str, confidence: float = 0.75, derived_from: list[str] | None = None) -> dict[str, Any]:
    is_unknown = value is None or value == UNKNOWN or value == ""
    return {
        "value": UNKNOWN if is_unknown else value,
        "status": "unknown" if is_unknown else "known",
        "provenance": provenance(
            source=source if not is_unknown else "unavailable",
            collector=collector,
            confidence=0.0 if is_unknown else confidence,
            derived_from=derived_from,
        ),
    }
