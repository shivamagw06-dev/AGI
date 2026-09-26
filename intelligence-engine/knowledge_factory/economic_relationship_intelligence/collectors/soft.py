"""Soft collectors — read prior knowledge layers; never invent relationships."""

from __future__ import annotations

from typing import Any

from knowledge_factory.economic_relationship_intelligence.relationship_objects.builder import (
    build_relationship,
)
from knowledge_factory.economic_relationship_intelligence.schema import UNKNOWN


def collect_soft_priors() -> dict[str, Any]:
    """Aggregate soft priors from IIVI / IGRI / peers. Missing → empty, not fabricated."""
    return {
        "iivi_industry_links": _from_iivi(),
        "igri_policy_links": _from_igri(),
        "peer_competitors": _from_peers(),
        "fabricated": False,
    }


def soft_relationships_from_priors() -> list[dict[str, Any]]:
    """Materialise only evidence-backed edges from soft priors."""
    out: list[dict[str, Any]] = []
    pack = collect_soft_priors()

    for row in pack["iivi_industry_links"]:
        try:
            out.append(
                build_relationship(
                    source_kind="industry",
                    source_id=row["source"],
                    target_kind="industry",
                    target_id=row["target"],
                    relationship_type=row["relationship_type"],
                    direction="outbound",
                    strength=row.get("strength") or "moderate",
                    confidence=float(row.get("confidence") or 0.75),
                    evidence=row.get("evidence") or "iivi_value_chain",
                    source="industry_associations",
                    collector="ieri.collectors.iivi",
                    available_from=row.get("available_from") or "2016-01-01",
                    semantics=row.get("semantics"),
                    derived_from=["iivi"],
                )
            )
        except Exception:
            continue

    for row in pack["igri_policy_links"]:
        try:
            out.append(
                build_relationship(
                    source_kind="policy",
                    source_id=row["policy_id"],
                    target_kind=row["target_kind"],
                    target_id=row["target_id"],
                    relationship_type="policy_dependency",
                    direction="affects",
                    strength=row.get("strength") or "moderate",
                    confidence=float(row.get("confidence") or 0.8),
                    evidence=row.get("evidence") or "igri_policy",
                    source="government_publications",
                    collector="ieri.collectors.igri",
                    available_from=row.get("available_from") or "2016-01-01",
                    semantics="policy",
                    derived_from=["igri", row["policy_id"]],
                    transmission_order=row.get("transmission_order"),
                )
            )
        except Exception:
            continue

    for row in pack["peer_competitors"]:
        try:
            out.append(
                build_relationship(
                    source_kind="company",
                    source_id=row["a"],
                    target_kind="company",
                    target_id=row["b"],
                    relationship_type="competitor",
                    direction="bidirectional",
                    strength="moderate",
                    confidence=float(row.get("confidence") or 0.8),
                    evidence="ticker_peers_soft",
                    source="investor_presentations",
                    collector="ieri.collectors.peers",
                    available_from="2018-01-01",
                    semantics="structural",
                    derived_from=["company_analysis.TICKER_PEERS"],
                )
            )
        except Exception:
            continue

    return out


def _from_iivi() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        from knowledge_factory.industry_intelligence.playbooks.catalog import (
            DEEP_INDUSTRIES,
            get_playbook,
        )
    except Exception:
        return rows

    for iid in DEEP_INDUSTRIES or ():
        pb = get_playbook(iid) or {}
        if not isinstance(pb, dict):
            continue
        vc = pb.get("value_chain") or []
        for stage in vc:
            if not isinstance(stage, dict):
                continue
            st = str(stage.get("stage") or "")
            if st in ("raw_materials", "upstream"):
                for p in stage.get("participants") or []:
                    pid = str(p).lower().replace(" ", "_").replace("/", "_")
                    if pid and pid != UNKNOWN.lower() and len(pid) < 40:
                        rows.append(
                            {
                                "source": pid,
                                "target": iid,
                                "relationship_type": "upstream_industry",
                                "confidence": 0.7,
                                "evidence": f"iivi_value_chain_{iid}",
                                "semantics": "structural",
                            }
                        )
            if st in ("customer", "downstream"):
                for p in stage.get("participants") or []:
                    pid = str(p).lower().replace(" ", "_").replace("/", "_")
                    if pid and pid != UNKNOWN.lower() and len(pid) < 40:
                        rows.append(
                            {
                                "source": iid,
                                "target": pid,
                                "relationship_type": "downstream_industry",
                                "confidence": 0.7,
                                "evidence": f"iivi_value_chain_{iid}",
                                "semantics": "structural",
                            }
                        )
    return rows


def _from_igri() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        from knowledge_factory.government_intelligence import store as igri_store
        from knowledge_factory.government_intelligence.pipeline import (
            run_government_intelligence_pipeline,
        )

        if igri_store.policy_count() == 0:
            run_government_intelligence_pipeline()
        policies = igri_store.list_policies()
    except Exception:
        return rows

    for p in policies:
        pid = p.get("policy_id")
        if not pid:
            continue
        available = p.get("announcement_date") or p.get("effective_date") or "2016-01-01"
        for ind in p.get("affected_industries") or []:
            rows.append(
                {
                    "policy_id": pid,
                    "target_kind": "industry",
                    "target_id": str(ind).lower().replace(" ", "_"),
                    "available_from": available,
                    "confidence": float((p.get("transmission") or {}).get("confidence") or 0.8),
                    "evidence": p.get("evidence") or pid,
                    "transmission_order": 1,
                    "strength": "high" if p.get("impact_level") == "Critical" else "moderate",
                }
            )
        for sec in p.get("affected_sectors") or []:
            if sec == "all":
                continue
            rows.append(
                {
                    "policy_id": pid,
                    "target_kind": "sector",
                    "target_id": str(sec).lower().replace(" ", "_"),
                    "available_from": available,
                    "confidence": 0.8,
                    "evidence": p.get("evidence") or pid,
                    "transmission_order": 1,
                }
            )
        for co in p.get("affected_companies") or []:
            rows.append(
                {
                    "policy_id": pid,
                    "target_kind": "company",
                    "target_id": str(co).upper(),
                    "available_from": available,
                    "confidence": 0.85,
                    "evidence": p.get("evidence") or pid,
                    "transmission_order": 1,
                    "strength": "high",
                }
            )
    return rows


def _from_peers() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        from company_analysis.schema import TICKER_PEERS
    except Exception:
        return rows
    seen: set[tuple[str, str]] = set()
    for ticker, peers in (TICKER_PEERS or {}).items():
        a = str(ticker).upper()
        for p in peers or []:
            b = str(p).upper()
            key = tuple(sorted((a, b)))
            if key in seen or a == b:
                continue
            seen.add(key)
            rows.append({"a": key[0], "b": key[1], "confidence": 0.85})
    return rows
