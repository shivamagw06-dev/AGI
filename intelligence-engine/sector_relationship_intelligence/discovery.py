"""Relationship discovery — catalog + soft HSIP/HMIP/MRI confirmation."""

from __future__ import annotations

from typing import Any

from sector_relationship_intelligence.catalog import all_catalog_entries
from sector_relationship_intelligence.schema import (
    RelationshipEvidence,
    SectorRelationship,
    stable_relationship_id,
)
from sector_relationship_intelligence.store import STORE


def _from_catalog(entry: dict[str, Any]) -> SectorRelationship:
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
    return SectorRelationship(
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
        contradictory_evidence=list(entry.get("contradictory_evidence") or []),
        provenance={
            "gateway": "SRI",
            "origin": "evidence_catalog",
            "direction_note": entry.get("direction_note"),
            "ask_triggered": False,
        },
    )


def discover_from_catalog() -> list[SectorRelationship]:
    return [_from_catalog(e) for e in all_catalog_entries()]


def _sector_key_guess(name: str) -> str | None:
    from continuous_sector_knowledge.schema import canonicalize

    return canonicalize(name)


def enrich_with_hsip(rel: SectorRelationship) -> SectorRelationship:
    """Soft-confirm using published HSIP timelines — never collects."""
    try:
        from historical_sector_intelligence.production import sector as hsip_sector
    except Exception:
        return rel

    confirmed = False
    for name in (rel.source, rel.target):
        key = _sector_key_guess(name)
        if not key:
            continue
        tip = hsip_sector(key, limit=20)
        if tip.get("found") and tip.get("timeline"):
            confirmed = True
            tl = tip["timeline"]
            rel.evidence.append(
                RelationshipEvidence(
                    kind="historical_sector",
                    summary=(
                        f"HSIP timeline soft-confirms {name}: "
                        f"completeness {tl.get('completeness_pct')}%, "
                        f"years {tl.get('years_span')}"
                    ),
                    period=str((tl.get("years_span") or [None])[-1]),
                    source_refs=[f"hsip:{key}:timeline"],
                    weight=0.85,
                )
            )
            STORE.record_discovery(
                {
                    "relationship_id": rel.relationship_id,
                    "source": rel.source,
                    "target": rel.target,
                    "enrichment": "hsip_timeline",
                }
            )
    if confirmed:
        rel.confidence_pct = min(97, int(rel.confidence_pct) + 1)
        rel.provenance = {
            **rel.provenance,
            "hsip_soft_confirmed": True,
            "providers_queried": [],
        }
        if "Historical Sector" not in rel.supporting_layers:
            rel.supporting_layers = list(rel.supporting_layers) + ["Historical Sector"]
    return rel


def enrich_with_hmip(rel: SectorRelationship) -> SectorRelationship:
    """Soft-confirm macro endpoints via HMIP — never collects."""
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator
    except Exception:
        return rel

    confirmed = False
    for name in (rel.source, rel.target):
        if _sector_key_guess(name):
            continue  # sector names skip HMIP
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
                        f"HMIP timeline soft-confirms {name}: "
                        f"completeness {tl.get('completeness_pct')}%"
                    ),
                    period=None,
                    source_refs=[f"hmip:{name}:timeline"],
                    weight=0.8,
                )
            )
    if confirmed:
        rel.provenance = {**rel.provenance, "hmip_soft_confirmed": True, "providers_queried": []}
        if "Historical Macro" not in rel.supporting_layers:
            rel.supporting_layers = list(rel.supporting_layers) + ["Historical Macro"]
    return rel


def enrich_with_mri_tip(rel: SectorRelationship) -> SectorRelationship:
    """Optional soft tip from MRI for overlapping macro→sector edges — never rebuilds MRI."""
    if rel.kind != "macro_to_sector":
        return rel
    try:
        from macroeconomic_relationship_intelligence.production import for_indicator

        pack = for_indicator(rel.source, limit=20)
    except Exception:
        return rel
    for row in pack.get("relationships") or []:
        tgt = str(row.get("target") or "").lower()
        if rel.target.lower() in tgt or tgt in rel.target.lower():
            rel.provenance = {
                **rel.provenance,
                "mri_soft_tip": {
                    "relationship_id": row.get("relationship_id"),
                    "confidence_pct": row.get("confidence_pct"),
                    "gateway": "MRI_KRIG",
                },
                "providers_queried": [],
            }
            if "MRI tip" not in rel.supporting_layers:
                rel.supporting_layers = list(rel.supporting_layers) + ["MRI tip"]
            break
    return rel
