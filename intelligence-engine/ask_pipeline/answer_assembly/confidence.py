"""Stage 5 — Confidence calibration from coverage + gaps (deterministic)."""

from __future__ import annotations

from typing import Any

from ask_pipeline.answer_assembly.schema import CONFIDENCE_BANDS


def calibrate_confidence(
    *,
    classified: dict[str, Any],
    gaps: dict[str, Any],
    ordered: dict[str, Any],
) -> dict[str, Any]:
    n = int(classified.get("item_count") or 0)
    coverage = float(gaps.get("coverage") or 0.0)
    penalty = float(gaps.get("confidence_penalty") or 0.0)
    top_scores = [float(i.get("rank_score") or 0) for i in (ordered.get("ordered") or [])[:5]]
    avg_rank = sum(top_scores) / len(top_scores) if top_scores else 0.0

    # Base from coverage and retrieval depth
    score = 0.35 * coverage + 0.35 * min(1.0, n / 8.0) + 0.30 * min(1.0, avg_rank)
    score = max(0.0, min(1.0, score - penalty))

    band = "Insufficient"
    for threshold, label in CONFIDENCE_BANDS:
        if score >= threshold:
            band = label
            break

    return {
        "stage": "confidence_calibration",
        "score": round(score, 4),
        "band": band,
        "coverage": coverage,
        "item_count": n,
        "penalty": penalty,
        "avg_top_rank_score": round(avg_rank, 4),
        "missing_domains": gaps.get("missing_domains") or [],
        "fabricated": False,
    }
