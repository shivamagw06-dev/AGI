"""KOC V1.2 — Institutional Knowledge Mission Control."""

from __future__ import annotations

from knowledge_operations.production import (
    get_desk,
    get_missing_inbox,
    get_overview,
    get_status,
    get_system_health,
    health,
    soft_slice_mission_control,
)
from knowledge_operations.schema import KOC_VERSION, KOC_WORKSTREAM_ID

__all__ = [
    "KOC_VERSION",
    "KOC_WORKSTREAM_ID",
    "health",
    "get_status",
    "get_overview",
    "get_desk",
    "get_system_health",
    "get_missing_inbox",
    "soft_slice_mission_control",
]
