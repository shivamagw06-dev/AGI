"""Module 4 — Evidence Provenance.

Every metric answers: Where? When? Who? How? Validated?
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

PROVENANCE_VERSION = "evidence-provenance-v1.0.0"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def metric_provenance(
    *,
    field: str,
    value: Any,
    entity_id: str,
    provider: str,
    method: str,
    validated: bool,
    quality: float | None = None,
    as_of: str | None = None,
    data_class: str = "seed_panel",
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Canonical provenance envelope for one metric observation."""
    payload = {
        "field": field,
        "value": value,
        "symbol": str(entity_id).upper(),
        "entity_id": str(entity_id).upper(),
        "provider": provider,
        "who": provider,
        "where": provider,
        "when": as_of or now_iso(),
        "how": method,
        "validated": bool(validated),
        "verified": bool(validated),
        "verified_at": as_of or now_iso(),
        "as_of": as_of or now_iso(),
        "quality": quality,
        "data_class": data_class,
        "provenance_version": PROVENANCE_VERSION,
        "winning_provider": provider,
        "source": provider,
    }
    if extra:
        payload.update(extra)
    return payload
