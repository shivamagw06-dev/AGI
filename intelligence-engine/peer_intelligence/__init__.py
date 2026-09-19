"""Peer Intelligence Layer V1 — institutional comparison engine (soft layer)."""

from peer_intelligence.production import (
    analyse,
    company,
    compare,
    dashboard,
    history,
    quality_gates,
    rankings,
    soft_slice_for_analyst,
    soft_slice_for_eil,
    soft_slice_for_irs,
)
from peer_intelligence.schema import PIL_VERSION

__all__ = [
    "PIL_VERSION",
    "analyse",
    "company",
    "compare",
    "dashboard",
    "history",
    "quality_gates",
    "rankings",
    "soft_slice_for_analyst",
    "soft_slice_for_eil",
    "soft_slice_for_irs",
]
