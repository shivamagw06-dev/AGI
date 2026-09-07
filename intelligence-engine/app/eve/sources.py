"""Source registry + configurable reliability."""

from __future__ import annotations

from app.eve.config import DEFAULT_SOURCES, SOURCE_RELIABILITY
from app.eve.models import SourceRecord
from app.eve.store import EveStore


def reliability_for(category: str, *, overrides: dict[str, float] | None = None) -> float:
    table = {**(SOURCE_RELIABILITY), **(overrides or {})}
    key = (category or "unknown").lower().strip()
    if key in table:
        return float(table[key])
    for k, v in table.items():
        if k in key or key in k:
            return float(v)
    return float(table.get("unknown", 0.30))


def seed_sources(store: EveStore, *, reliability_overrides: dict[str, float] | None = None) -> int:
    n = 0
    for row in DEFAULT_SOURCES:
        cat = str(row.get("category") or "unknown")
        score = reliability_for(cat, overrides=reliability_overrides)
        store.add_source(
            SourceRecord(
                source_id=str(row["source_id"]),
                name=str(row["name"]),
                category=cat,
                organisation=str(row.get("organisation") or ""),
                country=str(row.get("country") or ""),
                website=str(row.get("website") or ""),
                authority_level=str(row.get("authority_level") or "standard"),
                reliability_score=score,
                update_frequency=str(row.get("update_frequency") or "unknown"),
                license_notes=str(row.get("license_notes") or ""),
            )
        )
        n += 1
    return n


def resolve_source_id(store: EveStore, *, connector_id: str = "", doc_type: str = "") -> str:
    """Map AOI connector/doc_type onto a registry source."""
    candidates = [
        (doc_type or "").lower(),
        (connector_id or "").lower(),
    ]
    for cat in candidates:
        if not cat:
            continue
        for src in store.sources.values():
            if src.category == cat or src.category in cat or cat in src.category:
                return src.source_id
        # synthetic source if known reliability category
        if cat in SOURCE_RELIABILITY:
            sid = f"src_{cat}"
            if sid not in store.sources:
                store.add_source(
                    SourceRecord(
                        source_id=sid,
                        name=cat.replace("_", " ").title(),
                        category=cat,
                        reliability_score=reliability_for(cat),
                    )
                )
            return sid
    return "src_unknown"


def touch_sync(store: EveStore, source_id: str, *, when: str) -> None:
    src = store.sources.get(source_id)
    if not src:
        return
    store.sources[source_id] = src.model_copy(update={"last_successful_sync": when})
