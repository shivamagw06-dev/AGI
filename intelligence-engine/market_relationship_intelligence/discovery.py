"""Relationship discovery — catalog + soft HMKIP/HMIP/HSIP/Macro-MRI confirmation."""

from __future__ import annotations

from typing import Any

from market_relationship_intelligence.catalog import all_catalog_entries
from market_relationship_intelligence.schema import (
    MarketRelationship,
    RelationshipEvidence,
    stable_relationship_id,
)
from market_relationship_intelligence.store import STORE


def _from_catalog(entry: dict[str, Any]) -> MarketRelationship:
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
    return MarketRelationship(
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
            "gateway": "MKRI",
            "origin": "evidence_catalog",
            "direction_note": entry.get("direction_note"),
            "ask_triggered": False,
            "providers_queried": [],
        },
    )


def discover_from_catalog() -> list[MarketRelationship]:
    return [_from_catalog(e) for e in all_catalog_entries()]


def enrich_with_hmkip(rel: MarketRelationship) -> MarketRelationship:
    """Soft-confirm using published HMKIP timelines — never collects."""
    try:
        from historical_market_intelligence.production import market as hmkip_market
        from historical_market_intelligence.production import history as hmkip_history
    except Exception:
        return rel

    confirmed = False
    for name in (rel.source, rel.target, *(rel.chain or [])):
        tip = None
        lower = name.lower()
        if any(x in lower for x in ("breadth", "liquidity", "volatility", "flow", "vix", "nifty", "equity", "bull", "bear", "recovery", "correction")):
            # Prefer india_equity / domain packs
            domain = "india_equity"
            if "breadth" in lower:
                domain = "breadth"
            elif "liquidity" in lower:
                domain = "liquidity"
            elif "volatil" in lower or "vix" in lower:
                domain = "volatility"
            elif "flow" in lower or "fii" in lower or "dii" in lower:
                domain = "institutional_flows"
            elif "cross" in lower or "usd" in lower or "gold" in lower or "oil" in lower or "bond" in lower:
                domain = "cross_asset"
            elif "leadership" in lower:
                domain = "leadership"
            tip = hmkip_market(domain, limit=10)
        if tip and tip.get("found") and tip.get("timeline"):
            confirmed = True
            tl = tip["timeline"]
            rel.evidence.append(
                RelationshipEvidence(
                    kind="historical_market",
                    summary=(
                        f"HMKIP timeline soft-confirms {name}: "
                        f"completeness {tl.get('completeness_pct')}%, "
                        f"years {tl.get('years_span')}"
                    ),
                    period=str((tl.get("years_span") or [None])[-1]),
                    source_refs=[f"hmkip:{domain}:timeline"],
                    weight=0.85,
                )
            )
            STORE.record_discovery(
                {
                    "relationship_id": rel.relationship_id,
                    "source": rel.source,
                    "target": rel.target,
                    "enrichment": "hmkip_timeline",
                }
            )
    if not confirmed:
        hist = hmkip_history(limit=1)
        if hist.get("n", 0) > 0:
            confirmed = True
            rel.provenance = {
                **rel.provenance,
                "hmkip_history_tip": {"n": hist.get("n"), "gateway": "HMKIP_KRIG"},
            }
    if confirmed:
        rel.confidence_pct = min(97, int(rel.confidence_pct) + 1)
        rel.provenance = {
            **rel.provenance,
            "hmkip_soft_confirmed": True,
            "providers_queried": [],
        }
        if "Historical Market" not in rel.supporting_layers:
            rel.supporting_layers = list(rel.supporting_layers) + ["Historical Market"]
    return rel


def enrich_with_hmip(rel: MarketRelationship) -> MarketRelationship:
    """Soft-confirm macro endpoints via HMIP — never collects."""
    try:
        from historical_macro_intelligence.production import indicator as hmip_indicator
    except Exception:
        return rel

    macro_names = {
        "repo rate",
        "cpi",
        "us treasury yield",
        "bond yields",
        "usdinr",
        "fiscal deficit",
    }
    confirmed = False
    for name in (rel.source, rel.target):
        if name.lower() not in macro_names and "yield" not in name.lower() and "repo" not in name.lower() and "cpi" not in name.lower():
            continue
        tip = hmip_indicator(name, country="India")
        if not tip.get("found"):
            tip = hmip_indicator(name, country="United States")
        if not tip.get("found"):
            tip = hmip_indicator(name, country="Global")
        if tip.get("found"):
            confirmed = True
            rel.evidence.append(
                RelationshipEvidence(
                    kind="historical_macro",
                    summary=f"HMIP soft-confirms {name} (n={tip.get('n')})",
                    period=None,
                    source_refs=[f"hmip:{name}"],
                    weight=0.8,
                )
            )
    if confirmed:
        rel.provenance = {**rel.provenance, "hmip_soft_confirmed": True, "providers_queried": []}
        if "Historical Macro" not in rel.supporting_layers:
            rel.supporting_layers = list(rel.supporting_layers) + ["Historical Macro"]
    return rel


def enrich_with_hsip(rel: MarketRelationship) -> MarketRelationship:
    """Soft-confirm sector endpoints via HSIP — never collects."""
    try:
        from historical_sector_intelligence.production import sector as hsip_sector
        from continuous_sector_knowledge.schema import canonicalize
    except Exception:
        return rel

    confirmed = False
    for name in (rel.source, rel.target, *(rel.chain or [])):
        key = canonicalize(name)
        if not key:
            # try common aliases
            aliases = {
                "banks": "banking",
                "banking leadership": "banking",
                "defensive sectors": "fmcg",
                "midcaps": "auto",
                "capital goods": "capital_goods",
            }
            key = aliases.get(name.lower())
        if not key:
            continue
        tip = hsip_sector(key, limit=10)
        if tip.get("found") and tip.get("timeline"):
            confirmed = True
            tl = tip["timeline"]
            rel.evidence.append(
                RelationshipEvidence(
                    kind="historical_sector",
                    summary=(
                        f"HSIP timeline soft-confirms {name}: "
                        f"completeness {tl.get('completeness_pct')}%"
                    ),
                    period=None,
                    source_refs=[f"hsip:{key}:timeline"],
                    weight=0.8,
                )
            )
    if confirmed:
        rel.provenance = {**rel.provenance, "hsip_soft_confirmed": True, "providers_queried": []}
        if "Historical Sector" not in rel.supporting_layers:
            rel.supporting_layers = list(rel.supporting_layers) + ["Historical Sector"]
    return rel


def enrich_with_macro_mri_tip(rel: MarketRelationship) -> MarketRelationship:
    """Optional soft tip from Macro MRI for overlapping macro edges — never rebuilds MRI."""
    if rel.kind not in {"macro_to_market", "cross_asset"}:
        return rel
    try:
        from macroeconomic_relationship_intelligence.production import for_indicator

        pack = for_indicator(rel.source, limit=20)
    except Exception:
        return rel
    for row in pack.get("relationships") or []:
        tgt = str(row.get("target") or "").lower()
        if rel.target.lower() in tgt or tgt in rel.target.lower() or "market" in tgt or "equity" in tgt:
            rel.provenance = {
                **rel.provenance,
                "macro_mri_soft_tip": {
                    "relationship_id": row.get("relationship_id"),
                    "confidence_pct": row.get("confidence_pct"),
                    "gateway": "MRI_KRIG",
                },
                "providers_queried": [],
            }
            if "Macro MRI tip" not in rel.supporting_layers:
                rel.supporting_layers = list(rel.supporting_layers) + ["Macro MRI tip"]
            break
    return rel
