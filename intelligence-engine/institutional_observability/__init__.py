"""PRP-03 — Observability & Operations.

Observability explains how the platform behaves.
It never changes platform behavior.
"""

from institutional_observability.schema import (
    AGIB_PLATFORM_VERSION,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    PRP_VERSION,
    PRP_WORKSTREAM_ID,
)

__all__ = [
    "PRP_WORKSTREAM_ID",
    "PRP_VERSION",
    "ARCHITECTURE_FROZEN",
    "AGIB_PLATFORM_VERSION",
    "GUIDING_PRINCIPLE",
]
