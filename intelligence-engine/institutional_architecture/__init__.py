"""RC-01 — Architecture Conformance & Release Candidate.

Quality gate for AGIB v1.0. Not a feature.
"""

from institutional_architecture.schema import (
    AGIB_GENERAL_AVAILABILITY,
    AGIB_PLATFORM_VERSION,
    AGIB_RELEASE_CANDIDATE,
    AGIB_RELEASE_STATUS,
    ARCHITECTURE_FROZEN,
    GUIDING_PRINCIPLE,
    RC_VERSION,
    RC_WORKSTREAM_ID,
)

__all__ = [
    "RC_WORKSTREAM_ID",
    "RC_VERSION",
    "ARCHITECTURE_FROZEN",
    "AGIB_PLATFORM_VERSION",
    "AGIB_RELEASE_CANDIDATE",
    "AGIB_GENERAL_AVAILABILITY",
    "AGIB_RELEASE_STATUS",
    "GUIDING_PRINCIPLE",
]
