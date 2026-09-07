"""Citation binding — section → evidence IDs → documents / replay."""

from __future__ import annotations

from typing import Any

from institutional_communication.styles.institutional import bullet


def render_sources_section(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    citations = institutional_answer.get("citations") or {}
    flat = list(citations.get("flat") or [])
    ev_items = list(((institutional_answer.get("evidence") or {}).get("items") or []))
    lines: list[str] = []
    if flat:
        for row in flat[:15]:
            lines.append(
                bullet(
                    f"{row.get('evidence_id')}: source={row.get('source')}; "
                    f"doc={row.get('document_id')}; object={row.get('knowledge_object')}; "
                    f"replay={row.get('replay_id')}; as_of={row.get('as_of')}"
                )
            )
    else:
        for item in ev_items[:12]:
            lines.append(
                bullet(
                    f"{item.get('evidence_id')}: source={item.get('source')}; "
                    f"doc={item.get('document_id')}; type={item.get('evidence_type')}"
                )
            )
    if not lines:
        lines.append(bullet("No citation rows available on the InstitutionalAnswer object."))

    replay = institutional_answer.get("replay") or {}
    if replay.get("retrieval_id"):
        lines.append(bullet(f"Retrieval / replay id: {replay.get('retrieval_id')}"))

    return {
        "section": "sources",
        "title": "Sources",
        "bullets": lines,
        "citation_count": len(flat) or len(ev_items),
        "visible": True,
    }
