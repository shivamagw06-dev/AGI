"""Report policy — publication constraints for the selected blueprint."""

from __future__ import annotations

from typing import Any


def build_report_policy(
    report_type: str,
    bp_meta: dict[str, Any],
    priorities: dict[str, Any],
) -> dict[str, Any]:
    return {
        "report_type": report_type,
        "audience": bp_meta.get("audience"),
        "purpose": bp_meta.get("purpose"),
        "output_style": bp_meta.get("output_style"),
        "max_length_words": bp_meta.get("max_length_words"),
        "must_include": list(priorities.get("mandatory_sections") or []),
        "must_not_include": list(priorities.get("suppressed_sections") or []),
        "hidden_by_default": list(priorities.get("hidden_sections") or []),
        "blueprint_finalised_before_research": True,
    }
