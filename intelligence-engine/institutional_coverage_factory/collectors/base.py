"""Shared collector result helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def collector_result(
    collector_id: str,
    ticker: str,
    *,
    ok: bool,
    steps: Optional[List[Dict[str, Any]]] = None,
    error: Optional[str] = None,
    **extra: Any,
) -> Dict[str, Any]:
    return {
        "ok": ok,
        "collector": collector_id,
        "ticker": str(ticker or "").upper().strip(),
        "ran_at": _now(),
        "steps": list(steps or []),
        "error": error,
        **extra,
    }


def soft_step(name: str, fn) -> Dict[str, Any]:
    try:
        out = fn()
        return {"step": name, "ok": True, "result_keys": sorted((out or {}).keys())[:12] if isinstance(out, dict) else None}
    except Exception as exc:
        return {"step": name, "ok": False, "error": str(exc)[:200]}
