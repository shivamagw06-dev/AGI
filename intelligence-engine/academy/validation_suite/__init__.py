"""Academy Validation Suite — can the intelligence demonstrate institutional knowledge?"""

from academy.validation_suite.production import (
    dashboard,
    list_exams,
    quality_gates,
    reset_for_tests,
    run_exam,
    run_level,
    run_suite,
)
from academy.validation_suite.schema import AVS_VERSION

__all__ = [
    "AVS_VERSION",
    "dashboard",
    "list_exams",
    "quality_gates",
    "reset_for_tests",
    "run_exam",
    "run_level",
    "run_suite",
]
