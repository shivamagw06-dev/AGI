"""Field-level provenance — required on every ICI field."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_factory.company_intelligence.schema import ICI_VERSION, PROVENANCE_FIELDS, UNKNOWN


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def provenance(
    *,
    source: str,
    collector: str,
    confidence: float = 0.7,
    derived_from: list[str] | str | None = None,
    retrieved_at: str | None = None,
    validated_at: str | None = None,
    version: str | None = None,
) -> dict[str, Any]:
    if isinstance(derived_from, str):
        derived_from = [derived_from]
    ts = retrieved_at or _now()
    env = {
        "source": source,
        "retrieved_at": ts,
        "validated_at": validated_at or ts,
        "collector": collector,
        "confidence": round(float(confidence), 4),
        "derived_from": list(derived_from or []),
        "version": version or ICI_VERSION,
        "fabricated": False,
    }
    for f in PROVENANCE_FIELDS:
        assert f in env, f"missing provenance field {f}"
    return env


def field(
    value: Any,
    *,
    source: str,
    collector: str,
    confidence: float = 0.7,
    derived_from: list[str] | str | None = None,
) -> dict[str, Any]:
    """Wrap a value with provenance. UNKNOWN is explicit, never invented."""
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


def module_block(module: str, payload: dict[str, Any], *, source: str, collector: str, confidence: float) -> dict[str, Any]:
    return {
        "module": module,
        "fields": payload,
        "provenance": provenance(source=source, collector=collector, confidence=confidence, derived_from=[module]),
        "fabricated": False,
    }
