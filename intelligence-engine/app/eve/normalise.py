"""Fact normalisation — configurable aliases to canonical fields."""

from __future__ import annotations

import re

from app.eve.config import FACT_NORMALISATION


def _norm_key(value: str) -> str:
    s = (value or "").strip().lower()
    s = s.replace("-", "_").replace("/", "_")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def canonical_fact_key(raw_field: str, *, overrides: dict[str, str] | None = None) -> str:
    table = {**FACT_NORMALISATION, **(overrides or {})}
    key = _norm_key(raw_field)
    if key in table:
        return table[key]
    # spaced variants already normalised; try loose contains
    for alias, canon in table.items():
        if _norm_key(alias) == key:
            return canon
    return key or "unknown_fact"


def values_equivalent(a: str, b: str) -> bool:
    """Lightweight numeric/text equivalence for multi-source validation."""
    left = (a or "").strip().lower()
    right = (b or "").strip().lower()
    if not left or not right:
        return False
    if left == right:
        return True
    # strip currency / commas
    def _num(s: str) -> float | None:
        cleaned = re.sub(r"[₹$,]", "", s)
        cleaned = cleaned.replace(",", "").replace("crore", "").replace("cr", "").strip()
        m = re.search(r"-?\d+(?:\.\d+)?", cleaned)
        if not m:
            return None
        try:
            return float(m.group(0))
        except ValueError:
            return None

    na, nb = _num(left), _num(right)
    if na is not None and nb is not None:
        if na == 0 and nb == 0:
            return True
        return abs(na - nb) / max(abs(na), abs(nb), 1e-9) < 0.02
    # token overlap for qualitative facts
    ta = set(re.findall(r"[a-z0-9]{3,}", left))
    tb = set(re.findall(r"[a-z0-9]{3,}", right))
    if not ta or not tb:
        return False
    return len(ta & tb) / max(1, len(ta | tb)) >= 0.85
