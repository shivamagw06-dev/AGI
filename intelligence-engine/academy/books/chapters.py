"""Chapter / section hierarchy detection — never treat a book as one blob."""

from __future__ import annotations

import re
from typing import Any

from academy.books.copyright import scrub
from academy.books.schema import ChapterNode


_HEADING_RE = re.compile(
    r"^(?:"
    r"(?:PART|Part)\s+([IVXLC\d]+)[:.\s]+(.+)"
    r"|(?:CHAPTER|Chapter)\s+(\d+)[:.\s]+(.+)"
    r"|(#{1,4})\s+(.+)"
    r"|(\d+(?:\.\d+){0,2})\s+([A-Z][^\n]{3,80})"
    r")\s*$"
)


def detect_hierarchy(book_id: str, text: str) -> list[ChapterNode]:
    lines = (text or "").splitlines()
    nodes: list[ChapterNode] = []
    current_chapter_id: str | None = None
    order = 0
    buf: list[str] = []
    pending: ChapterNode | None = None

    def flush() -> None:
        nonlocal pending, buf
        if pending is not None:
            pending.summary = scrub(" ".join(buf), limit=240)
            nodes.append(pending)
        pending = None
        buf = []

    for line in lines:
        m = _HEADING_RE.match(line.strip())
        if not m:
            if pending is not None and line.strip():
                buf.append(line.strip())
            continue
        flush()
        order += 1
        part_n, part_t, ch_n, ch_t, md_h, md_t, num, num_t = m.groups()
        if part_n:
            level, title = "part", f"Part {part_n}: {part_t.strip()}"
            parent = None
        elif ch_n:
            level, title = "chapter", f"Chapter {ch_n}: {ch_t.strip()}"
            parent = None
        elif md_h:
            hashes = len(md_h)
            title = md_t.strip()
            if hashes <= 1:
                level, parent = "chapter", None
            elif hashes == 2:
                level, parent = "section", current_chapter_id
            else:
                level, parent = "subsection", current_chapter_id
        else:
            depth = num.count(".")
            title = f"{num} {num_t.strip()}"
            if depth == 0:
                level, parent = "chapter", None
            elif depth == 1:
                level, parent = "section", current_chapter_id
            else:
                level, parent = "subsection", current_chapter_id

        node_id = f"{book_id}:n{order}"
        pending = ChapterNode(
            node_id=node_id,
            book_id=book_id,
            title=title[:160],
            level=level,
            order=order,
            parent_id=parent,
        )
        if level == "chapter":
            current_chapter_id = node_id

    flush()

    if not nodes:
        # Soft fallback — synthetic chapters by ~chunk so book is never one document
        chunks = _chunk(text, size=3500)
        for i, chunk in enumerate(chunks, start=1):
            nodes.append(
                ChapterNode(
                    node_id=f"{book_id}:ch{i}",
                    book_id=book_id,
                    title=f"Section {i}",
                    level="chapter",
                    order=i,
                    summary=scrub(chunk, limit=240),
                )
            )
    return nodes


def _chunk(text: str, *, size: int = 3500) -> list[str]:
    t = (text or "").strip()
    if not t:
        return []
    return [t[i : i + size] for i in range(0, len(t), size)][:40]


def hierarchy_stats(nodes: list[ChapterNode]) -> dict[str, Any]:
    counts = {"part": 0, "chapter": 0, "section": 0, "subsection": 0}
    for n in nodes:
        counts[n.level] = counts.get(n.level, 0) + 1
    return counts
