"""Shared collector helpers — fixture-first, live optional, never crash frameworks."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_factory.schema import dataset_envelope


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def ok_dataset(
    *,
    kind: str,
    entity: str | None,
    source: str,
    payload: dict[str, Any],
    coverage: float = 1.0,
    quality: float = 90.0,
) -> dict[str, Any]:
    ts = now_iso()
    return dataset_envelope(
        kind=kind,
        entity=entity,
        source=source,
        timestamp=ts,
        payload=payload,
        freshness_hours=0.0,
        coverage=coverage,
        quality=quality,
        provenance={"source": source, "collected_at": ts, "method": "collect"},
    )


def unavailable(source: str, entity: str | None, reason: str = "source_unavailable") -> dict[str, Any]:
    return {
        "ok": False,
        "source": source,
        "entity": entity,
        "reason": reason,
        "timestamp": now_iso(),
        "payload": {},
    }
