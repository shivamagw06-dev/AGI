"""Field-level provenance envelopes — institutional auditability."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from universe_intelligence.schema import PROVENANCE_FIELDS


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def provenance(
    *,
    source: str,
    collector: str = "iui_registry",
    confidence: float = 0.9,
    derived_from: list[str] | str | None = None,
    retrieved_at: str | None = None,
    validated_at: str | None = None,
    method: str = "registry",
) -> dict[str, Any]:
    """Every registry field carries provenance for audit / debug."""
    if isinstance(derived_from, str):
        derived_from = [derived_from]
    ts = retrieved_at or _now()
    env = {
        "source": source,
        "retrieved_at": ts,
        "validated_at": validated_at or ts,
        "confidence": round(float(confidence), 4),
        "collector": collector,
        "derived_from": list(derived_from or []),
        "method": method,
        "fabricated": False,
    }
    for f in PROVENANCE_FIELDS:
        assert f in env, f"missing provenance field {f}"
    return env


def field_with_provenance(value: Any, **prov_kwargs: Any) -> dict[str, Any]:
    return {"value": value, "provenance": provenance(**prov_kwargs)}


def attach_object_provenance(obj: dict[str, Any], **prov_kwargs: Any) -> dict[str, Any]:
    out = dict(obj)
    out["provenance"] = provenance(**prov_kwargs)
    out["fabricated"] = False
    return out
