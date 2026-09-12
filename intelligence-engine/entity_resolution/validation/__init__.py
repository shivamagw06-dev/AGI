"""ERE validation helpers."""

from __future__ import annotations

from typing import Any

from entity_resolution.schema import CANONICAL_FIELDS, OUTPUT_FIELDS


def validate_output(row: dict[str, Any]) -> dict[str, Any]:
    missing = [f for f in OUTPUT_FIELDS if f not in row]
    canonical_ok = True
    ce = row.get("canonical_entity")
    if ce:
        canonical_ok = all(f in ce for f in CANONICAL_FIELDS)
    return {
        "ok": not missing and (row.get("needs_clarification") or canonical_ok),
        "missing_output_fields": missing,
        "canonical_complete": canonical_ok,
        "never_guess_honored": bool(row.get("never_guess")),
        "blocked_when_unclear": (not row.get("needs_clarification"))
        or bool(row.get("research_blocked")),
    }
