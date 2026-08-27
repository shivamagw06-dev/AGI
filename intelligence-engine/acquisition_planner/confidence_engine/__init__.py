"""Confidence engine — expected confidence from planned acquisition."""

from __future__ import annotations

from typing import Any


def estimate_confidence(
    *,
    quality: dict[str, Any],
    reuse_count: int,
    acquire_count: int,
    duplicate_count: int,
    authority_compliant: bool,
) -> dict[str, Any]:
    base = float(quality.get("expected_quality") or 0.5)
    reuse_boost = min(0.08, reuse_count * 0.015)
    acquire_boost = min(0.1, acquire_count * 0.012)
    dup_pen = min(0.2, duplicate_count * 0.05)
    auth_pen = 0.0 if authority_compliant else 0.15
    confidence = max(0.0, min(0.99, base + reuse_boost + acquire_boost - dup_pen - auth_pen))
    return {
        "confidence": round(confidence, 4),
        "components": {
            "quality_base": round(base, 4),
            "reuse_boost": round(reuse_boost, 4),
            "acquire_boost": round(acquire_boost, 4),
            "duplicate_penalty": round(dup_pen, 4),
            "authority_penalty": round(auth_pen, 4),
        },
    }
