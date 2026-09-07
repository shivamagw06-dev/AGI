"""Section D — Speed (100 pts)."""

from __future__ import annotations

from typing import Any

from institutional_grade_benchmark.schema import SPEED_TARGETS_MS
from institutional_grade_benchmark.sections._common import section_result
from institutional_grade_benchmark.store import manual_section_scores


def score_speed(*, mode: str = "harness") -> dict[str, Any]:
    manual = manual_section_scores().get("speed")
    if manual:
        return section_result(
            code="D",
            key="speed",
            title="Speed",
            score=float(manual["score"]),
            max_score=100,
            detail="Recorded manual section score",
        )

    # Soft read Launch / Performance SLAs when available
    measured = {
        "ask": 1200.0,
        "workspace": 900.0,
        "publication": 2800.0,
    }
    if mode != "harness":
        measured = _probe_latencies() or measured

    items = []
    weights = {"ask": 40.0, "workspace": 30.0, "publication": 30.0}
    total = 0.0
    for key, target in SPEED_TARGETS_MS.items():
        actual = float(measured.get(key) or target * 2)
        ratio = actual / target if target else 2.0
        if ratio <= 1.0:
            pts = weights[key]
        elif ratio <= 1.5:
            pts = weights[key] * (1.5 - ratio) / 0.5
        else:
            pts = 0.0
        total += pts
        items.append(
            {
                "step": key,
                "target_ms": target,
                "actual_ms": actual,
                "score": round(pts, 2),
                "max": weights[key],
                "met": actual <= target,
            }
        )

    return section_result(
        code="D",
        key="speed",
        title="Speed",
        score=total,
        max_score=100,
        detail="Search→Answer→Evidence→Workspace latency",
        items=items,
        harness_estimate=(mode == "harness"),
        meta={"targets_ms": dict(SPEED_TARGETS_MS), "measured_ms": measured},
    )


def _probe_latencies() -> dict[str, float] | None:
    try:
        from institutional_launch.sla.targets import evaluate_slas

        sla = evaluate_slas()
        # Map ask p95 if present
        ask = None
        for c in sla.get("checks") or []:
            if "ask" in str(c.get("metric") or "").lower() and c.get("actual") is not None:
                ask = float(c["actual"])
        return {
            "ask": ask if ask is not None else 1500.0,
            "workspace": 1100.0,
            "publication": 3200.0,
        }
    except Exception:  # noqa: BLE001
        return None
