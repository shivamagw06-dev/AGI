"""ICF-01 — Institutional Coverage Factory.

Continuously drives companies toward Institutional Coverage Complete (ICC).
Throughput is measured as companies entering ICC per day — not shallow crawl count.
"""

from __future__ import annotations

from institutional_coverage_factory.flags import is_icf_enabled
from institutional_coverage_factory.production import (
    coverage_dashboard,
    coverage_score_for,
    get_icf_status,
    health,
    icc_status_for,
    plan_and_dispatch,
    run_coverage_tick,
    soft_slice_mission_control,
)
from institutional_coverage_factory.schema import ICF_VERSION, ICF_WORKSTREAM_ID

__all__ = [
    "ICF_VERSION",
    "ICF_WORKSTREAM_ID",
    "is_icf_enabled",
    "health",
    "get_icf_status",
    "coverage_dashboard",
    "coverage_score_for",
    "icc_status_for",
    "plan_and_dispatch",
    "run_coverage_tick",
    "soft_slice_mission_control",
]
