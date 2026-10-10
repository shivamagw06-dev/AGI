"""Question parser — extract candidate entity mentions."""

from __future__ import annotations

import re
from typing import Any

from entity_resolution.alias_dictionary import normalize_alias
from entity_resolution.entity_registry import all_entities
from entity_resolution.entity_registry.seed import AMBIGUOUS_STEMS

_STOP = {
    "should",
    "i",
    "buy",
    "sell",
    "add",
    "the",
    "a",
    "an",
    "is",
    "are",
    "what",
    "where",
    "when",
    "why",
    "how",
    "vs",
    "versus",
    "compare",
    "with",
    "and",
    "or",
    "to",
    "for",
    "of",
    "in",
    "on",
    "my",
    "me",
    "today",
    "best",
    "high",
    "low",
    "explain",
    "analyse",
    "analyze",
    "summarise",
    "summarize",
}


def parse_mentions(question: str) -> list[dict[str, Any]]:
    """Find alias spans in the question, longest-first."""
    q = normalize_alias(question)
    if not q:
        return []

    # Build searchable alias list from registry
    aliases: list[tuple[str, str]] = []  # (alias, entity_id)
    for ent in all_entities():
        cands = [str(ent.get("canonical_name") or "").lower(), str(ent.get("ticker") or "").lower()]
        cands.extend(str(a).lower() for a in (ent.get("aliases") or []))
        for a in cands:
            a = a.strip()
            if a and a not in _STOP:
                aliases.append((a, ent["id"]))
    for stem in AMBIGUOUS_STEMS:
        aliases.append((stem, f"AMBIG::{stem}"))

    aliases = sorted(set(aliases), key=lambda x: len(x[0]), reverse=True)
    mentions: list[dict[str, Any]] = []
    covered = [False] * (len(q) + 1)

    for alias, eid in aliases:
        # word-boundary search
        if len(alias) <= 2:
            pat = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        else:
            pat = rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])"
        for m in re.finditer(pat, q):
            start, end = m.start(), m.end()
            if any(covered[start:end]):
                continue
            for i in range(start, end):
                covered[i] = True
            mentions.append(
                {
                    "text": m.group(0),
                    "alias": alias,
                    "start": start,
                    "end": end,
                    "registry_hint": eid,
                    "ambiguous_stem": alias if alias in AMBIGUOUS_STEMS else None,
                }
            )

    mentions.sort(key=lambda x: x["start"])
    return mentions
