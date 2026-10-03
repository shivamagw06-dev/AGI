"""PAT-01 — Production Acceptance Test for AGIB v1.0 GA.

Break the platform before onboarding users. Architecture remains frozen.
"""

from __future__ import annotations

from institutional_acceptance.schema import (
    PAT_PRODUCT,
    PAT_VERSION,
    PAT_WORKSTREAM_ID,
)
from institutional_acceptance.test_runner import run_all, run_phase

__all__ = [
    "PAT_WORKSTREAM_ID",
    "PAT_PRODUCT",
    "PAT_VERSION",
    "run_all",
    "run_phase",
]
