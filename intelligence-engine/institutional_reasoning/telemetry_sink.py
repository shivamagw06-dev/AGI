"""Phase 1 — Immutable telemetry sink (Supabase append-only + local fallback).

Never raises into the answer path. Never updates existing rows.
Ask path buffers in memory and flushes Supabase/disk asynchronously.
Architecture v1.0.1 LOCKED — soft helper under institutional_reasoning.
"""

from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TABLE = "framework_execution_runs"
_LOCK = threading.Lock()
_MEMORY: list[dict[str, Any]] = []
_MEMORY_LIMIT = 500


def _fallback_path() -> Path:
    raw = (os.environ.get("KIP_DATA_DIR") or "").strip()
    base = Path(raw) if raw else Path(__file__).resolve().parents[1] / "data" / "kip"
    return base / "framework_execution_runs.jsonl"


def _supabase_client():
    url = (os.environ.get("SUPABASE_URL") or os.environ.get("VITE_SUPABASE_URL") or "").strip()
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()
    if not url or not key:
        return None
    try:
        from supabase import create_client  # type: ignore

        return create_client(url, key)
    except Exception:
        return None


def _flush_external(stamped: list[dict[str, Any]]) -> dict[str, Any]:
    """Write already-stamped rows to Supabase or disk. Does not touch memory buffer."""
    if not stamped:
        return {"ok": True, "written": 0, "sink": "noop"}

    client = _supabase_client()
    if client is not None:
        try:
            payload = [
                {k: v for k, v in row.items() if k != "recorded_at"} for row in stamped
            ]
            client.table(TABLE).insert(payload).execute()
            return {"ok": True, "written": len(payload), "sink": "supabase"}
        except Exception as exc:
            supabase_error = str(exc)[:200]
    else:
        supabase_error = "no_supabase_credentials"

    try:
        path = _fallback_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            for row in stamped:
                fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")
        return {
            "ok": True,
            "written": len(stamped),
            "sink": "disk",
            "path": str(path),
            "supabase_error": supabase_error,
        }
    except Exception as exc:
        return {
            "ok": False,
            "written": 0,
            "sink": "memory",
            "error": str(exc)[:200],
            "supabase_error": supabase_error,
        }


def persist_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Ask-safe: buffer in memory immediately, flush Supabase/disk off the request path."""
    if not rows:
        return {"ok": True, "written": 0, "sink": "noop"}

    stamped = [
        {**r, "recorded_at": datetime.now(timezone.utc).isoformat()} for r in rows
    ]
    with _LOCK:
        _MEMORY.extend(stamped)
        if len(_MEMORY) > _MEMORY_LIMIT:
            del _MEMORY[: len(_MEMORY) - _MEMORY_LIMIT]

    threading.Thread(
        target=_flush_external,
        args=(list(stamped),),
        name="telemetry-persist",
        daemon=True,
    ).start()
    return {"ok": True, "written": len(stamped), "sink": "async_buffer"}


def recent(limit: int = 50) -> list[dict[str, Any]]:
    with _LOCK:
        return list(_MEMORY[-limit:])


def health() -> dict[str, Any]:
    client = _supabase_client()
    return {
        "table": TABLE,
        "supabase_configured": client is not None,
        "fallback_path": str(_fallback_path()),
        "buffered_rows": len(_MEMORY),
        "append_only": True,
    }
