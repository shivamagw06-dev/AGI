"""Audited institutional data objects for DVC."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_field_version() -> str:
    return f"v-{uuid4().hex[:10]}"


def make_validated_field(
    *,
    field: str,
    value: Any,
    provider: str,
    confidence: float,
    symbol: str,
    unit: str | None = None,
    fallback_provider: str | None = None,
    previous_value: Any = None,
    rejected_providers: list[str] | None = None,
    reason: str | None = None,
    observations: list[dict[str, Any]] | None = None,
    validation_status: str = "validated",
) -> dict[str, Any]:
    """Every canonical field becomes an audited institutional data object."""
    prev = previous_value
    changed = None
    change_pct = None
    try:
        if prev is not None and value is not None and isinstance(value, (int, float)) and isinstance(prev, (int, float)) and prev != 0:
            changed = float(value) - float(prev)
            change_pct = (changed / float(prev)) * 100.0
    except Exception:
        pass
    return {
        "field": field,
        "symbol": (symbol or "").upper(),
        "value": value,
        "unit": unit,
        "provider": provider,
        "verified_at": _now(),
        "confidence": round(float(confidence), 4),
        "fallback_provider": fallback_provider,
        "previous_value": prev,
        "changed": changed,
        "change_percent": round(change_pct, 4) if change_pct is not None else None,
        "version": new_field_version(),
        "validation_status": validation_status,
        "rejected_providers": rejected_providers or [],
        "reason": reason,
        "observations": observations or [],
        "consensus_history": [],
        "dvc_version": "dvc-v1.0.0",
    }


Severity = Literal["low", "medium", "high", "critical"]
