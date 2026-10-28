"""Multi-stage confidence — extraction / normalization / structural / overall."""

from __future__ import annotations

from typing import Any


def compute_confidence(
    *,
    extraction: float,
    normalization: float,
    structural: float,
    failure_stage: str | None = None,
) -> dict[str, Any]:
    e = max(0.0, min(1.0, float(extraction)))
    n = max(0.0, min(1.0, float(normalization)))
    s = max(0.0, min(1.0, float(structural)))
    overall = 0.4 * e + 0.4 * n + 0.2 * s
    stage = failure_stage
    if stage is None:
        if e < 0.5:
            stage = "extraction"
        elif n < 0.5:
            stage = "normalization"
        elif s < 0.5:
            stage = "structural"
    return {
        "extraction": round(e, 4),
        "normalization": round(n, 4),
        "structural": round(s, 4),
        "overall": round(overall, 4),
        "failure_stage": stage,
        "formula": "0.4*extraction + 0.4*normalization + 0.2*structural",
    }


def structural_confidence(sections: list[str] | None, hierarchy_ok: bool) -> float:
    secs = [s for s in (sections or []) if s and s != "unknown"]
    if not secs:
        return 0.2
    base = min(1.0, 0.4 + 0.2 * len(secs))
    return base if hierarchy_ok else base * 0.5
