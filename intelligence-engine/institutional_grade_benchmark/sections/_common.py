"""Shared section result helper."""

from __future__ import annotations

from typing import Any, Optional


def section_result(
    *,
    code: str,
    key: str,
    title: str,
    score: float,
    max_score: float,
    detail: str = "",
    items: Optional[list[dict[str, Any]]] = None,
    requires_human: bool = False,
    harness_estimate: bool = False,
    meta: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    sc = max(0.0, min(float(max_score), float(score)))
    return {
        "code": code,
        "key": key,
        "title": title,
        "score": round(sc, 2),
        "max": float(max_score),
        "pct": round(100.0 * sc / max_score, 2) if max_score else 0.0,
        "detail": detail,
        "items": list(items or []),
        "requires_human": bool(requires_human),
        "harness_estimate": bool(harness_estimate),
        "meta": dict(meta or {}),
    }
