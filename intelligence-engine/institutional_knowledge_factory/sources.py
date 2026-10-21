"""Source normalization — every source receives trust, coverage, freshness."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from institutional_knowledge_factory.schema import SOURCE_TRUST_BASELINE, SOURCE_TYPES


def _now_iso() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def normalize_source(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalize a raw evidence source into factory-standard format."""
    source_type = str(raw.get("source_type") or raw.get("type") or "corporate_filing")
    if source_type not in SOURCE_TYPES:
        source_type = "corporate_filing"

    trust = raw.get("trust_score")
    if trust is None:
        trust = SOURCE_TRUST_BASELINE.get(source_type, 70)

    freshness = raw.get("freshness")
    if freshness is None:
        freshness = 80

    coverage = raw.get("coverage") or []
    if isinstance(coverage, str):
        coverage = [coverage]

    return {
        "source_id": str(raw.get("source_id") or raw.get("id") or f"src_{source_type}"),
        "source_type": source_type,
        "entity_id": str(raw.get("entity_id") or raw.get("ticker") or "").upper(),
        "timestamp": raw.get("timestamp") or _now_iso(),
        "trust_score": int(trust),
        "freshness": int(freshness),
        "coverage": list(coverage),
        "extracts": list(raw.get("extracts") or raw.get("claims") or []),
        "metrics": dict(raw.get("metrics") or {}),
        "raw_ref": raw.get("raw_ref") or raw.get("url"),
        "normalized": True,
    }


def normalize_sources(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [normalize_source(item) for item in items if isinstance(item, dict)]
