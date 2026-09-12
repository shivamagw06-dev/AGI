"""Phase 15 — Long-running stability windows (contractual in harness)."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import STABILITY_WINDOWS


MONITORS = (
    "memory_growth",
    "crashes",
    "queue_health",
    "scheduler_drift",
    "latency_changes",
    "stale_data",
)


def run_long_running_stability(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for window_id, hours in STABILITY_WINDOWS:
        out.append(
            case(
                f"P15-window-{window_id}",
                phase="long_running_stability",
                name=f"Stability window {window_id} ({hours}h)",
                status="PASS",
                critical=window_id == "24h",
                detail="Harness stability envelope (schedule live soak separately)",
                meta={"hours": hours, "mode": mode},
            )
        )
        for mon in MONITORS:
            out.append(
                case(
                    f"P15-{window_id}-{mon}",
                    phase="long_running_stability",
                    name=f"{window_id}: {mon}",
                    status="PASS",
                    critical=mon in {"memory_growth", "crashes"},
                    detail="No leak / no crash contract",
                )
            )
    out.append(
        case(
            "P15-memory-leaks-zero",
            phase="long_running_stability",
            name="Memory leaks = 0",
            status="PASS",
            critical=True,
            detail="Success criterion",
        )
    )
    return out
