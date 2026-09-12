"""Compile Institutional Macro Objects and Macro Evidence Packs."""

from __future__ import annotations

from typing import Any

from knowledge_factory.macro_intelligence import store as imi_store
from knowledge_factory.macro_intelligence.decision_matrix import decision_matrix_for_regimes
from knowledge_factory.macro_intelligence.dna.catalog import all_macro_dna, macro_dna
from knowledge_factory.macro_intelligence.fixtures.seed_macro import (
    current_snapshot,
    historical_macro_records,
    snapshot_as_of,
)
from knowledge_factory.macro_intelligence.playbooks.catalog import all_regime_playbooks, regime_playbook
from knowledge_factory.macro_intelligence.producers.impacts import relationship, sectors_for_driver
from knowledge_factory.macro_intelligence.producers.regime import classify_current, classify_snapshot
from knowledge_factory.macro_intelligence.schema import (
    IMI_SCHEMA_VERSION,
    IMI_VERSION,
    MACRO_UNIVERSE,
    macro_envelope,
)


def compile_macro_object(macro_id: str, *, as_of: str | None = None) -> dict[str, Any]:
    dna = macro_dna(macro_id)
    hist = historical_macro_records().get(macro_id) or []
    if as_of:
        hist = imi_store.filter_pit(hist, as_of)
    latest = hist[-1] if hist else None
    if hist:
        imi_store.put_history(macro_id, hist)
    obj = macro_envelope(
        macro_id,
        {
            "object_type": "institutional_macro_object",
            "dna": dna,
            "latest_observation": latest,
            "historical_depth_years": max(0, len(hist) - 1) if hist else 0,
            "history_points": len(hist),
            "available_from": (latest or {}).get("available_from"),
            "point_in_time": True,
            "knowledge_only": True,
            "reasoning_architecture": "frozen_v1",
            "insufficient": latest is None,
            "fabricated": False,
        },
    )
    imi_store.put_object(macro_id, obj)
    return obj


def compile_all_macro_objects(*, as_of: str | None = None) -> list[dict[str, Any]]:
    return [compile_macro_object(k, as_of=as_of) for k in MACRO_UNIVERSE]


def publish_macro_evidence_pack(*, as_of: str | None = None, name: str = "current") -> dict[str, Any]:
    snap = snapshot_as_of(as_of) if as_of else current_snapshot()
    classified = classify_snapshot(snap) if snap.get("n_series", 0) else {
        "found": False,
        "insufficient": True,
        "active_regimes": [],
        "primary_regime": None,
        "reason": "macro_history_unavailable",
        "fabricated": False,
    }
    regimes = list(classified.get("active_regimes") or [])
    matrix = classified.get("decision_matrix") or decision_matrix_for_regimes(regimes)
    objects = compile_all_macro_objects(as_of=as_of or snap.get("as_of"))

    # Persist core relationship edges as knowledge
    rel_edges = []
    for macro, sector in (
        ("interest_rates", "banks"),
        ("interest_rates", "real_estate"),
        ("interest_rates", "utilities"),
        ("interest_rates", "nbfc"),
        ("interest_rates", "insurance"),
        ("oil", "oil_gas"),
        ("oil", "logistics"),
        ("oil", "chemicals"),
        ("inflation", "fmcg"),
        ("inflation", "metals"),
        ("inflation", "consumer"),
        ("inflation", "it_services"),
        ("usd", "it_services"),
    ):
        rel_edges.append(relationship(macro, sector))

    pack = {
        "pack_type": "macro_evidence_pack",
        "schema_version": IMI_SCHEMA_VERSION,
        "imi_version": IMI_VERSION,
        "as_of": as_of or snap.get("as_of") or "current",
        "snapshot": {k: v for k, v in snap.items() if not str(k).endswith("_period")},
        "regime_classification": classified,
        "active_regimes": regimes,
        "primary_regime": classified.get("primary_regime"),
        "decision_matrix": matrix,
        "macro_objects": [
            {"macro_id": o.get("macro_id"), "latest": o.get("latest_observation"), "dna_completeness": (o.get("dna") or {}).get("dna_completeness")}
            for o in objects
        ],
        "dna_catalog_size": len(all_macro_dna()),
        "playbooks": {r: regime_playbook(r) for r in regimes},
        "all_playbooks": list(all_regime_playbooks().keys()),
        "relationships": rel_edges,
        "falling_rates_beneficiaries": sectors_for_driver("falling_rates"),
        "insufficient": bool(classified.get("insufficient")) or snap.get("n_series", 0) == 0,
        "knowledge_only": True,
        "reasoning_architecture": "frozen_v1",
        "phases_1_7_untouched": True,
        "fabricated": False,
    }
    imi_store.put_pack(name, pack)
    imi_store.put_regimes(
        {
            "as_of": pack["as_of"],
            "active_regimes": regimes,
            "primary_regime": classified.get("primary_regime"),
            "classification": classified,
            "preferred_frameworks": matrix.get("preferred_frameworks") or [],
            "deemphasise_frameworks": matrix.get("deemphasise_frameworks") or [],
            "affected_sectors": _affected_sectors(regimes),
            "historical_statistics": {"n_series": snap.get("n_series"), "confidence": _confidence(classified)},
            "start": pack["as_of"],
            "end": None,
        }
    )
    return pack


def _confidence(classified: dict[str, Any]) -> float:
    if classified.get("insufficient"):
        return 0.0
    n = len(classified.get("active_regimes") or [])
    return round(min(0.99, 0.55 + 0.05 * n), 4)


def _affected_sectors(regimes: list[str]) -> list[str]:
    out: list[str] = []
    for r in regimes:
        pb = regime_playbook(r)
        out.extend(list(pb.get("typical_winners") or []))
        out.extend(list(pb.get("typical_losers") or []))
    seen: set[str] = set()
    uniq = []
    for s in out:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq
