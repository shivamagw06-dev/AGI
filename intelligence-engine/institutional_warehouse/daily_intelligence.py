"""Bounded post-close fundamental refresh and cached change feed.

This module intentionally does not call vendors, rebuild the historical
warehouse, or run technical analysis. The finance service supplies the small
set of companies whose source statements were refreshed after market close.
Only those companies are recalculated and published as an auditable change
feed for product pages and the research desk.
"""

from __future__ import annotations

import uuid
from typing import Any, Iterable

from institutional_warehouse import audit, gateway, store
from institutional_warehouse.formulas import recalculate
from institutional_warehouse.values import today_iso

SOURCE = "daily_intelligence_refresh"
_FUNDAMENTAL_FIELDS = ("revenue", "pat", "equity", "debt")
_ALPHA_FIELDS = ("value_score", "quality_score", "growth_score", "consensus_score", "opportunity_score")


def _latest(rows: list[dict[str, Any]], key: str) -> dict[str, Any]:
    usable = [row for row in rows if row.get(key) not in (None, "")]
    return max(usable, key=lambda row: str(row.get(key))) if usable else {}


def _number(value: Any) -> float | None:
    try:
        if value in (None, ""):
            return None
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _snapshot(symbol: str) -> dict[str, dict[str, float | None]]:
    annual = _latest(store.all_rows("financials_annual", entity=symbol, limit=40), "fiscal_year")
    factors = _latest(store.all_rows("hedge_fund_factors", entity=symbol, limit=8), "as_of")
    return {
        "fundamentals": {field: _number(annual.get(field)) for field in _FUNDAMENTAL_FIELDS},
        "alpha": {field: _number(factors.get(field)) for field in _ALPHA_FIELDS},
    }


def _changed(before: dict[str, Any], after: dict[str, Any], group: str) -> dict[str, dict[str, float | None]]:
    output: dict[str, dict[str, float | None]] = {}
    for field, current in (after.get(group) or {}).items():
        previous = (before.get(group) or {}).get(field)
        if previous != current:
            output[field] = {"previous": previous, "current": current}
    return output


def _summary(change_type: str, changes: dict[str, dict[str, float | None]]) -> str:
    if not changes:
        return "Source refresh completed; no material computed field changed."
    labels = ", ".join(field.replace("_", " ").upper() for field in changes)
    lead = "Reported financial fields updated" if change_type == "fundamentals" else "Fundamental Alpha scores recalculated"
    return f"{lead}: {labels}."


def refresh_companies(
    symbols: Iterable[str], *, actor: str = "daily_intelligence_refresh", max_companies: int = 25
) -> dict[str, Any]:
    """Recalculate fundamental-only intelligence for a finite source-updated batch."""
    unique: list[str] = []
    for value in symbols:
        symbol = str(value or "").strip().upper()
        if symbol and symbol not in unique:
            unique.append(symbol)
    targets = unique[: max(1, min(int(max_companies or 25), 50))]
    run_id = uuid.uuid4().hex
    date = today_iso()
    records: list[dict[str, Any]] = []
    refreshed: list[str] = []
    errors: list[dict[str, str]] = []

    for symbol in targets:
        before = _snapshot(symbol)
        result = recalculate(
            actor=actor,
            entity=symbol,
            stages=("statement_derivations", "ratios", "factors"),
            as_of=date,
        )
        if not result.get("ok"):
            errors.append({"symbol": symbol, "error": str(result.get("errors") or "recalculate_failed")})
            continue
        after = _snapshot(symbol)
        fundamentals = _changed(before, after, "fundamentals")
        alpha = _changed(before, after, "alpha")
        entries = (("fundamentals", fundamentals), ("alpha", alpha))
        wrote = False
        for change_type, changes in entries:
            if changes:
                records.append({
                    "symbol": symbol, "date": date, "change_type": change_type,
                    "summary": _summary(change_type, changes), "changed_fields": changes,
                    "previous_snapshot": before.get(change_type), "current_snapshot": after.get(change_type),
                    "refresh_run_id": run_id,
                })
                wrote = True
        if not wrote:
            records.append({
                "symbol": symbol, "date": date, "change_type": "no_material_change",
                "summary": _summary("no_material_change", {}), "changed_fields": {},
                "previous_snapshot": before, "current_snapshot": after, "refresh_run_id": run_id,
            })
        refreshed.append(symbol)

    written = gateway.write(
        "daily_intelligence_changes", records, source=SOURCE, actor=actor,
        reason="post_close_fundamental_refresh",
    )
    audit.record(
        "daily_intelligence_refresh", actor=actor,
        detail={"run_id": run_id, "targets": targets, "refreshed": refreshed, "errors": errors},
        ok=not errors,
    )
    return {
        "ok": not errors, "run_id": run_id, "date": date, "requested": len(targets),
        "refreshed": refreshed, "change_records": written.get("written", 0),
        "errors": errors, "write": written,
    }
