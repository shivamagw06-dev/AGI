"""Shared helpers for delta detection."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def deep_get(obj: Any, path: str) -> Any:
    cur = obj
    for part in path.split("."):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(part)
    return cur


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, default=str, separators=(",", ":"))


def checksum(obj: Any) -> str:
    return hashlib.sha256(canonical_json(obj).encode("utf-8")).hexdigest()[:16]


def memory_fingerprint(memory: dict[str, Any]) -> str:
    """Stable fingerprint excluding volatile compile metadata."""
    slim = {
        k: memory.get(k)
        for k in (
            "entity",
            "financial_history",
            "ownership_history",
            "valuation_history",
            "corporate_history",
            "sector_history",
            "price_intelligence",
            "risk_history",
            "event_timeline",
            "business_model",
            "competitive_position",
        )
        if k in memory
    }
    # Drop latency / compiled_at noise from nested latest_evidence freshness if present
    return checksum(slim)


def approx_equal(a: Any, b: Any, *, rel: float = 1e-6, abs_tol: float = 1e-9) -> bool:
    if a is None and b is None:
        return True
    if type(a) != type(b) and not (isinstance(a, (int, float)) and isinstance(b, (int, float))):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == b:
            return True
        scale = max(abs(float(a)), abs(float(b)), 1.0)
        return abs(float(a) - float(b)) <= max(abs_tol, rel * scale)
    if isinstance(a, (list, dict)):
        return canonical_json(a) == canonical_json(b)
    return a == b
