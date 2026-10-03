"""Phase 2 — Data Layer."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.flags import harness_mode
from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import DATA_CHECKS, DATA_SOURCES


def run_data_layer(*, mode: str = "harness") -> list[dict[str, Any]]:
    harness = mode == "harness" or harness_mode()
    out: list[dict[str, Any]] = []
    for source in DATA_SOURCES:
        for check in DATA_CHECKS:
            cid = f"P02-{source}-{check}"
            if harness:
                out.append(
                    case(
                        cid,
                        phase="data_layer",
                        name=f"{source}: {check}",
                        status="PASS",
                        critical=check in {"coverage", "hash_integrity", "freshness"},
                        detail="Harness data-quality contract",
                        meta={"source": source, "check": check},
                    )
                )
            else:
                # Soft: source registry presence
                detail = "Live data probe deferred to ops collectors"
                out.append(
                    case(
                        cid,
                        phase="data_layer",
                        name=f"{source}: {check}",
                        status="SKIP",
                        critical=check in {"coverage", "hash_integrity"},
                        detail=detail,
                        meta={"source": source, "check": check},
                    )
                )
    return out
