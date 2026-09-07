"""Shared helpers for Autonomous Research Office."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def as_float(v: Any) -> float | None:
    if v is None or isinstance(v, bool):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def priority_rank(p: str | None) -> int:
    order = ("Critical", "High", "Medium", "Low", "Monitor")
    try:
        return order.index(p or "Monitor")
    except ValueError:
        return len(order)


def resolve_ticker(ticker: str) -> str:
    try:
        from company_memory.resolve import resolve_ticker as _r

        return _r(ticker)
    except Exception:
        key = (ticker or "").upper().replace(".NS", "").replace(".BO", "").strip()
        return {"TATAMOTORS": "TMPV", "ZOMATO": "ETERNAL"}.get(key, key)


def soft_call(label: str, fn, *args, **kwargs) -> dict[str, Any]:
    try:
        out = fn(*args, **kwargs)
        if isinstance(out, dict):
            return {**out, "_soft": label, "_ok": True}
        return {"_soft": label, "_ok": True, "value": out}
    except Exception as exc:  # noqa: BLE001
        return {"_soft": label, "_ok": False, "error": f"{type(exc).__name__}:{str(exc)[:120]}"}


def oie_of(pack: dict[str, Any]) -> dict[str, Any]:
    return pack.get("opportunity") if isinstance(pack.get("opportunity"), dict) else {}


def delta_of(pack: dict[str, Any]) -> dict[str, Any]:
    oie = oie_of(pack)
    if isinstance(oie.get("opportunity"), dict):
        kd = oie["opportunity"].get("knowledge_delta")
        if isinstance(kd, dict):
            return kd
    if isinstance(pack.get("memory_delta"), dict):
        return pack["memory_delta"]
    mem = pack.get("memory") if isinstance(pack.get("memory"), dict) else {}
    if isinstance(mem.get("memory_delta"), dict):
        return mem["memory_delta"]
    return {}
