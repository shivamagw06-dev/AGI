"""Shared helpers for Valuation Analyst — no engine calls."""

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
        elif isinstance(p, dict):
            chunks.extend(as_list(list(p.values()), limit=12))
        else:
            s = txt(p)
            if s:
                chunks.append(s)
    return " ".join(chunks).lower()


def parse_num(v: Any) -> float | None:
    if v is None or v == "" or v == "n/a":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("%", "").replace("x", "")
    try:
        return float(s)
    except Exception:
        return None
