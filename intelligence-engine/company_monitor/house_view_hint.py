"""Suggested House View Review — never auto-changes house view."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from company_monitor.flags import flag_house_view_hints


def maybe_suggest_review(
    ticker: str,
    *,
    changes: list[dict[str, Any]],
    summary: dict[str, Any] | None = None,
    house_view_label: str | None = None,
) -> dict[str, Any] | None:
    if not flag_house_view_hints():
        return None

    material = [c for c in changes if str(c.get("significance") or "") in {"High", "Critical"}]
    if not material:
        return None

    reasons = [str(c.get("detail") or c.get("change_type")) for c in material[:6]]
    return {
        "ticker": (ticker or "").upper(),
        "suggested_at": datetime.now(timezone.utc).isoformat(),
        "action": "Suggested House View Review",
        "auto_changed": False,
        "policy": "never_automatically_change_house_view",
        "current_house_view_label": house_view_label,
        "max_significance": (summary or {}).get("max_significance") or material[0].get("significance"),
        "reasons": reasons,
        "material_changes": len(material),
    }
