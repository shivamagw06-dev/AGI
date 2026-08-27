"""FIL confidence — tier mix, validation, coverage."""

from __future__ import annotations

from typing import Any


def score_filings(facts: list[dict[str, Any]], docs: list[dict[str, Any]]) -> dict[str, Any]:
    if not facts:
        return {
            "confidence": 15.0,
            "breakdown": {"tier_quality": 0, "validation": 0, "coverage": 0, "recency": 0},
            "explain": "No extracted facts",
        }
    tiers = [int(f.get("evidence_tier") or 5) for f in facts]
    tier_quality = max(0.0, 100.0 - (sum(tiers) / len(tiers) - 1) * 18.0)
    verified = sum(1 for f in facts if f.get("validation_status") == "verified")
    partial = sum(1 for f in facts if f.get("validation_status") == "partially_verified")
    validation = min(100.0, (verified * 1.0 + partial * 0.6) / len(facts) * 100.0)
    coverage = min(100.0, len({f.get("category") for f in facts}) * 14.0)
    # recency: presence of Q1FY27 / 2026 docs
    recent = any("2026" in str(d.get("as_of") or "") for d in docs)
    recency = 90.0 if recent else 50.0
    conf = round(tier_quality * 0.35 + validation * 0.30 + coverage * 0.20 + recency * 0.15, 1)
    return {
        "confidence": conf,
        "breakdown": {
            "tier_quality": round(tier_quality, 1),
            "validation": round(validation, 1),
            "coverage": round(coverage, 1),
            "recency": round(recency, 1),
        },
        "weights": {"tier_quality": 0.35, "validation": 0.30, "coverage": 0.20, "recency": 0.15},
        "explain": (
            f"Tier {tier_quality:.0f}×35% + Validation {validation:.0f}×30% + "
            f"Coverage {coverage:.0f}×20% + Recency {recency:.0f}×15% = {conf:.0f}"
        ),
    }
