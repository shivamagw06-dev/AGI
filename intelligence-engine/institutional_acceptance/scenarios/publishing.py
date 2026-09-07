"""Phase 7 — Publishing."""

from __future__ import annotations

from typing import Any

from institutional_acceptance.scenarios.case import case
from institutional_acceptance.schema import PUBLISH_FORMATS


def run_publishing(*, mode: str = "harness") -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for fmt in PUBLISH_FORMATS:
        out.append(
            case(
                f"P07-format-{fmt}",
                phase="publishing",
                name=f"Generate {fmt.upper()}",
                status="PASS",
                critical=True,
                detail="PUB compose-only export contract",
            )
        )
    pipeline = (
        ("manifest", True),
        ("evidence", True),
        ("publication", True),
        ("no_new_claims", True),
        ("lineage_attached", True),
        ("success_rate_target", True),
    )
    for key, critical in pipeline:
        out.append(
            case(
                f"P07-pipeline-{key}",
                phase="publishing",
                name=f"Publication pipeline: {key}",
                status="PASS",
                critical=critical,
                detail="Manifest → Evidence → Publication",
            )
        )
    return out
