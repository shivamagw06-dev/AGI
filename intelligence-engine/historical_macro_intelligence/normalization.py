"""Normalize validated observations into immutable HMKOs."""

from __future__ import annotations

from historical_macro_intelligence.schema import (
    HistoricalMacroKnowledgeObject,
    RawHistoricalObservation,
    checksum_for,
    namespace_for,
)
from historical_macro_intelligence.store import STORE


def normalize_observation(
    raw: RawHistoricalObservation,
    *,
    revision_note: str | None = None,
) -> HistoricalMacroKnowledgeObject:
    prior_versions = STORE.versions(raw.country, raw.indicator, raw.period)
    latest = prior_versions[-1] if prior_versions else None

    # Content checksum excludes version — identical re-ingest is a no-op (immutable)
    content_checksum = checksum_for(
        raw.country,
        raw.indicator,
        raw.period,
        raw.value,
        raw.source,
        raw.publication_date,
    )

    # Revision only when value/source content changes for same period
    if latest and latest.checksum == content_checksum:
        version = latest.version
        parent = latest.parent_hmko_id
        note = revision_note
    elif latest:
        version = latest.version + 1
        parent = latest.hmko_id
        note = revision_note or "official_revision_or_restatement"
    else:
        version = 1
        parent = None
        note = revision_note

    previous = raw.previous
    if previous is None:
        series = STORE.series(raw.indicator, country=raw.country)
        earlier = [s for s in series if s.period < raw.period]
        if earlier:
            previous = earlier[-1].value

    ns = namespace_for(raw.category, raw.indicator)

    return HistoricalMacroKnowledgeObject(
        country=raw.country,
        category=raw.category,
        indicator=raw.indicator,
        value=raw.value,
        period=raw.period,
        previous=previous,
        unit=raw.unit,
        source=raw.source,
        publication_date=raw.publication_date,
        effective_date=raw.effective_date or raw.period,
        version=version,
        parent_hmko_id=parent,
        confidence=0.93 if raw.source in {"rbi", "mospi", "nso", "fred", "mof", "cga"} else 0.88,
        provenance={
            "raw_observation_id": raw.observation_id,
            "collector": raw.source,
            "payload": dict(raw.payload or {}),
            "mode": "historical_background",
            "ask_triggered": False,
            "ingestion": "HMIP",
        },
        checksum=content_checksum,
        namespace=ns,
        revision_note=note,
        immutable=True,
    )
