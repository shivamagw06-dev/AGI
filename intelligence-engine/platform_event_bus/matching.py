"""Event type pattern matching — exact + wildcards (e.g. portfolio.*)."""

from __future__ import annotations

import re


def pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """
    Glob-style patterns over dotted event types.
    - `portfolio.*` matches `portfolio.updated`, `portfolio.snapshot.created`
    - `*` matches any event type
    - exact string matches only itself
    """
    p = (pattern or "").strip()
    if not p:
        raise ValueError("empty subscription pattern")
    if p == "*":
        return re.compile(r"^.*$")
    # Escape then replace \* wildcards segment-aware: * matches any chars including dots
    parts = []
    for ch in p:
        if ch == "*":
            parts.append(".*")
        elif ch in ".+?^${}()|[]\\":
            parts.append("\\" + ch)
        else:
            parts.append(ch)
    return re.compile("^" + "".join(parts) + "$")


def matches(pattern: str, event_type: str) -> bool:
    try:
        return bool(pattern_to_regex(pattern).match(event_type or ""))
    except ValueError:
        return False
