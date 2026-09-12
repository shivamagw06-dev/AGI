"""Section priority — mandatory / optional / hidden / suppressed."""

from __future__ import annotations

from typing import Any

# Sections that are irrelevant for educational questions
EDUCATIONAL_SUPPRESS = {
    "portfolio_fit",
    "committee_opinion",
    "forecast",
    "valuation",
    "investment_thesis",
    "cio_summary",
    "risk",
    "stress_scenarios",
}


def prioritise_sections(
    *,
    report_type: str,
    mandatory: list[str],
    optional: list[str],
    suppress_default: list[str],
    primary_objective: str | None = None,
    intent_family: str | None = None,
) -> dict[str, Any]:
    obj = (primary_objective or "").strip().lower()
    family = (intent_family or "").strip().lower()

    suppressed = set(suppress_default)
    if report_type == "educational_guide" or obj in {"educational", "educational_explanation"} or family == "educational":
        suppressed |= EDUCATIONAL_SUPPRESS

    # Hidden: optional that we keep in blueprint but not render by default
    hidden: set[str] = set()
    for key in optional:
        if key == "appendix":
            hidden.add(key)

    mandatory_final = [k for k in mandatory if k not in suppressed]
    optional_final = [k for k in optional if k not in suppressed and k not in hidden]
    hidden_final = sorted(hidden - suppressed)
    suppressed_final = sorted(suppressed)

    # No irrelevant: suppressed must not appear in mandatory/optional
    irrelevant_leak = [k for k in mandatory_final + optional_final if k in suppressed]
    return {
        "mandatory_sections": mandatory_final,
        "optional_sections": optional_final,
        "hidden_sections": hidden_final,
        "suppressed_sections": suppressed_final,
        "priorities": {
            **{k: "mandatory" for k in mandatory_final},
            **{k: "optional" for k in optional_final},
            **{k: "hidden" for k in hidden_final},
            **{k: "suppressed" for k in suppressed_final},
        },
        "no_irrelevant_sections": len(irrelevant_leak) == 0,
    }
