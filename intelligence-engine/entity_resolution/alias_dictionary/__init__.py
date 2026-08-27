"""Alias dictionary — ticker / name / abbreviation / common forms."""

from __future__ import annotations

import re
from typing import Any

from entity_resolution.entity_registry import lookup_alias, registry_stats


def normalize_alias(text: str) -> str:
    t = (text or "").lower().strip()
    t = t.replace("&", " and ")
    t = re.sub(r"[^a-z0-9./\s:-]+", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def expand_candidates(token: str) -> list[dict[str, Any]]:
    """Return registry entities matching an alias token."""
    norm = normalize_alias(token)
    if not norm:
        return []
    hits = lookup_alias(norm)
    if hits:
        return hits
    # strip corporate suffixes
    for suf in (" limited", " ltd", " ltd.", " inc", " corporation", " company"):
        if norm.endswith(suf):
            hits = lookup_alias(norm[: -len(suf)].strip())
            if hits:
                return hits
    return []


def dictionary_health() -> dict[str, Any]:
    return {"ok": True, **registry_stats()}
