"""Render Framework Explanation Object — never hide selection."""

from __future__ import annotations

from typing import Any

from institutional_communication.styles.institutional import bullet, clean_line


def render_framework_section(institutional_answer: dict[str, Any]) -> dict[str, Any]:
    fw = institutional_answer.get("frameworks") or {}
    expl = fw.get("explanation") if isinstance(fw.get("explanation"), dict) else {}
    lines: list[str] = []

    def _names(rows: list) -> list[str]:
        out = []
        for r in rows or []:
            if isinstance(r, dict):
                out.append(str(r.get("name") or r.get("framework_id")))
            else:
                out.append(str(r))
        return out

    primary = _names(fw.get("primary") or [])
    secondary = _names(fw.get("secondary") or [])
    supporting = _names(fw.get("supporting") or [])

    if primary:
        lines.append(bullet(f"Primary: {'; '.join(primary)}"))
    if secondary:
        lines.append(bullet(f"Secondary: {'; '.join(secondary)}"))
    if supporting:
        lines.append(bullet(f"Supporting: {'; '.join(supporting)}"))

    reason = clean_line(expl.get("reason") or "", max_len=500)
    if reason:
        lines.append(bullet(f"Reason: {reason}"))
    elif fw.get("sector"):
        lines.append(
            bullet(
                f"Sector context: {fw.get('sector')}. Frameworks selected from the institutional registry."
            )
        )

    forbidden = fw.get("forbidden_rejected") or expl.get("forbidden_for_sector") or []
    if forbidden:
        lines.append(bullet(f"Excluded (forbidden for context): {', '.join(map(str, forbidden))}"))

    conf = fw.get("confidence") or expl.get("confidence") or {}
    if conf.get("band") or conf.get("pct") is not None:
        lines.append(
            bullet(
                f"Framework-selection confidence: {conf.get('band') or 'n/a'}"
                + (f" ({conf.get('pct')}%)" if conf.get("pct") is not None else "")
            )
        )

    if not lines:
        lines.append(bullet("No framework selection object available — communication incomplete."))

    return {
        "section": "framework_used",
        "title": "Framework Used",
        "bullets": [x for x in lines if x],
        "framework_ids": list(fw.get("framework_ids") or []),
        "visible": True,
    }
