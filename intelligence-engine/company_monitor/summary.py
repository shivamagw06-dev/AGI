"""Build human-readable What Changed summary blocks."""

from __future__ import annotations

from typing import Any


def build_change_summary(
    changes: list[dict[str, Any]],
    *,
    current: dict[str, Any] | None = None,
    previous: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = []
    for c in changes:
        rows.append(
            {
                "metric": c.get("metric"),
                "label": _label(c),
                "current": c.get("current"),
                "previous": c.get("previous"),
                "direction": c.get("direction"),
                "magnitude": c.get("magnitude"),
                "significance": c.get("significance"),
                "detail": c.get("detail"),
                "change_type": c.get("change_type"),
            }
        )

    # Ensure PE vs history narrative when available even if already in changes
    cm = (current or {}).get("metrics") or {}
    pe = cm.get("pe")
    hist = cm.get("historical_pe")
    narrative = []
    for r in rows[:8]:
        narrative.append(str(r.get("detail") or r.get("label")))
    if pe is not None and hist is not None:
        try:
            if float(pe) > float(hist):
                narrative.append(f"Current PE above historical average ({pe} vs {hist})")
            elif float(pe) < float(hist):
                narrative.append(f"Current PE below historical average ({pe} vs {hist})")
        except Exception:
            pass

    max_sig = "Low"
    order = {"Low": 1, "Medium": 2, "High": 3, "Critical": 4}
    for r in rows:
        s = str(r.get("significance") or "Low")
        if order.get(s, 0) > order.get(max_sig, 0):
            max_sig = s

    return {
        "rows": rows,
        "narrative": narrative[:10],
        "max_significance": max_sig,
        "change_count": len(rows),
        "since": (previous or {}).get("captured_at"),
        "as_of": (current or {}).get("captured_at"),
    }


def _label(c: dict[str, Any]) -> str:
    metric = str(c.get("metric") or c.get("change_type") or "change").replace("_", " ").title()
    direction = c.get("direction") or ""
    mag = c.get("magnitude")
    if mag is not None:
        return f"{metric} {direction} {mag}".strip()
    return f"{metric} {direction}".strip()
