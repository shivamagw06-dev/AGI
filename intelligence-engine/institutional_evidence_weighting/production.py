"""Production façade — Institutional Evidence Weighting Engine (IEW)."""

from __future__ import annotations

from typing import Any

from institutional_evidence_weighting import store as iew_store
from institutional_evidence_weighting.config import active_weight_version, list_profiles, load_profile
from institutional_evidence_weighting.contradictions import identify_conflicts
from institutional_evidence_weighting.dashboard.board import build_board
from institutional_evidence_weighting.extract import collect_candidates
from institutional_evidence_weighting.schema import (
    COMPANY,
    FREEZE_LOCKS,
    IEW_VERSION,
    MODULE_CODE,
    PROGRAMME,
    WEIGHT_VERSION,
)
from institutional_evidence_weighting.scoring.engine import score_evidence, weight_objects


def status() -> dict[str, Any]:
    return {
        "module": MODULE_CODE,
        "company": COMPANY,
        "version": IEW_VERSION,
        "weight_version": active_weight_version(),
        "programme": PROGRAMME,
        "status": "ready",
        "freeze_locks": dict(FREEZE_LOCKS),
        "institutional_guarantee": (
            "Evidence priority is deterministic, explainable, and LLM-free; "
            "reasoning consumes ordered weighted evidence without logic changes."
        ),
        "api_prefix": "/v1/evidence-weighting",
        "observability": "langsmith_mandatory",
        "fabricated": False,
        "llm_used": False,
    }


def configuration(profile_id: str | None = None) -> dict[str, Any]:
    prof = load_profile(profile_id)
    return {
        "active_weight_version": active_weight_version(),
        "profiles": list_profiles(),
        "profile": {
            "profile_id": prof.get("profile_id"),
            "version": prof.get("version"),
            "caps": prof.get("caps"),
            "fixture_ceiling": prof.get("fixture_ceiling"),
            "deterministic": True,
            "llm_used": False,
        },
        "history": list_profiles(),
    }


def score(payload: dict[str, Any]) -> dict[str, Any]:
    """Score a single evidence object (API)."""
    obj = dict(payload.get("evidence") or payload.get("object") or payload)
    as_of = payload.get("as_of")
    peers = payload.get("peer_sources") or []
    return score_evidence(obj, as_of=as_of, peer_sources=list(peers), profile=load_profile(payload.get("profile_id")))


def explain(payload: dict[str, Any]) -> dict[str, Any]:
    scored = score(payload)
    return {
        "evidence_id": scored.get("evidence_id"),
        "weight_score": scored.get("weight_score"),
        "weight_breakdown": scored.get("weight_breakdown"),
        "reason": scored.get("reason"),
        "weight_version": scored.get("weight_version"),
        "classes": scored.get("classes"),
        "exclusion_reason": scored.get("exclusion_reason"),
        "deterministic": True,
        "llm_used": False,
    }


def ranking(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    payload = payload or {}
    objects = list(payload.get("evidence") or payload.get("objects") or [])
    if not objects:
        # fall back to latest run
        runs = iew_store.latest_runs(limit=1)
        if runs:
            return {
                "weighted": runs[0].get("top_weighted") or [],
                "weight_version": runs[0].get("weight_version"),
                "source": "latest_run",
            }
        return {"weighted": [], "weight_version": WEIGHT_VERSION, "source": "empty"}
    weighted = weight_objects(objects, as_of=payload.get("as_of"), profile_id=payload.get("profile_id"))
    return {
        "weighted": weighted,
        "n": len(weighted),
        "weight_version": active_weight_version(),
        "source": "request",
        "deterministic": True,
    }


def dashboard() -> dict[str, Any]:
    return build_board()


def telemetry() -> dict[str, Any]:
    return iew_store.telemetry_snapshot()


def _reorder_surface_bullets(
    bullets: list[Any] | None,
    weighted: list[dict[str, Any]],
) -> list[Any]:
    """Best-effort: prefer bullets that mention higher-weighted evidence ids/titles."""
    if not bullets:
        return list(bullets or [])
    text_bullets = [str(b) for b in bullets]
    scored: list[tuple[float, int, str]] = []
    for idx, b in enumerate(text_bullets):
        bl = b.lower()
        best = 0.0
        for w in weighted:
            eid = str(w.get("evidence_id") or "").lower()
            title = str(w.get("title") or "").lower()
            hit = False
            if eid and eid in bl:
                hit = True
            elif title and len(title) > 8 and title[:40] in bl:
                hit = True
            if hit:
                best = max(best, float(w.get("weight_score") or 0))
        scored.append((-best, idx, b))
    scored.sort()
    return [b for _neg, _i, b in scored]


def apply_weighting(
    *,
    as_of: str | None = None,
    evidence_graph: dict[str, Any] | None = None,
    institutional_memory: dict[str, Any] | None = None,
    evidence: dict[str, Any] | None = None,
    question_id: str | None = None,
    intent: str | None = None,
    framework: str | None = None,
    playbook: str | None = None,
    replay_mode: bool | None = None,
    profile_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Soft-wire entrypoint: score/rank evidence; return pack + lightly ordered surfaces.
    Never mutates frozen module internals in-place beyond returned copies.
    """
    candidates = collect_candidates(
        evidence_graph=evidence_graph,
        institutional_memory=institutional_memory,
        evidence=evidence,
    )
    weighted = weight_objects(candidates, as_of=as_of, profile_id=profile_id)
    conflicts = identify_conflicts(weighted)
    eligible = [w for w in weighted if w.get("eligible") is not False]
    excluded = [w for w in weighted if w.get("eligible") is False]
    weak = [w for w in eligible if float(w.get("weight_score") or 0) < 35.0][:15]
    top = eligible[:15]
    source_counts: dict[str, int] = {}
    for w in weighted:
        src = str(w.get("source") or "unknown")
        source_counts[src] = source_counts.get(src, 0) + 1

    # Ordered reasoning input (ids + compact rows)
    reasoning_input = [
        {
            "evidence_id": w.get("evidence_id"),
            "source": w.get("source"),
            "weight_score": w.get("weight_score"),
            "confidence_modifier": w.get("confidence_modifier"),
            "reason": w.get("reason"),
            "ranking_position": w.get("ranking_position"),
            "temporal_status": w.get("temporal_status"),
            "title": w.get("title"),
        }
        for w in eligible
    ]

    eg_out = dict(evidence_graph or {})
    if eg_out:
        eg_out = {
            **eg_out,
            "surface_bullets": _reorder_surface_bullets(eg_out.get("surface_bullets"), weighted),
            "weighted_evidence_ids": [w.get("evidence_id") for w in eligible[:20]],
            "iew_applied": True,
            "iew_version": IEW_VERSION,
        }

    im_out = dict(institutional_memory or {})
    if im_out:
        im_out = {
            **im_out,
            "surface_bullets": _reorder_surface_bullets(im_out.get("surface_bullets"), weighted),
            "weighted_memory_ids": [
                w.get("evidence_id") for w in eligible if str(w.get("evidence_id") or "").startswith("MEM") or "memory" in str(w.get("source"))
            ][:10],
            "iew_applied": True,
            "iew_version": IEW_VERSION,
        }

    pack = {
        "iew_version": IEW_VERSION,
        "weight_version": active_weight_version() if not profile_id else str(load_profile(profile_id).get("profile_id")),
        "as_of": as_of,
        "question_id": question_id,
        "intent": intent,
        "framework": framework,
        "playbook": playbook,
        "replay_mode": bool(replay_mode) if replay_mode is not None else bool(as_of),
        "n_candidates": len(candidates),
        "n_weighted": len(weighted),
        "n_eligible": len(eligible),
        "n_excluded": len(excluded),
        "n_conflicts": len(conflicts),
        "weighted_evidence": weighted,
        "ordered_evidence": reasoning_input,
        "top_weighted": top,
        "weak_evidence": weak,
        "conflicts": conflicts,
        "contradictions_resolved": False,
        "guides_evidence_priority": True,
        "reasoning_changed": False,
        "framework_changed": False,
        "communication_changed": False,
        "temporal_integrity_changed": False,
        "llm_used": False,
        "fabricated": False,
        "deterministic": True,
        "metadata": dict(metadata or {}),
    }

    summary = {
        "question_id": question_id,
        "weight_version": pack["weight_version"],
        "n_weighted": len(weighted),
        "n_excluded": len(excluded),
        "n_conflicts": len(conflicts),
        "sum_weight": sum(float(w.get("weight_score") or 0) for w in eligible),
        "source_counts": source_counts,
        "top_weighted": [
            {
                "evidence_id": w.get("evidence_id"),
                "source": w.get("source"),
                "weight_score": w.get("weight_score"),
                "ranking_position": w.get("ranking_position"),
                "reason": w.get("reason"),
            }
            for w in top[:10]
        ],
        "weak_evidence": [
            {
                "evidence_id": w.get("evidence_id"),
                "source": w.get("source"),
                "weight_score": w.get("weight_score"),
            }
            for w in weak[:10]
        ],
        "conflicts": conflicts[:10],
        "average_weight": round(
            (sum(float(w.get("weight_score") or 0) for w in eligible) / len(eligible)) if eligible else 0.0,
            2,
        ),
    }
    iew_store.record_run(summary)

    return {
        "pack": pack,
        "evidence_graph": eg_out or evidence_graph,
        "institutional_memory": im_out or institutional_memory,
        "report": {
            "iew_version": IEW_VERSION,
            "weight_version": pack["weight_version"],
            "n_candidates": len(candidates),
            "n_eligible": len(eligible),
            "n_excluded": len(excluded),
            "n_conflicts": len(conflicts),
            "average_weight": summary["average_weight"],
            "top_evidence_id": (top[0].get("evidence_id") if top else None),
            "reasoning_changed": False,
            "llm_used": False,
        },
    }
