"""IKT durable versioned fact store — one JSON file per company.

Layout: $KIP_DATA_DIR/institutional_knowledge_tables/facts/<TICKER>.json

    {
      "ticker": "RELIANCE",
      "tables": {
        "company_master": {
          "sector": [ {value, source, effective_date, recorded_at, version, current}, ... ]
        },
        "financial_statements": {
          "FY2024|Q4::revenue": [ ... ]
        }
      },
      "updated_at": "..."
    }

Design rules (do not violate):
  * Never overwrite history — append a new version, mark prior current=False.
  * Never fabricate — a field with no recorded fact is simply absent.
  * keyed_by_period tables namespace facts by `<period>::<field>`.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from institutional_knowledge_tables.schema import TABLE_DEFS, table_fields, valid_table

_LOCK = threading.RLock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today() -> str:
    return date.today().isoformat()


def store_root() -> Path:
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    raw = (os.getenv("IKT_STORE_ROOT") or "").strip()
    if raw:
        root = Path(raw)
    elif kip:
        root = Path(kip) / "institutional_knowledge_tables"
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "institutional_knowledge_tables"
    (root / "facts").mkdir(parents=True, exist_ok=True)
    return root


def _company_path(ticker: str) -> Path:
    t = str(ticker or "").strip().upper()
    return store_root() / "facts" / f"{t}.json"


def _write_json(path: Path, payload: Any) -> None:
    try:
        from institutional_data.persistence.atomic import atomic_write_json, file_lock

        with file_lock(path):
            atomic_write_json(path, payload)
        return
    except Exception:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)


def _read_json(path: Path) -> Any:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_company(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").strip().upper()
    disk = _read_json(_company_path(t))
    if isinstance(disk, dict):
        disk.setdefault("tables", {})
        return disk
    return {"ticker": t, "tables": {}, "updated_at": None}


def _save_company(ticker: str, body: dict[str, Any]) -> None:
    body["updated_at"] = _now()
    _write_json(_company_path(ticker), body)


def _fact_key(table: str, field: str, period: str | None) -> str:
    meta = TABLE_DEFS.get(table) or {}
    if meta.get("keyed_by_period"):
        p = str(period or "unspecified").strip()
        return f"{p}::{field}"
    return field


def upsert_fact(
    ticker: str,
    table: str,
    field: str,
    value: Any,
    *,
    source: str,
    effective_date: str | None = None,
    period: str | None = None,
    trigger: str = "collector",
) -> dict[str, Any]:
    """Append a new versioned fact. Prior versions of the same field/period stay
    in history with current=False — never overwritten, never deleted.
    """
    t = str(ticker or "").strip().upper()
    tb = str(table or "").strip().lower()
    if not t:
        raise ValueError("ticker is required")
    if not valid_table(tb):
        raise ValueError(f"unknown IKT table: {table}")
    fld = str(field or "").strip()
    if fld not in table_fields(tb):
        raise ValueError(f"unknown field '{field}' for table '{tb}'")
    if not source:
        raise ValueError("source is required (evidence lineage; never fabricate)")

    key = _fact_key(tb, fld, period)
    with _LOCK:
        body = _load_company(t)
        tables = body.setdefault("tables", {})
        table_body = tables.setdefault(tb, {})
        history = list(table_body.get(key) or [])
        for row in history:
            row["current"] = False
        version = len(history) + 1
        record = {
            "value": value,
            "source": source,
            "effective_date": effective_date or _today(),
            "recorded_at": _now(),
            "version": version,
            "current": True,
            "trigger": trigger,
        }
        history.append(record)
        table_body[key] = history
        _save_company(t, body)
    return {
        "ok": True,
        "ticker": t,
        "table": tb,
        "field": fld,
        "period": period,
        "version": version,
        "recorded_at": record["recorded_at"],
    }


def get_field_history(
    ticker: str, table: str, field: str, *, period: str | None = None
) -> list[dict[str, Any]]:
    t = str(ticker or "").strip().upper()
    tb = str(table or "").strip().lower()
    key = _fact_key(tb, field, period)
    body = _load_company(t)
    return list((body.get("tables") or {}).get(tb, {}).get(key) or [])


def get_table(ticker: str, table: str, *, period: str | None = None) -> dict[str, Any]:
    """Return the CURRENT row(s) for a table.

    Non-period tables: one row of {field: {value, source, effective_date, ...}}.
    Period tables: if `period` given, one row for that period; else a list of
    rows across all periods that have data (never invents periods).
    """
    t = str(ticker or "").strip().upper()
    tb = str(table or "").strip().lower()
    meta = TABLE_DEFS.get(tb) or {}
    if not meta:
        return {"ok": False, "error": "unknown_table", "table": table}
    fields = table_fields(tb)
    body = _load_company(t)
    table_body = (body.get("tables") or {}).get(tb, {})

    def _current(history: list[dict[str, Any]]) -> dict[str, Any] | None:
        for row in reversed(history):
            if row.get("current"):
                return row
        return history[-1] if history else None

    if not meta.get("keyed_by_period"):
        row: dict[str, Any] = {}
        missing: list[str] = []
        for f in fields:
            hist = table_body.get(f) or []
            cur = _current(hist)
            if cur is None:
                row[f] = None
                missing.append(f)
            else:
                row[f] = {
                    "value": cur.get("value"),
                    "source": cur.get("source"),
                    "effective_date": cur.get("effective_date"),
                    "version": cur.get("version"),
                }
        return {
            "ok": True,
            "ticker": t,
            "table": tb,
            "label": meta.get("label"),
            "row": row,
            "missing_fields": missing,
            "populated_fields": [f for f in fields if f not in missing],
            "coverage_pct": round(100.0 * (len(fields) - len(missing)) / max(1, len(fields)), 1),
        }

    # keyed_by_period
    periods: dict[str, dict[str, Any]] = {}
    for key, hist in table_body.items():
        if "::" not in key:
            continue
        p, f = key.split("::", 1)
        if f not in fields:
            continue
        cur = _current(hist)
        if cur is None:
            continue
        periods.setdefault(p, {"period": p})[f] = {
            "value": cur.get("value"),
            "source": cur.get("source"),
            "effective_date": cur.get("effective_date"),
            "version": cur.get("version"),
        }
    rows = sorted(periods.values(), key=lambda r: str(r.get("period")))
    if period is not None:
        match = next((r for r in rows if r.get("period") == str(period)), None)
        return {
            "ok": True,
            "ticker": t,
            "table": tb,
            "label": meta.get("label"),
            "period": period,
            "row": match or {},
            "found": bool(match),
        }
    return {
        "ok": True,
        "ticker": t,
        "table": tb,
        "label": meta.get("label"),
        "rows": rows,
        "period_count": len(rows),
    }


def list_companies() -> list[str]:
    root = store_root() / "facts"
    if not root.exists():
        return []
    return sorted(p.stem for p in root.glob("*.json"))


def company_record(ticker: str) -> dict[str, Any]:
    t = str(ticker or "").strip().upper()
    body = _load_company(t)
    tables_out: dict[str, Any] = {}
    for tb in TABLE_DEFS:
        if tb in (body.get("tables") or {}):
            tables_out[tb] = get_table(t, tb)
    return {
        "ok": True,
        "ticker": t,
        "populated_tables": list(tables_out.keys()),
        "total_tables": len(TABLE_DEFS),
        "tables": tables_out,
        "updated_at": body.get("updated_at"),
    }


def delete_company(ticker: str) -> None:
    """Test helper — remove all IKT facts for a ticker."""
    p = _company_path(ticker)
    if p.exists():
        try:
            p.unlink()
        except Exception:
            pass
