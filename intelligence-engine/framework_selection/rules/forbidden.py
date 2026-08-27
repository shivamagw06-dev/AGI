"""Forbidden framework rules by sector / context."""

from __future__ import annotations

from typing import Any

# Sector → frameworks that must never be selected as primary/sole valuation anchors
FORBIDDEN_BY_SECTOR: dict[str, set[str]] = {
    "banks": {"FW_EV_EBITDA", "FW_EV_SALES", "FW_ROIC"},
    "insurance": {"FW_EV_EBITDA", "FW_EV_SALES"},
    "nbfc": {"FW_EV_EBITDA", "FW_EV_SALES"},
}

# Soft composition rules — reject incomplete compositions
COMPOSITION_RULES: list[dict[str, Any]] = [
    {
        "id": "airlines_not_pb_only",
        "sector": "airlines",
        "reject_if_only": {"FW_PB"},
        "reason": "Airlines must not be analysed on Price/Book alone",
    },
    {
        "id": "conglomerates_require_sotp",
        "sector": "conglomerates",
        "require_any": {"FW_SOTP"},
        "reject_if_single_multiple_only": {"FW_PE", "FW_EV_EBITDA", "FW_PB"},
        "reason": "Conglomerates require SOTP; a single multiple is insufficient",
    },
    {
        "id": "hospitals_not_dcf_only",
        "sector": "hospitals",
        "reject_if_only": {"FW_DCF"},
        "reason": "Hospitals must not use DCF alone — require healthcare ops / EV-EBITDA",
    },
]


def is_forbidden(framework_id: str, *, sector: str | None) -> bool:
    if not sector:
        return False
    return framework_id in FORBIDDEN_BY_SECTOR.get(sector, set())


def forbidden_for_sector(sector: str | None) -> list[str]:
    if not sector:
        return []
    return sorted(FORBIDDEN_BY_SECTOR.get(sector, set()))
