"""RW-01 workspace navigation + in-workspace search."""

from __future__ import annotations

from typing import Any, Sequence
from urllib.parse import quote

from institutional_workspace.models import InstitutionalWorkspace
from institutional_workspace.schema import NAVIGATION


def navigation_items(
    *,
    context: str,
    ticker: str = "",
    portfolio_id: str = "",
) -> tuple[str, ...]:
    return NAVIGATION


def ask_deep_link(*, ticker: str = "", portfolio_id: str = "", question: str = "") -> str:
    qs = []
    if question:
        qs.append(f"q={quote(question)}")
    if ticker:
        qs.append(f"ticker={quote(ticker)}")
    if portfolio_id:
        qs.append(f"context=portfolio&portfolio={quote(portfolio_id)}")
    return "/agi/ask" + (("?" + "&".join(qs)) if qs else "")


def workspace_deep_link(
    *,
    ticker: str = "",
    portfolio_id: str = "",
    focus: str = "timeline",
    context: str = "",
) -> str:
    """Ask → Workspace: open the analyst workstation focused on a section."""
    focus = (focus or "timeline").strip().lower() or "timeline"
    ctx = (context or "").strip().lower()
    if ticker:
        return f"/agi/companies/{quote(ticker.upper())}?tab={quote(focus)}&rw=1"
    if portfolio_id or ctx == "portfolio":
        pid = quote(portfolio_id or "agi-core-equity")
        return f"/agi/portfolio?portfolio={pid}&tab={quote(focus)}&rw=1"
    if ctx == "committee":
        return f"/agi/committee?tab={quote(focus)}&rw=1"
    return f"/agi/research?tab={quote(focus)}&rw=1"


def workspace_focus_for_intent(intent: str) -> str:
    """Map Ask intent to the workspace section analysts should open."""
    mapping = {
        "Committee": "committee",
        "Policy": "policy",
        "Risk": "risk",
        "Portfolio Analysis": "decisions",
        "Company Analysis": "decisions",
        "Evidence": "evidence",
        "Search": "timeline",
    }
    return mapping.get(intent or "", "timeline")


def search_workspace(workspace: InstitutionalWorkspace, query: str) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    hits: list[dict[str, Any]] = []

    for ev in workspace.timeline:
        blob = f"{ev.title} {ev.summary} {ev.kind}".lower()
        if q in blob:
            hits.append(
                {
                    "kind": "timeline",
                    "title": ev.title,
                    "object_type": ev.object_type,
                    "object_id": ev.object_id,
                    "href": next(
                        (o.href for o in workspace.linked_objects if o.object_type == ev.object_type),
                        "",
                    ),
                }
            )

    for o in workspace.linked_objects:
        if q in f"{o.label} {o.summary} {o.object_type}".lower():
            hits.append(
                {
                    "kind": "linked_object",
                    "title": o.label,
                    "object_type": o.object_type,
                    "object_id": o.object_id,
                    "href": o.href,
                }
            )

    for e in workspace.evidence:
        if q in f"{e.title} {e.snippet} {e.source_type}".lower():
            hits.append(
                {
                    "kind": "evidence",
                    "title": e.title,
                    "object_type": "Evidence",
                    "object_id": e.evidence_id,
                    "href": e.href,
                }
            )

    for n in workspace.notes:
        if q in f"{n.title} {n.body} {' '.join(n.tags)}".lower():
            hits.append(
                {
                    "kind": "note",
                    "title": n.title,
                    "object_type": "ResearchNote",
                    "object_id": n.note_id,
                    "href": f"/agi/research?note={n.note_id}",
                }
            )

    # Keyword shortcuts
    shortcuts = {
        "capital allocation": "financials",
        "ceo": "business",
        "buyback": "evidence",
        "dividend": "evidence",
        "esg": "risk",
        "risk": "risk",
    }
    for key, section in shortcuts.items():
        if key in q or q in key:
            hits.append(
                {
                    "kind": "section",
                    "title": f"Section: {section}",
                    "object_type": "Section",
                    "object_id": section,
                    "href": "",
                }
            )

    # Dedupe by title+kind
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for h in hits:
        k = f"{h['kind']}|{h['title']}"
        if k in seen:
            continue
        seen.add(k)
        unique.append(h)
    return unique[:40]
