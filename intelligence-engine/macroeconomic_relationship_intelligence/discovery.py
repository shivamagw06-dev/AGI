"""Relationship discovery — catalog + soft HMIP confirmation (never Ask-triggered)."""

from __future__ import annotations

from typing import Any

from macroeconomic_relationship_intelligence.catalog import all_catalog_entries
from macroeconomic_relationship_intelligence.schema import (
    MacroRelationship,
    RelationshipEvidence,
    stable_relationship_id,
)
from macroeconomic_relationship_intelligence.store import STORE


def _from_catalog(entry: dict[str, Any]) -> MacroRelationship:
    evidence = [
        RelationshipEvidence(
            kind=e["kind"],
            summary=e["summary"],
            period=e.get("period"),
            source_refs=list(e.get("source_refs") or []),
            weight=float(e.get("weight") or 1.0),
        )
        for e in (entry.get("evidence") or [])
    ]
    rid = stable_relationship_id(entry["source"], entry["target"], entry["relationship"])
    return MacroRelationship(
        relationship_id=rid,
        source=entry["source"],
        source_label=entry.get("source_label") or entry["source"],
        target=entry["target"],
        target_label=entry.get("target_label") or entry["target"],
        relationship=entry["relationship"],
        kind=entry["kind"],
        direction=entry.get("direction") or "Positive",
        evidence_strength=entry.get("evidence_strength") or "Medium",
        confidence_pct=int(entry.get("confidence_pct") or 70),
        historical_observations=int(entry.get("historical_observations") or 1),
        average_lag=entry.get("average_lag"),
        first_observed=entry.get("first_observed"),
        last_confirmed=entry.get("last_confirmed"),
        chain=list(entry.get("chain") or []),
        evidence=evidence,
        supporting_layers=list(entry.get("supporting_layers") or []),
        provenance={
            "gateway": "MRI",
            "origin": "evidence_catalog",
            "direction_note": entry.get("direction_note"),
            "ask_triggered": False,
        },
    )


def discover_from_catalog() -> list[MacroRelationship]:
    return [_from_catalog(e) for e in all_catalog_entries()]


def enrich_with_hmip(rel: MacroRelationship) -> MacroRelationship:
    """Soft-confirm using published HMIP timelines — never collects."""
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator
    except Exception:
        return rel

    confirmed = False
    for name in (rel.source, rel.target):
        # Only macro-like names hit HMIP
        tip = hmip_indicator(name, country="India")
        if not tip.get("found"):
            tip = hmip_indicator(name, country="United States")
        if not tip.get("found"):
            tip = hmip_indicator(name, country="Global")
        if tip.get("found") and tip.get("timeline"):
            confirmed = True
            tl = tip["timeline"]
            rel.evidence.append(
                RelationshipEvidence(
                    kind="historical_macro",
                    summary=(
                        f"HMIP timeline for {name} available "
                        f"({tl.get('completeness_pct')}% complete, "
                        f"span {tl.get('years_span')})"
                    ),
                    period="-".join(str(y) for y in (tl.get("years_span") or [])),
                    source_refs=[f"hmip:{name}:timeline"],
                    weight=0.8,
                )
            )
            STORE.record_discovery(
                {
                    "relationship_id": rel.relationship_id,
                    "hmip_indicator": name,
                    "nodes": len(tl.get("nodes") or []),
                }
            )

    if confirmed and rel.last_confirmed:
        # Keep last_confirmed; bump confidence slightly if HMIP present
        rel.confidence_pct = min(97, int(rel.confidence_pct) + 1)
        rel.provenance = {
            **rel.provenance,
            "hmip_soft_confirmed": True,
            "providers_queried": [],
        }
    return rel
