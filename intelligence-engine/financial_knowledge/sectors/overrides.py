"""Sector-specific guidance and threshold overrides (FKB-01)."""

from __future__ import annotations

from typing import Any

SECTOR_GUIDANCE: dict[str, dict[str, Any]] = {
    "banks": {
        "sector": "BANKS",
        "notes": [
            "ROE interpretation differs from industrials; leverage is structural.",
            "Cash conversion cycle and inventory metrics are generally not applicable.",
            "Asset quality and NIM matter more than gross margin.",
        ],
        "preferred_return_metric": "roe",
        "de_emphasize": ["inventory_turnover", "cash_conversion_cycle", "gross_margin"],
        "threshold_overrides": {
            "roe_quality_default": {"value": 12.0, "description": "Banking ROE quality reference (indicative)."},
            "debt_to_ebitda_warning": {"value": None, "description": "Debt/EBITDA less meaningful for banks."},
        },
    },
    "insurance": {
        "sector": "INSURANCE",
        "notes": [
            "Combined ratio is a primary underwriting quality lens.",
            "Investment income complicates simple operating margin reads.",
        ],
        "preferred_return_metric": "roe",
        "de_emphasize": ["inventory_turnover"],
        "threshold_overrides": {
            "roe_quality_default": {"value": 12.0, "description": "Insurance ROE quality reference (indicative)."},
        },
    },
    "manufacturing": {
        "sector": "MANUFACTURING",
        "notes": [
            "Inventory days and working capital efficiency are important.",
            "ROCE is often more informative than ROE.",
        ],
        "preferred_return_metric": "roce",
        "emphasize": ["inventory_turnover", "cash_conversion_cycle", "roce"],
        "threshold_overrides": {
            "roce_quality_default": {"value": 15.0},
            "debt_to_ebitda_warning": {"value": 2.5},
        },
    },
    "software": {
        "sector": "SOFTWARE",
        "notes": [
            "Gross margin expectations are typically higher than manufacturing.",
            "Recurring revenue quality matters more than inventory metrics.",
        ],
        "preferred_return_metric": "roic",
        "emphasize": ["gross_margin", "recurring_revenue", "fcf_conversion"],
        "de_emphasize": ["inventory_turnover"],
        "threshold_overrides": {
            "margin_expansion_bps": {"value": 100.0},
            "roe_quality_default": {"value": 18.0},
        },
    },
    "capital_intensive": {
        "sector": "CAPITAL_INTENSIVE",
        "notes": [
            "ROCE is more important than simple growth metrics.",
            "Capex and FCF conversion require careful interpretation through the cycle.",
        ],
        "preferred_return_metric": "roce",
        "emphasize": ["roce", "capex", "free_cash_flow", "asset_turnover"],
        "threshold_overrides": {
            "roce_quality_default": {"value": 12.0, "description": "Lower ROCE bar may still be acceptable mid-cycle."},
            "debt_to_ebitda_warning": {"value": 3.0},
        },
    },
}


def all_sectors() -> list[dict[str, Any]]:
    return [dict(v) for v in SECTOR_GUIDANCE.values()]


def get_sector(key: str) -> dict[str, Any] | None:
    k = key.strip().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "bank": "banks",
        "banking": "banks",
        "it": "software",
        "tech": "software",
        "saas": "software",
        "capex_heavy": "capital_intensive",
        "infrastructure": "capital_intensive",
    }
    k = aliases.get(k, k)
    row = SECTOR_GUIDANCE.get(k)
    return dict(row) if row else None


def sector_threshold(sector: str, threshold_id: str) -> dict[str, Any] | None:
    sec = get_sector(sector)
    if not sec:
        return None
    ov = (sec.get("threshold_overrides") or {}).get(threshold_id)
    if ov is None:
        return None
    return dict(ov)
