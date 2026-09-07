"""Research Office morning workflow definition (metadata)."""

from __future__ import annotations

from typing import Any

from research_office.schema import PUBLICATION_TYPES, RO_VERSION

MORNING_WORKFLOW: dict[str, Any] = {
    "workflow_id": "research_office_morning",
    "name": "Institutional Research Office — Morning Desk",
    "trigger": "institutional_scheduler.READY",
    "steps": [
        "morning_publications",
        "company_research_notes",
        "research_queue",
        "watchlists",
        "mission_control_soft_update",
        "ready_for_users",
    ],
    "publication_types": list(PUBLICATION_TYPES),
    "version": RO_VERSION,
    "knowledge_only": True,
    "no_recommendations": True,
}
