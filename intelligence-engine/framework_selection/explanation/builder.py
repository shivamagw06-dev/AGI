"""Framework Explanation Object — auditable selection rationale."""

from __future__ import annotations

from typing import Any

from framework_selection.registry.frameworks import get_framework
from framework_selection.rules.forbidden import forbidden_for_sector


def build_explanation(
    *,
    selected: list[dict[str, Any]],
    sector: str | None,
    sector_source: str,
    intent_v2: str | None,
    confidence: dict[str, Any],
    forbidden_rejected: list[str],
    evidence_required: list[str],
    evidence_present: list[str] | None = None,
) -> dict[str, Any]:
    lines = []
    for row in selected:
        role = str(row.get("role") or "supporting").title()
        name = row.get("name") or row.get("framework_id")
        lines.append(f"{name} ({role})")

    sector_label = sector or "unspecified"
    reason_bits = [
        f"Sector context: {sector_label} (source={sector_source}).",
        f"Intent: {intent_v2 or 'Unknown'}.",
    ]
    if sector == "banks":
        reason_bits.append(
            "The entity/context is a regulated bank with book value as the principal "
            "anchor of value. EV/EBITDA is explicitly excluded by the framework registry."
        )
    elif sector == "it_services":
        reason_bits.append(
            "IT services are cash-generative operating businesses — DCF and EV/EBITDA apply."
        )
    elif sector == "conglomerates":
        reason_bits.append("Multi-business groups require Sum-of-the-Parts, not a single multiple.")
    elif intent_v2 in {"Macro", "CrossDomain"}:
        reason_bits.append("Macro / cross-domain questions use transmission and scenario frameworks.")
    elif intent_v2 == "Government":
        reason_bits.append("Government questions use the policy framework.")

    if forbidden_rejected:
        reason_bits.append(
            "Excluded forbidden frameworks: " + ", ".join(forbidden_rejected) + "."
        )

    present = set(evidence_present or [])
    evidence_checks = []
    for et in evidence_required:
        evidence_checks.append({"evidence": et, "present": et in present or not present})

    return {
        "selected_frameworks": [
            {
                "framework_id": r.get("framework_id"),
                "name": r.get("name"),
                "role": r.get("role"),
            }
            for r in selected
        ],
        "selected_lines": lines,
        "reason": " ".join(reason_bits),
        "confidence": {
            "pct": (confidence or {}).get("pct"),
            "band": (confidence or {}).get("band"),
            "score": (confidence or {}).get("score"),
        },
        "evidence_required": evidence_checks,
        "forbidden_for_sector": forbidden_for_sector(sector),
        "sector": sector,
        "intent_v2": intent_v2,
        "fabricated": False,
    }


def evidence_union(selected: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for row in selected:
        meta = get_framework(str(row.get("framework_id"))) or {}
        for et in meta.get("required_evidence") or []:
            if et not in seen:
                seen.add(et)
                out.append(et)
    return out
