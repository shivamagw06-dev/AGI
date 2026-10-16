"""Temporal contract — every object entering reasoning must expose PIT fields."""

from __future__ import annotations

from typing import Any

from temporal_integrity.schema import TEMPORAL_CONTRACT_FIELDS
from temporal_integrity.validator.dates import (
    available_from_of,
    parse_date,
    period_end_year,
    text_has_future_year,
    violates_available_from,
)


def build_contract(
    obj: dict[str, Any],
    *,
    as_of: str | None,
    object_id: str | None = None,
    source: str = "unknown",
) -> dict[str, Any]:
    oid = object_id or str(obj.get("object_id") or obj.get("id") or obj.get("memory_id") or obj.get("node_id") or "")
    af = available_from_of(obj)
    cutoff = parse_date(as_of)
    status = "n/a"
    reason = None
    if cutoff is None:
        status = "n/a"
    elif af is None:
        # Unknown timing: mark unknown; filters decide whether to drop.
        status = "unknown"
        reason = "missing_available_from"
    elif af > cutoff:
        status = "rejected"
        reason = f"available_from>{as_of}"
    else:
        # Period / surface year leaks count as future knowledge
        period = obj.get("time_period") or obj.get("period") or ""
        pend = period_end_year(period)
        if pend is not None and pend > cutoff.year:
            status = "rejected"
            reason = f"time_period_end_year>{cutoff.year}"
        else:
            blob = " ".join(
                str(obj.get(k) or "")
                for k in ("title", "lesson", "outcome", "summary", "label", "text", "surface")
            )
            if text_has_future_year(blob, as_of) or text_has_future_year(period, as_of):
                status = "rejected"
                reason = f"surface_future_year>{cutoff.year}"
            else:
                status = "allowed"

    return {
        "object_id": oid,
        "source": source,
        "available_from": af.isoformat() if af else None,
        "effective_date": str(obj.get("effective_date") or "")[:10] or None,
        "announcement_date": str(obj.get("announcement_date") or "")[:10] or None,
        "observation_date": str(obj.get("observation_date") or "")[:10] or None,
        "source_timestamp": str(obj.get("source_timestamp") or obj.get("available_from") or "")[:10] or None,
        "replay_timestamp": as_of,
        "allowed_as_of": as_of,
        "temporal_status": status,
        "reason_if_rejected": reason,
        "contract_fields": list(TEMPORAL_CONTRACT_FIELDS),
        "fabricated": False,
    }


def is_allowed(contract: dict[str, Any]) -> bool:
    return contract.get("temporal_status") == "allowed"


def evaluate_object(obj: dict[str, Any], *, as_of: str | None, source: str = "unknown") -> dict[str, Any]:
    contract = build_contract(obj, as_of=as_of, source=source)
    return {
        "allowed": is_allowed(contract) if as_of else True,
        "contract": contract,
        "violates_available_from": violates_available_from(obj, as_of) if as_of else False,
    }
