"""Bind evidence before conclusions — map to evidence IDs / docs / replay."""

from __future__ import annotations

from typing import Any

from institutional_communication.styles.institutional import bullet, clean_line


def render_evidence_section(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    ev = institutional_answer.get("evidence") or {}
    items = list(ev.get("items") or [])
    lines: list[str] = []
    bindings: list[dict[str, Any]] = []

    for item in items[:12]:
        eid = item.get("evidence_id") or "unknown"
        title = clean_line(item.get("title") or item.get("evidence_type") or eid, max_len=160)
        src = item.get("source") or "unspecified"
        doc = item.get("document_id")
        domain = item.get("domain") or item.get("evidence_type")
        bit = f"[{eid}] {title} (source={src}"
        if doc:
            bit += f"; doc={doc}"
        if domain:
            bit += f"; type={domain}"
        bit += ")"
        lines.append(bullet(bit))
        bindings.append(
            {
                "evidence_id": eid,
                "document_id": doc,
                "source": src,
                "knowledge_object": item.get("evidence_type"),
                "available_from": item.get("available_from"),
                "replay_id": (institutional_answer.get("replay") or {}).get("retrieval_id"),
            }
        )

    if not lines:
        lines.append(bullet("No ranked evidence items were available in the InstitutionalAnswer object."))

    ranked = ev.get("iere_ranked_count")
    if ranked is not None:
        lines.insert(0, bullet(f"IERE ranked evidence count: {ranked}"))

    # AGIB v3.6 — Institutional Evidence Graph relationships / domain coverage
    eg = institutional_answer.get("evidence_graph") or {}
    graph_lines: list[str] = []
    if eg.get("graph_id") or eg.get("n_nodes"):
        graph_lines.append(
            bullet(
                clean_line(
                    f"Evidence graph: {eg.get('n_nodes') or 0} nodes · "
                    f"{eg.get('n_edges') or 0} edges · "
                    f"domain coverage {eg.get('domain_coverage_pct')}%.",
                    max_len=220,
                )
            )
        )
        for b in (eg.get("surface_bullets") or [])[:6]:
            graph_lines.append(bullet(clean_line(str(b), max_len=240)))
        for b in (eg.get("chain_bullets") or [])[:4]:
            graph_lines.append(bullet(clean_line(str(b), max_len=240)))
        # Prefetch graph lines before isolated facts when ranked evidence is thin
        if ranked in (None, 0) or len(items) < 3:
            lines = graph_lines + lines
        else:
            lines = lines[:4] + graph_lines + lines[4:]

    # AGIB v3.6 Sprint 2.2 — Historical Analogues (IMAI) — only when evidence exists
    im = institutional_answer.get("institutional_memory") or {}
    memory_lines: list[str] = []
    if im.get("have_we_seen_this_before") and (im.get("surface_bullets") or im.get("memories")):
        memory_lines.append(
            bullet("Have we seen this before? — Institutional Memory & Analog Intelligence")
        )
        for b in (im.get("surface_bullets") or [])[:5]:
            memory_lines.append(bullet(clean_line(str(b), max_len=260)))
        comp = im.get("comparison") or {}
        for lesson in (comp.get("similarities") or [])[:2]:
            memory_lines.append(bullet(clean_line(f"Lesson from history: {lesson}", max_len=240)))
        if memory_lines:
            lines = lines[:6] + memory_lines + lines[6:]

    return {
        "section": "evidence",
        "title": "Evidence",
        "bullets": lines[:22],
        "bindings": bindings,
        "visible": True,
        "evidence_graph_id": eg.get("graph_id"),
        "institutional_memory_ids": im.get("top_memory_ids") or [],
    }
