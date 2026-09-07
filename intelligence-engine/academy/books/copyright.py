"""Copyright hygiene — never store long verbatim book text."""

from __future__ import annotations

import re

from academy.books.schema import (
    MAX_DEFINITION_CHARS,
    MAX_EXAMPLE_CHARS,
    MAX_EXPLANATION_CHARS,
    MAX_VERBATIM_REJECT,
)


_WS = re.compile(r"\s+")


def scrub(text: str | None, *, limit: int = MAX_EXPLANATION_CHARS) -> str:
    """Normalise and hard-truncate. Rejects oversized spans entirely when asked."""
    if not text:
        return ""
    s = _WS.sub(" ", str(text)).strip()
    if len(s) > MAX_VERBATIM_REJECT:
        # Do not keep long copyrighted passages — keep a short AGI paraphrase stub
        s = s[: max(80, limit // 2)].rstrip() + "…"
    if len(s) > limit:
        s = s[: limit - 1].rstrip() + "…"
    return s


def scrub_definition(text: str | None) -> str:
    return scrub(text, limit=MAX_DEFINITION_CHARS)


def scrub_explanation(text: str | None) -> str:
    return scrub(text, limit=MAX_EXPLANATION_CHARS)


def scrub_example(text: str | None) -> str:
    return scrub(text, limit=MAX_EXAMPLE_CHARS)


def assert_no_long_verbatim(payload: dict) -> list[str]:
    """Quality gate helper — flag any string field over reject threshold."""
    bad: list[str] = []

    def walk(obj, path: str) -> None:
        if isinstance(obj, dict):
            for k, v in obj.items():
                walk(v, f"{path}.{k}" if path else str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj[:50]):
                walk(v, f"{path}[{i}]")
        elif isinstance(obj, str) and len(obj) > MAX_VERBATIM_REJECT:
            bad.append(path)

    walk(payload, "")
    return bad
