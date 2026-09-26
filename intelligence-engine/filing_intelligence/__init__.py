"""Filing Intelligence Layer V1 — institutional memory from official filings."""

from filing_intelligence.production import (
    analyse,
    company,
    dashboard,
    evidence,
    history,
    quality_gates,
    soft_slice_for_analyst,
    soft_slice_for_eil,
    soft_slice_for_irs,
    timeline,
)
from filing_intelligence.schema import FIL_VERSION

__all__ = [
    "FIL_VERSION",
    "analyse",
    "company",
    "dashboard",
    "evidence",
    "history",
    "quality_gates",
    "soft_slice_for_analyst",
    "soft_slice_for_eil",
    "soft_slice_for_irs",
    "timeline",
]
