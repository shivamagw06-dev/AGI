"""Shared text helpers for Business Analyst V2 — no engine calls."""

from __future__ import annotations

from typing import Any


def txt(v: Any) -> str:
    return str(v or "").strip()


def as_list(v: Any, *, limit: int = 6) -> list[str]:
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    out: list[str] = []
    for item in v:
        s = txt(item)
        if s and s not in out:
            out.append(s)
        if len(out) >= limit:
            break
    return out


def blob_of(*parts: Any) -> str:
    chunks: list[str] = []
    for p in parts:
        if isinstance(p, (list, tuple)):
            chunks.extend(as_list(p, limit=12))
        else:
            s = txt(p)
            if s:
                chunks.append(s)
    return " ".join(chunks).lower()


def rate_from_signals(hits: int, *, improving: bool = False, declining: bool = False) -> str:
    if declining:
        return "Declining"
    if hits >= 3:
        return "Improving" if improving else "Strong"
    if hits == 2:
        return "Improving" if improving else "Medium"
    if hits == 1:
        return "Weak"
    return "Weak"
