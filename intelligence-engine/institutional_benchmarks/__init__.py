"""IBS-01 — AGI Institutional Benchmark Suite."""

from institutional_benchmarks.production import (
    dashboard,
    get_benchmark,
    health,
    list_benchmarks,
    run,
    run_all_benchmarks,
    soft_slice_mission_control,
)
from institutional_benchmarks.schema import IBS_VERSION, IBS_WORKSTREAM_ID

__all__ = [
    "IBS_WORKSTREAM_ID",
    "IBS_VERSION",
    "health",
    "dashboard",
    "list_benchmarks",
    "get_benchmark",
    "run",
    "run_all_benchmarks",
    "soft_slice_mission_control",
]
