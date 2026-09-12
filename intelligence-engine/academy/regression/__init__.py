"""Institutional Regression Suite (IRS) V1 — Did this PR make AGIB smarter?"""

from academy.regression.production import (
    admin_page,
    dashboard,
    is_enabled,
    quality_gates,
    release_gate,
    reset_for_tests,
    run_regression,
)
from academy.regression.schema import IRS_VERSION

__all__ = [
    "IRS_VERSION",
    "admin_page",
    "dashboard",
    "is_enabled",
    "quality_gates",
    "release_gate",
    "reset_for_tests",
    "run_regression",
]
