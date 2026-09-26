"""Institutional style helpers — short, evidence-first, no filler."""

from __future__ import annotations

import re

_FILLER = re.compile(
    r"\b(delve|landscape|robust|seamless|cutting[- ]edge|game[- ]changer|leverage synergies)\b",
    re.I,
)


def clean_line(text: str, *, max_len: int = 280) -> str:
    t = " ".join(str(text or "").split())
    t = _FILLER.sub("", t)
    t = re.sub(r"\s{2,}", " ", t).strip(" -;")
    if len(t) > max_len:
        t = t[: max_len - 1].rstrip() + "…"
    return t


def bullet(text: str) -> str:
    line = clean_line(text)
    if not line:
        return ""
    if not line.startswith("-"):
        return f"- {line}"
    return line
