"""Suppression policy — unselected analysts must not execute."""

from __future__ import annotations

from typing import Any

from analyst_router.mandates import never_topics
from analyst_router.schema import ANALYST_REGISTRY


def build_exclusions(
    required: list[str],
    optional: list[str],
    suppressed: list[str],
    synthesis: list[str] | None = None,
) -> dict[str, Any]:
    allowed = set(required) | set(optional) | set(synthesis or [])
    must_not_run = [a for a in ANALYST_REGISTRY if a not in allowed]
    # Prefer provided suppressed list order when present
    if suppressed:
        must_not_run = list(suppressed)

    mandate_walls = {a: never_topics(a) for a in (list(required) + list(optional))}

    return {
        "suppressed_analysts": must_not_run,
        "no_placeholders": True,
        "no_empty_sections": True,
        "no_generic_paragraphs": True,
        "execution_policy": "Suppressed analysts must not execute.",
        "mandate_walls": mandate_walls,
        "unavailable_policy": {
            "if_required_unavailable": "Pause",
            "if_optional_unavailable": "Continue",
        },
    }
