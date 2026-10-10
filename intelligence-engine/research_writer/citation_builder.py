"""Citation builder — institutional evidence references without provider/engine names."""

from __future__ import annotations

from typing import Any

from research_writer.language_quality import scrub_leaks


def build_citations(opinions: dict[str, dict[str, Any]], *, limit: int = 12) -> list[dict[str, str]]:
    cites: list[dict[str, str]] = []
    for role, op in (opinions or {}).items():
        if not isinstance(op, dict):
            continue
        analyst = scrub_leaks(op.get("analyst") or role.replace("_", " ").title(), limit=80)
        for ev in list(op.get("evidence") or [])[:2]:
            text = scrub_leaks(ev, limit=180)
            if not text:
                continue
            cites.append(
                {
                    "source": analyst,
                    "note": text,
                    "role": role,
                }
            )
            if len(cites) >= limit:
                return cites
    return cites
