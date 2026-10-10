"""Ownership engine — every section belongs to one owner."""

from __future__ import annotations

from typing import Any

from research_blueprint.blueprint_registry import DEFAULT_SECTION_OWNERS


def assign_owners(
    *,
    section_keys: list[str],
    required_analysts: list[str] | None = None,
) -> dict[str, Any]:
    required = set(required_analysts or [])
    owners: dict[str, str] = {}
    for key in section_keys:
        owner = DEFAULT_SECTION_OWNERS.get(key, "Research Writer")
        # If owner analyst is suppressed from IAR, keep ownership but mark note
        owners[key] = owner

    # Writing / synthesis always Research Writer / CIO where applicable
    if "executive_summary" in owners:
        owners["executive_summary"] = "Research Writer"
    if "cio_summary" in owners:
        owners["cio_summary"] = "CIO"
    if "committee_opinion" in owners:
        owners["committee_opinion"] = "Committee"

    ownership_ok = all(bool(owners.get(k)) for k in section_keys)
    return {
        "section_owner": owners,
        "ownership_complete": ownership_ok,
        "owners_unique": sorted(set(owners.values())),
        "required_analysts_context": sorted(required),
    }
