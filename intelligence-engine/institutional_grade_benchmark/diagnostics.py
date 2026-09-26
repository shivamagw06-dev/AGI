"""IB-01 diagnostics."""

from __future__ import annotations

from typing import Any

from institutional_grade_benchmark.flags import flags_dict, is_enabled
from institutional_grade_benchmark.schema import (
    ADDS_INTELLIGENCE_ENGINES,
    ARCHITECTURE_FROZEN,
    COMPARATORS,
    GUIDING_PRINCIPLE,
    IB_COMPANIES,
    IB_SPEC,
    IB_VERSION,
    IB_WORKSTREAM_ID,
    PASS_THRESHOLD,
    SECTIONS,
    TOTAL_POINTS,
)


def build_diagnostics() -> dict[str, Any]:
    return {
        "workstream_id": IB_WORKSTREAM_ID,
        "version": IB_VERSION,
        "enabled": is_enabled(),
        "architecture_frozen": ARCHITECTURE_FROZEN,
        "adds_intelligence_engines": ADDS_INTELLIGENCE_ENGINES,
        "guiding_principle": GUIDING_PRINCIPLE,
        "total_points": TOTAL_POINTS,
        "pass_threshold": PASS_THRESHOLD,
        "companies": list(IB_COMPANIES),
        "comparators": list(COMPARATORS),
        "sections": [
            {"code": c, "key": k, "title": t, "max": m} for c, k, t, m in SECTIONS
        ],
        "flags": flags_dict(),
        "spec": IB_SPEC,
        "distinct_from": ["PAT-01", "IBS-01"],
    }
