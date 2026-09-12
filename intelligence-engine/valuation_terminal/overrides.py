"""Manual overrides with a full audit trail.

Imported values are never overwritten. An override is a new layer on top of
the import, carrying who changed it, when, and why — so any number on the
terminal can be traced back to either a vendor or a named person.
"""

from __future__ import annotations

import json
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from valuation_terminal.store import store_root

_LOCK = threading.RLock()
_CACHE: dict[str, Any] | None = None

# Fields an admin may override.
EDITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "price",
        "market_cap",
        "pe",
        "forward_pe",
        "pb",
        "ev_ebitda",
        "ev_sales",
        "ps",
        "roe",
        "eps",
        "book_value",
        "dividend_yield",
        "profit_margin",
        "debt_to_equity",
    }
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _path() -> Path:
    return store_root() / "overrides.json"


def _load() -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        if _CACHE is not None:
            return _CACHE
        payload: dict[str, Any] = {"rows": {}, "audit": []}
        if _path().exists():
            try:
                disk = json.loads(_path().read_text(encoding="utf-8"))
                if isinstance(disk, dict):
                    payload = {"rows": disk.get("rows") or {}, "audit": disk.get("audit") or []}
            except Exception:
                pass
        _CACHE = payload
        return payload


def _save(payload: dict[str, Any]) -> None:
    global _CACHE
    with _LOCK:
        tmp = _path().with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
        tmp.replace(_path())
        _CACHE = payload


def invalidate_cache() -> None:
    global _CACHE
    with _LOCK:
        _CACHE = None


def set_override(
    ticker: str,
    field: str,
    value: Any,
    *,
    actor: str,
    reason: str,
    imported_value: Any = None,
) -> dict[str, Any]:
    tk = str(ticker or "").strip().upper()
    key = str(field or "").strip()
    if not tk:
        return {"ok": False, "error": "ticker_required"}
    if key not in EDITABLE_FIELDS:
        return {"ok": False, "error": "field_not_editable", "field": key}
    if not str(reason or "").strip():
        return {"ok": False, "error": "reason_required"}

    payload = _load()
    rows = dict(payload["rows"])
    company = dict(rows.get(tk) or {})
    history = list((company.get(key) or {}).get("history") or [])

    entry = {
        "id": uuid.uuid4().hex[:10],
        "value": value,
        "imported_value": imported_value,
        "actor": actor or "admin",
        "reason": str(reason).strip(),
        "at": _now(),
    }
    history.append(entry)
    company[key] = {
        "value": value,
        "imported_value": imported_value,
        "actor": entry["actor"],
        "reason": entry["reason"],
        "updated_at": entry["at"],
        "version": len(history),
        "history": history,
    }
    rows[tk] = company

    audit = list(payload["audit"])
    audit.append({"ticker": tk, "field": key, **entry})
    _save({"rows": rows, "audit": audit[-2000:]})
    return {"ok": True, "ticker": tk, "field": key, **company[key]}


def clear_override(ticker: str, field: str, *, actor: str, reason: str) -> dict[str, Any]:
    tk = str(ticker or "").strip().upper()
    payload = _load()
    rows = dict(payload["rows"])
    company = dict(rows.get(tk) or {})
    if field not in company:
        return {"ok": False, "error": "no_override"}
    removed = company.pop(field)
    rows[tk] = company
    audit = list(payload["audit"])
    audit.append(
        {
            "ticker": tk,
            "field": field,
            "id": uuid.uuid4().hex[:10],
            "value": None,
            "imported_value": removed.get("imported_value"),
            "actor": actor or "admin",
            "reason": f"cleared: {reason}",
            "at": _now(),
        }
    )
    _save({"rows": rows, "audit": audit[-2000:]})
    return {"ok": True, "ticker": tk, "field": field, "reverted_to": "imported"}


def for_ticker(ticker: str) -> dict[str, Any]:
    return dict((_load()["rows"].get(str(ticker or "").strip().upper()) or {}))


def apply_to(ticker: str, row: dict[str, Any]) -> dict[str, Any]:
    """Return the row with overrides applied and provenance recorded."""
    overrides = for_ticker(ticker)
    if not overrides:
        return row
    merged = dict(row)
    provenance: dict[str, Any] = {}
    for field, entry in overrides.items():
        provenance[field] = {
            "source": "manual_override",
            "actor": entry.get("actor"),
            "reason": entry.get("reason"),
            "updated_at": entry.get("updated_at"),
            "imported_value": entry.get("imported_value", merged.get(field)),
            "version": entry.get("version"),
        }
        merged[field] = entry.get("value")
    merged["field_provenance"] = provenance
    return merged


def audit_log(limit: int = 100, ticker: Optional[str] = None) -> dict[str, Any]:
    entries = list(_load()["audit"])
    if ticker:
        tk = str(ticker).strip().upper()
        entries = [e for e in entries if e.get("ticker") == tk]
    entries.reverse()
    return {"ok": True, "count": len(entries), "entries": entries[:limit]}


def summary() -> dict[str, Any]:
    payload = _load()
    rows = payload["rows"]
    fields = sum(len(v) for v in rows.values())
    return {
        "companies_with_overrides": len(rows),
        "fields_overridden": fields,
        "audit_entries": len(payload["audit"]),
        "editable_fields": sorted(EDITABLE_FIELDS),
    }
