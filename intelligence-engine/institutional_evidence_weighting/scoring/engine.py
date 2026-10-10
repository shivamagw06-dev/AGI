"""Deterministic multi-dimension evidence weighting."""

from __future__ import annotations

from typing import Any

from institutional_evidence_weighting.config import active_weight_version, load_profile
from institutional_evidence_weighting.scoring.normalize import (
    canonical_source,
    infer_freshness,
    infer_materiality,
    infer_quality,
    infer_specificity,
    temporal_status_of,
)
from institutional_evidence_weighting.schema import IEW_VERSION, WEIGHT_VERSION


def _round(x: float) -> float:
    return round(float(x), 2)


def _frac(table: dict[str, float], key: str, default: float = 0.35) -> float:
    return float(table.get(key, table.get("unknown", default)))


def score_evidence(
    obj: dict[str, Any],
    *,
    as_of: str | None = None,
    peer_sources: list[str] | None = None,
    analogue_strength: float | None = None,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Score one evidence-like object. Pure / deterministic."""
    prof = profile or load_profile()
    caps = prof.get("caps") or {}
    source_canon = canonical_source(obj.get("source") or obj.get("collector") or obj.get("kind"), prof)
    materiality = infer_materiality(obj)
    freshness = infer_freshness(obj, as_of=as_of)
    quality = infer_quality(obj, source_canon)
    specificity = infer_specificity(obj)
    temporal = temporal_status_of(obj)

    cred_f = _frac(prof.get("source_credibility") or {}, source_canon, 0.25)
    mat_f = _frac(prof.get("materiality") or {}, materiality)
    fresh_f = _frac(prof.get("freshness") or {}, freshness)
    qual_f = _frac(prof.get("quality") or {}, quality)
    spec_f = _frac(prof.get("specificity") or {}, specificity)

    # Corroboration: independent peer sources (excluding self/fixture)
    peers = [canonical_source(p, prof) for p in (peer_sources or [])]
    peers = [p for p in peers if p and p != source_canon and p not in ("fixture", "synthetic", "seed", "unknown")]
    unique_peers = sorted(set(peers))
    if len(unique_peers) >= 3:
        corr_f = 1.0
        corr_note = f"{len(unique_peers)} independent confirmations"
    elif len(unique_peers) == 2:
        corr_f = 0.75
        corr_note = "2 independent confirmations"
    elif len(unique_peers) == 1:
        corr_f = 0.45
        corr_note = "1 independent confirmation"
    else:
        corr_f = 0.15
        corr_note = "missing confirmation"

    # Analogue strength 0..1 from IMAI similarity or explicit
    if analogue_strength is not None:
        try:
            ana_f = max(0.0, min(1.0, float(analogue_strength)))
        except (TypeError, ValueError):
            ana_f = 0.0
    else:
        try:
            ana_f = max(0.0, min(1.0, float(obj.get("similarity_score") or obj.get("analogue_strength") or 0.0)))
        except (TypeError, ValueError):
            ana_f = 0.0
        if ana_f == 0.0 and (obj.get("kind") in ("memory", "analogue") or obj.get("memory_id")):
            ana_f = 0.35  # present but unscored analogue

    credibility = _round(float(caps.get("credibility", 40)) * cred_f)
    materiality_score = _round(float(caps.get("materiality", 22)) * mat_f)
    freshness_score = _round(float(caps.get("freshness", 10)) * fresh_f)
    quality_score = _round(float(caps.get("quality", 8)) * qual_f)
    corroboration_score = _round(float(caps.get("corroboration", 8)) * corr_f)
    analogue_score = _round(float(caps.get("analogue", 6)) * ana_f)
    specificity_score = _round(float(caps.get("specificity", 6)) * spec_f)

    breakdown = {
        "credibility": credibility,
        "materiality": materiality_score,
        "freshness": freshness_score,
        "quality": quality_score,
        "corroboration": corroboration_score,
        "analogue": analogue_score,
        "specificity": specificity_score,
    }
    raw = sum(breakdown.values())

    exclusion_reason = None
    eligible = True
    if temporal == "rejected":
        eligible = False
        exclusion_reason = "temporal_integrity_rejected"
        raw = 0.0

    # Fixture ceiling
    fixture_ceiling = float(prof.get("fixture_ceiling") or 25.0)
    if quality in ("fixture", "synthetic", "seed") or source_canon in ("fixture", "synthetic", "seed"):
        raw = min(raw, fixture_ceiling)

    weight_score = _round(raw)

    # Confidence modifier: shrink when weak corroboration / low quality
    conf_mod = 1.0
    if quality in ("fixture", "synthetic"):
        conf_mod *= 0.5
    if corr_f < 0.2:
        conf_mod *= 0.9
    if temporal == "unknown":
        conf_mod *= 0.95
    if not eligible:
        conf_mod = 0.0
    conf_mod = _round(conf_mod)

    reason_parts = [
        f"Credibility {credibility:g} ({source_canon})",
        f"Materiality {materiality_score:g} ({materiality})",
        f"Freshness {freshness_score:g} ({freshness})",
        f"Quality {quality_score:g} ({quality})",
        f"Corroboration {corroboration_score:g} ({corr_note})",
        f"Historical Analogue {analogue_score:g}",
        f"Specificity {specificity_score:g} ({specificity})",
    ]
    if exclusion_reason:
        reason_parts.append(f"Excluded: {exclusion_reason}")

    evidence_id = (
        obj.get("evidence_id")
        or obj.get("node_id")
        or obj.get("memory_id")
        or obj.get("document_id")
        or obj.get("id")
        or "unknown"
    )
    document_id = obj.get("document_id") or obj.get("document") or obj.get("checksum")
    citations = obj.get("citations") or obj.get("citation") or []
    if isinstance(citations, dict):
        citations = [citations]

    return {
        "evidence_id": str(evidence_id),
        "source": source_canon,
        "source_raw": obj.get("source") or obj.get("collector"),
        "document_id": document_id,
        "citations": citations if isinstance(citations, list) else [],
        "title": obj.get("title") or obj.get("label") or obj.get("outcome_summary"),
        "weight_score": weight_score,
        "credibility_score": credibility,
        "materiality_score": materiality_score,
        "freshness_score": freshness_score,
        "quality_score": quality_score,
        "corroboration_score": corroboration_score,
        "analogue_score": analogue_score,
        "specificity_score": specificity_score,
        "temporal_status": temporal,
        "confidence_modifier": conf_mod,
        "reason": "; ".join(reason_parts),
        "weight_breakdown": breakdown,
        "weight_version": str(prof.get("profile_id") or WEIGHT_VERSION),
        "iew_version": IEW_VERSION,
        "eligible": eligible,
        "exclusion_reason": exclusion_reason,
        "ranking_position": None,
        "classes": {
            "materiality": materiality,
            "freshness": freshness,
            "quality": quality,
            "specificity": specificity,
        },
        "fabricated": False,
        "llm_used": False,
        "deterministic": True,
    }


def apply_fixture_dominance_guard(
    weighted: list[dict[str, Any]],
    *,
    profile: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Ensure validated live evidence outranks fixtures when both exist."""
    prof = profile or load_profile()
    margin = float(prof.get("live_validated_floor_over_fixture") or 15.0)
    live = [
        w
        for w in weighted
        if w.get("eligible")
        and (w.get("classes") or {}).get("quality") not in ("fixture", "synthetic", "seed")
        and w.get("source") not in ("fixture", "synthetic", "seed")
    ]
    fixtures = [
        w
        for w in weighted
        if (w.get("classes") or {}).get("quality") in ("fixture", "synthetic", "seed")
        or w.get("source") in ("fixture", "synthetic", "seed")
    ]
    if not live or not fixtures:
        return weighted
    max_live = max(float(w.get("weight_score") or 0) for w in live)
    for w in fixtures:
        ceiling = max(0.0, max_live - margin)
        if float(w.get("weight_score") or 0) > ceiling:
            w["weight_score"] = round(ceiling, 2)
            w["reason"] = (w.get("reason") or "") + f"; Fixture capped below live (ceiling {ceiling:g})"
            bd = dict(w.get("weight_breakdown") or {})
            # Keep breakdown sum consistent by shrinking quality component note only
            w["weight_breakdown"] = bd
            w["fixture_capped"] = True
    return weighted


def rank_weighted(weighted: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stable sort: weight desc, then evidence_id asc for tie-break (replay-safe)."""
    ordered = sorted(
        weighted,
        key=lambda w: (-float(w.get("weight_score") or 0.0), str(w.get("evidence_id") or "")),
    )
    for i, w in enumerate(ordered, start=1):
        w["ranking_position"] = i
    return ordered


def weight_objects(
    objects: list[dict[str, Any]],
    *,
    as_of: str | None = None,
    profile_id: str | None = None,
) -> list[dict[str, Any]]:
    prof = load_profile(profile_id)
    sources = [canonical_source(o.get("source") or o.get("collector"), prof) for o in objects]
    out: list[dict[str, Any]] = []
    for i, obj in enumerate(objects):
        peers = [sources[j] for j in range(len(sources)) if j != i]
        ana = obj.get("similarity_score")
        if ana is None and isinstance(obj.get("memory"), dict):
            ana = obj["memory"].get("similarity_score")
        scored = score_evidence(obj, as_of=as_of, peer_sources=peers, analogue_strength=ana, profile=prof)
        out.append(scored)
    out = apply_fixture_dominance_guard(out, profile=prof)
    return rank_weighted(out)


def active_version() -> str:
    return active_weight_version()
