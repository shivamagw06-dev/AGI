"""RH-01 — AGI Release Health (single release gate dashboard)."""

from __future__ import annotations

from typing import Any

RH_WORKSTREAM_ID = "RH-01"
RH_PRODUCT = "AGI Release Health"
RH_VERSION = "rh-01-v1.0.0"
RH_SUBSYSTEM = "release_health"
RH_SPEC = "docs/AGI_RH_01_RELEASE_HEALTH.md"
RH_ROLE = "release_gate_dashboard"

IST_EXPECTED = 2
IBS_EXPECTED = 39
E2E_EXPECTED = 1

RELEASE_GATES: dict[str, Any] = {
    "ist_pass_min": IST_EXPECTED,
    "ibs_pass_min": IBS_EXPECTED,
    "e2e_pass_min": E2E_EXPECTED,
    "hallucinations_max": 0,
    "broken_provenance_max": 0,
    "regression_max": 0,  # average must not fall
    "average_benchmark_min": 85.0,
    "performance_must_pass": True,
}
