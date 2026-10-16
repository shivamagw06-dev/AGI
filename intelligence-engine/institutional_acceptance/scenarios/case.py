"""Acceptance case helpers."""

from __future__ import annotations

from typing import Any, Optional


def case(
    case_id: str,
    *,
    phase: str,
    name: str,
    status: str = "PASS",
    critical: bool = False,
    detail: str = "",
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    st = str(status or "PASS").upper()
    if st not in {"PASS", "FAIL", "SKIP"}:
        st = "FAIL"
    return {
        "id": case_id,
        "phase": phase,
        "name": name,
        "status": st,
        "critical": bool(critical),
        "detail": detail or "",
        "meta": dict(meta or {}),
    }


def soft_health(module: str, attr: str = "health") -> tuple[bool, dict[str, Any]]:
    try:
        mod = __import__(module, fromlist=[attr])
        fn = getattr(mod, attr, None)
        if not callable(fn):
            return False, {"error": f"missing {attr}"}
        out = fn()
        if isinstance(out, dict):
            return True, out
        return True, {"raw": out}
    except Exception as exc:  # noqa: BLE001
        return False, {"error": str(exc)}
