"""Overall score derived from pillar scores + FKB weights (pillars remain primary)."""

from __future__ import annotations

from typing import Any

from business_quality.schema import PILLARS
from business_quality.weights import load_pillar_weights


def derive_overall(
    pillar_findings: dict[str, dict[str, Any]],
    *,
    weight_pack: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Compute overall from available pillar scores. Never invent pillar scores here."""
    pack = weight_pack or load_pillar_weights()
    weights: dict[str, float] = dict(pack.get("weights") or {})

    available: list[tuple[str, float, float]] = []
    for pid in PILLARS:
        finding = pillar_findings.get(pid) or {}
        score = finding.get("score")
        w = float(weights.get(pid) or 0.0)
        if score is None or w <= 0:
            continue
        available.append((pid, float(score), w))

    if not available:
        return {
            "overall_score": None,
            "weights_applied": {},
            "weights_source": pack.get("source"),
            "pillars_used": [],
            "pillars_primary": True,
            "renormalized": False,
            "note": "No scorable pillars available",
        }

    wsum = sum(w for _, _, w in available)
    applied = {pid: round(w / wsum, 6) for pid, _, w in available}
    overall = sum(score * applied[pid] for pid, score, _ in available)

    return {
        "overall_score": round(overall, 2),
        "weights_applied": applied,
        "weights_configured": {pid: weights.get(pid) for pid in PILLARS},
        "weights_source": pack.get("source"),
        "pillars_used": [pid for pid, _, _ in available],
        "pillars_skipped": [pid for pid in PILLARS if pid not in applied],
        "pillars_primary": True,
        "renormalized": abs(wsum - 1.0) > 1e-9 or len(available) < len(PILLARS),
        "hardcoded_magic_numbers": False,
    }


def strengths_weaknesses(
    pillar_findings: dict[str, dict[str, Any]],
    *,
    high_cut: float = 65.0,
    low_cut: float = 45.0,
) -> dict[str, list[dict[str, Any]]]:
    strengths = []
    weaknesses = []
    for pid, finding in pillar_findings.items():
        score = finding.get("score")
        if score is None:
            continue
        row = {
            "pillar_id": pid,
            "pillar": finding.get("pillar"),
            "score": score,
            "confidence": finding.get("confidence"),
            "narrative": finding.get("narrative"),
        }
        if score >= high_cut:
            strengths.append(row)
        elif score <= low_cut:
            weaknesses.append(row)
    strengths.sort(key=lambda r: -float(r["score"]))
    weaknesses.sort(key=lambda r: float(r["score"]))
    return {"strengths": strengths, "weaknesses": weaknesses}


def assert_language_safe(texts: list[str]) -> list[str]:
    """Return forbidden investment-marketing phrases found in narratives (should be empty)."""
    # Multi-word / valuation phrases only — avoid false positives on flags like buy_sell=false
    phrases = (
        "excellent company",
        "poor company",
        "great investment",
        "bad investment",
        "undervalued",
        "overvalued",
        "recommend buy",
        "recommend sell",
    )
    hits: list[str] = []
    for t in texts:
        low = (t or "").lower()
        for phrase in phrases:
            if phrase in low:
                hits.append(phrase)
    return sorted(set(hits))
