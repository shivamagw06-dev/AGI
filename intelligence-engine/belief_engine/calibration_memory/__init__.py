"""Calibration memory — soft store of past belief accuracy hooks for ILM."""

from __future__ import annotations

from typing import Any

_MEMORY: list[dict[str, Any]] = []
# Running type-level calibration proxies (start neutral-high until outcomes arrive)
_TYPE_CALIBRATION: dict[str, float] = {
    "Business": 0.7,
    "Financial": 0.68,
    "Valuation": 0.62,
    "Macro": 0.58,
    "Risk": 0.6,
    "Portfolio": 0.65,
}


def historical_calibration_for_type(hyp_type: str) -> float:
    return float(_TYPE_CALIBRATION.get(hyp_type, 0.62))


def remember_belief(row: dict[str, Any]) -> dict[str, Any]:
    entry = {
        "question": row.get("question"),
        "belief_count": row.get("belief_count"),
        "mean_posterior": (row.get("metrics") or {}).get("mean_posterior"),
        "mean_confidence": (row.get("metrics") or {}).get("mean_confidence"),
        "timestamp": (row.get("metrics") or {}).get("generated_at"),
        "learning": {"feed_into": "ILM", "stage": "institutional_belief_update"},
    }
    _MEMORY.append(entry)
    if len(_MEMORY) > 500:
        del _MEMORY[:-500]
    return entry


def recent(limit: int = 20) -> list[dict[str, Any]]:
    return list(reversed(_MEMORY[-limit:]))


def memory_stats() -> dict[str, Any]:
    return {
        "stored": len(_MEMORY),
        "recent": recent(5),
        "type_calibration": dict(_TYPE_CALIBRATION),
    }
