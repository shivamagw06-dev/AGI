"""Ask AGI Institutional Answer Construction V3 — soft-wire orchestration."""

from answer_construction.production import health, package_for_ask_agi, quality_gates
from answer_construction.schema import AC_VERSION, PROGRAMME

try:
    from answer_construction.response_constitution import (
        CONSTITUTION_VERSION,
        apply_response_constitution,
    )
except Exception:  # pragma: no cover
    CONSTITUTION_VERSION = "1.0"
    apply_response_constitution = None  # type: ignore

__all__ = [
    "PROGRAMME",
    "AC_VERSION",
    "CONSTITUTION_VERSION",
    "health",
    "package_for_ask_agi",
    "quality_gates",
    "apply_response_constitution",
]
