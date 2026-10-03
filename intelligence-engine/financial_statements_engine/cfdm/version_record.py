"""Version record for facts/statements (FSE-03 §14)."""

from __future__ import annotations

from typing import Any

from financial_statements_engine.util import now_iso


def build_version_record(
    *,
    entity_id: str,
    entity_type: str,
    version: int,
    previous_version: int | None = None,
    change_reason: str | None = None,
    effective_date: str | None = None,
    restatement: bool = False,
) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "entity_type": entity_type,
        "version": int(version),
        "previous_version": previous_version,
        "change_reason": change_reason,
        "effective_date": effective_date,
        "restatement": bool(restatement),
        "immutable": True,
        "recorded_at": now_iso(),
        "object": "version",
    }
