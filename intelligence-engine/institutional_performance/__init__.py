"""PRP-01 — Performance & Scale (Production Readiness Programme).

No intelligence engines. Architecture frozen at AGIB v1.0.
"""

from institutional_performance.schema import (
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
)

__all__ = [
    "PRP_WORKSTREAM_ID",
    "PRP_VERSION",
    "ARCHITECTURE_FROZEN",
    "AGIB_PLATFORM_VERSION",
]
