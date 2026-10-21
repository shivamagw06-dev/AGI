"""Provenance for IERI relationship objects — never fabricate."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_factory.economic_relationship_intelligence.schema import IERI_VERSION, UNKNOWN


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
    src = source or UNKNOWN
    return {
        "source": src,
        "retrieved_at": ts,
        "validated_at": validated_at or ts,
        "collector": collector,
        "confidence": round(float(confidence), 4),
        "derived_from": list(derived_from or []),
        "version": version or IERI_VERSION,
        "fabricated": False,
    }
