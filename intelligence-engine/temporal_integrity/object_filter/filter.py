"""Generic object filter — available_from <= as_of."""

from __future__ import annotations

from typing import Any

from temporal_integrity.validator.contract import evaluate_object


def filter_objects(
    objects: list[dict[str, Any]] | None,
    *,
    as_of: str | None,
    source: str = "object",
    reject_unknown: bool = False,
) -> dict[str, Any]:
    rows = list(objects or [])
    if not as_of:
        return {
            "kept": rows,
            "rejected": [],
            "contracts": [],
            "n_checked": len(rows),
            "n_rejected": 0,
            "as_of": as_of,
            "fabricated": False,
        }
    kept: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    contracts: list[dict[str, Any]] = []
    for obj in rows:
        ev = evaluate_object(obj, as_of=as_of, source=source)
        c = ev["contract"]
        contracts.append(c)
        status = c.get("temporal_status")
        if status == "allowed" or (status == "unknown" and not reject_unknown):
            kept.append(obj)
        else:
            rejected.append({"object": obj, "contract": c})
    return {
        "kept": kept,
        "rejected": rejected,
        "contracts": contracts,
        "n_checked": len(rows),
        "n_rejected": len(rejected),
        "as_of": as_of,
        "fabricated": False,
    }
