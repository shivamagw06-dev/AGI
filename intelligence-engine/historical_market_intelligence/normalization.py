"""Normalize validated observations into immutable HMKTOs."""

from __future__ import annotations

from historical_market_intelligence.schema import (
    HistoricalMarketKnowledgeObject,
    RawHistoricalMarketObservation,
    checksum_for,
    namespace_for,
)
from historical_market_intelligence.store import STORE


def normalize_observation(
    raw: RawHistoricalMarketObservation,
    *,
    revision_note: str | None = None,
) -> HistoricalMarketKnowledgeObject:
    prior_versions = STORE.versions(raw.market_key, raw.indicator, raw.period)
    version = len(prior_versions) + 1
    parent = prior_versions[-1].hmkto_id if prior_versions else None
    ns = namespace_for(raw.category)
    checksum = checksum_for(
        raw.market_key,
        raw.indicator,
        raw.period,
        raw.value,
        raw.market_regime,
        "|".join(raw.major_events or []),
        version if revision_note else 1,
        revision_note or "",
    )
    provenance: dict = {
        "raw_id": raw.observation_id,
        "mode": "seeded_historical_derived",
        "ask_triggered": False,
        "layers": [raw.source, "CMKTP_universe"],
        "payload": dict(raw.payload or {}),
        "providers_queried": [],
    }
    # Soft CMKTP tip
    try:
        from continuous_market_knowledge.production import market as cmktp_market

        pack = cmktp_market()
        if pack.get("found"):
            provenance["cmktp_tip"] = {
                "gateway": "CMKTP_KRIG",
                "regime": (pack.get("market") or {}).get("market_regime"),
            }
    except Exception:
        pass
    # Soft HSIP tip
    try:
        from historical_sector_intelligence.production import history as hsip_history

        tip = hsip_history(limit=1)
        if tip.get("n", 0) > 0:
            provenance["hsip_tip"] = {"n": tip.get("n"), "gateway": "HSIP_KRIG"}
    except Exception:
        pass
    # Soft Macro HMIP tip
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator

        repo = hmip_indicator("Repo Rate", country="India")
        if repo.get("found"):
            provenance["hmip_repo_tip"] = {
                "n": repo.get("n"),
                "gateway": "HMIP_KRIG",
            }
    except Exception:
        pass

    return HistoricalMarketKnowledgeObject(
        market_key=raw.market_key,
        market_label=raw.market_label,
        category=raw.category,
        indicator=raw.indicator,
        value=raw.value,
        period=raw.period,
        previous=raw.previous,
        unit=raw.unit,
        source=raw.source,
        market_regime=raw.market_regime,
        breadth_state=raw.breadth_state,
        liquidity_state=raw.liquidity_state,
        volatility_state=raw.volatility_state,
        institutional_flows=raw.institutional_flows,
        leadership=raw.leadership,
        cross_asset_state=raw.cross_asset_state,
        major_events=list(raw.major_events or []),
        publication_date=raw.publication_date,
        effective_date=raw.effective_date or raw.period,
        version=version,
        parent_hmkto_id=parent,
        historical_confidence=0.92 if raw.value is not None else 0.85,
        provenance=provenance,
        checksum=checksum,
        namespace=ns,
        revision_note=revision_note,
    )
