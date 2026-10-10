"""Valuation metrics store — market multiples per company.

Market data (Yahoo Finance / Capital IQ) is stored separately from AGI's
interpretation. This module only holds the numbers.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

_LOCK = threading.RLock()
_CACHE: dict[str, Any] | None = None

METRIC_FIELDS: tuple[str, ...] = (
    "price",
    "market_cap",
    "pe",
    "forward_pe",
    "pb",
    "ev_ebitda",
    "ev_sales",
    "ps",
    "roe",
    "book_value",
    "eps",
    "dividend_yield",
    "profit_margin",
    "debt_to_equity",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def store_root() -> Path:
    raw = (os.getenv("VALUATION_TERMINAL_ROOT") or "").strip()
    kip = (os.getenv("KIP_DATA_DIR") or "").strip()
    if raw:
        root = Path(raw)
    elif kip:
        root = Path(kip) / "valuation_terminal"
    else:
        root = Path(__file__).resolve().parents[1] / "data" / "valuation_terminal"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path() -> Path:
    return store_root() / "metrics.json"


def invalidate_cache() -> None:
    global _CACHE
    with _LOCK:
        _CACHE = None


def load() -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        if _CACHE is not None:
            return _CACHE
        payload: dict[str, Any] = {"updated_at": None, "source": None, "rows": {}}
        path = _path()
        if path.exists():
            try:
                disk = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(disk, dict) and isinstance(disk.get("rows"), dict):
                    payload = disk
            except Exception:
                pass
        _CACHE = payload
        return payload


def save(rows: dict[str, dict[str, Any]], *, source: str) -> dict[str, Any]:
    global _CACHE
    with _LOCK:
        payload = {
            "updated_at": _now(),
            "source": source,
            "row_count": len(rows),
            "rows": rows,
        }
        tmp = _path().with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, indent=1, default=str), encoding="utf-8")
        tmp.replace(_path())
        _CACHE = payload
        return payload


def get(ticker: str) -> Optional[dict[str, Any]]:
    row = (load().get("rows") or {}).get(str(ticker or "").strip().upper())
    return dict(row) if isinstance(row, dict) else None


def all_rows() -> dict[str, dict[str, Any]]:
    return dict(load().get("rows") or {})


def health() -> dict[str, Any]:
    payload = load()
    rows = payload.get("rows") or {}
    covered = {
        field: sum(1 for r in rows.values() if r.get(field) is not None)
        for field in METRIC_FIELDS
    }
    return {
        "ok": True,
        "engine": "valuation_terminal",
        "status": "ok" if rows else "empty",
        "companies": len(rows),
        "updated_at": payload.get("updated_at"),
        "source": payload.get("source"),
        "field_coverage": covered,
    }
