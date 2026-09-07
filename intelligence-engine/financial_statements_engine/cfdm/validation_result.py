"""Validation Result object — status only; never edits fact values (FSE-03 §15)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.cfdm.schema import VALIDATION_STATUSES
from financial_statements_engine.util import now_iso


def build_validation_result(
    *,
    target_id: str,
    target_type: str,
    validation_status: str,
    validation_score: float | None = None,
    issues: list[dict[str, Any]] | None = None,
    validation_engine_version: str = "fse-05-pending",
) -> dict[str, Any]:
    if validation_status not in VALIDATION_STATUSES:
        raise ValueError(f"invalid validation_status: {validation_status}")
    return {
        "target_id": target_id,
        "target_type": target_type,
        "validation_status": validation_status,
        "validation_score": validation_score,
        "validation_timestamp": now_iso(),
        "validation_engine_version": validation_engine_version,
        "issues": list(issues or []),
        "mutates_values": False,
        "object": "validation_result",
    }
