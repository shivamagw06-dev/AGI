"""Normalize validated releases into Macro Knowledge Object drafts."""

from __future__ import annotations

from typing import Any

from continuous_macro_knowledge.schema import MacroKnowledgeObject, RawMacroRelease
from continuous_macro_knowledge.store import STORE


def normalize_release(raw: RawMacroRelease) -> MacroKnowledgeObject:
    prior = STORE.latest(raw.indicator, country=raw.country)
    version = (prior.version + 1) if prior else 1
    parent = prior.mko_id if prior else None

    # Prefer prior values when release omits previous
    previous = raw.previous_value
    if previous is None and prior and prior.current_value is not None:
        previous = prior.current_value

    surprise = None
    if raw.current_value is not None and raw.consensus is not None:
        surprise = round(raw.current_value - raw.consensus, 4)

    delta = None
    if raw.current_value is not None and previous is not None:
        delta = round(raw.current_value - previous, 4)

    normalized = {
        "indicator_key": raw.indicator.lower().replace(" ", "_"),
        "delta": delta,
        "surprise_vs_consensus": surprise,
        "unit": raw.unit,
        "payload": dict(raw.payload or {}),
        "region": "India" if raw.country == "India" else ("Global" if raw.country == "Global" else "International"),
    }

    confidence = 0.92 if raw.source in {"rbi", "mospi", "nso", "mof", "cga", "fred"} else 0.85
    if raw.current_value is None:
        confidence = 0.80  # document releases

    return MacroKnowledgeObject(
        country=raw.country,
        category=raw.category,
        indicator=raw.indicator,
        current_value=raw.current_value,
        previous_value=previous,
        consensus=raw.consensus,
        unit=raw.unit,
        release_date=raw.release_date,
        effective_date=raw.effective_date or raw.release_date,
        importance=raw.importance,
        source=raw.source,
        freshness_sec=0,
        confidence=confidence,
        version=version,
        parent_mko_id=parent,
        normalized=normalized,
        provenance={
            "raw_release_id": raw.release_id,
            "collector": raw.source,
            "mode": "continuous_background",
            "ask_triggered": False,
        },
    )
