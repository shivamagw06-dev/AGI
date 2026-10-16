"""Shared text helpers for Financial Analyst — no engine calls."""

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


def parse_num(v: Any) -> float | None:
    if v is None or v == "" or v == "n/a":
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "").replace("%", "")
    try:
        return float(s)
    except Exception:
        return None


def trend_label(text: str, *, score: float | None = None) -> str:
    t = (text or "").lower()
    if any(k in t for k in ("deterior", "weaken", "declin", "pressure", "stress")):
        return "Weakening"
    if any(k in t for k in ("accelerat",)):
        return "Accelerating"
    if any(k in t for k in ("decelerat", "slow")):
        return "Decelerating"
    if any(k in t for k in ("improv", "expand", "strengthen", "strong")):
        return "Improving"
    if score is not None:
        if score >= 70:
            return "Improving"
        if score < 45:
            return "Weakening"
    return "Stable"
