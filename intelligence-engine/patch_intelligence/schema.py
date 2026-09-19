"""Patch Intelligence — human-in-the-loop engineering briefs (never auto-codes)."""

from __future__ import annotations

from typing import Any

PI_VERSION = "patch-intelligence-v1.0.0"
PROGRAMME = "AGIB v3.6 – Phase 3 Quality Programme · Patch Intelligence"
MODULE_CODE = "PI"

FREEZE_LOCKS: dict[str, Any] = {
    "never_writes_code_automatically": True,
    "human_in_the_loop": True,
    "reasoning_frozen": True,
    "soft_wire_only": True,
    "deterministic_only": True,
}
