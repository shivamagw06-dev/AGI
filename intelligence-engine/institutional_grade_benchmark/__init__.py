"""IB-01 — AGIB Institutional Benchmark.

Can AGIB produce institutional-grade research comparable to Bloomberg,
Capital IQ, FactSet, AlphaSense, and sell-side research?

PAT proves the software works. IB-01 proves the intelligence is competitive.
"""

from __future__ import annotations

from institutional_grade_benchmark.schema import (
    IB_PRODUCT,
    IB_VERSION,
    IB_WORKSTREAM_ID,
    PASS_THRESHOLD,
    TOTAL_POINTS,
)
from institutional_grade_benchmark.runner import run_all

__all__ = [
    "IB_WORKSTREAM_ID",
    "IB_PRODUCT",
    "IB_VERSION",
    "TOTAL_POINTS",
    "PASS_THRESHOLD",
    "run_all",
]
