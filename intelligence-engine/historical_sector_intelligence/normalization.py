"""Normalize validated observations into immutable HSKOs."""

from __future__ import annotations

from historical_sector_intelligence.schema import (
    HistoricalSectorKnowledgeObject,
    RawHistoricalSectorObservation,
    checksum_for,
    namespace_for,
)
from historical_sector_intelligence.store import STORE


def normalize_observation(
    raw: RawHistoricalSectorObservation,
    *,
    revision_note: str | None = None,
) -> HistoricalSectorKnowledgeObject:
    prior_versions = STORE.versions(raw.sector_key, raw.indicator, raw.period)
    version = len(prior_versions) + 1
    parent = prior_versions[-1].hsko_id if prior_versions else None
    ns = namespace_for(raw.category, raw.indicator)
    checksum = checksum_for(
        raw.sector_key,
        raw.indicator,
        raw.period,
        raw.value,
        raw.sector_leader,
        "|".join(raw.key_events or []),
        version if revision_note else 1,
    )
    # Soft HMIP macro tip in provenance when available
    provenance = {
        "raw_id": raw.observation_id,
        "mode": "seeded_historical_derived",
        "ask_triggered": False,
        "layers": [raw.source, "CSKP_universe"],
        "payload": dict(raw.payload or {}),
    }
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator

        year = raw.period.replace("FY", "")[:4]
        repo = hmip_indicator("Repo Rate", country="India")
        if repo.get("found"):
            provenance["hmip_repo_tip"] = {
                "n": repo.get("n"),
                "gateway": "HMIP_KRIG",
                "period_hint": year,
            }
    except Exception:
        pass

    return HistoricalSectorKnowledgeObject(
        sector_key=raw.sector_key,
        sector_label=raw.sector_label,
        category=raw.category,
        indicator=raw.indicator,
        value=raw.value,
        period=raw.period,
        previous=raw.previous,
        unit=raw.unit,
        source=raw.source,
        sector_leader=raw.sector_leader,
        government_policies=list(raw.government_policies or []),
        macro_regime=raw.macro_regime,
        key_events=list(raw.key_events or []),
        publication_date=raw.publication_date,
        effective_date=raw.effective_date or raw.period,
        version=version,
        parent_hsko_id=parent,
        historical_confidence=0.92 if raw.value is not None else 0.85,
        provenance=provenance,
        checksum=checksum,
        namespace=ns,
        revision_note=revision_note,
    )
