"""Section / evidence / timeline search over an assembled workspace."""

from __future__ import annotations

from typing import Any, Mapping, Optional


def _match(text: str, q: str) -> bool:
    return q.lower() in (text or "").lower()


def search_workspace(
    workspace: Mapping[str, Any],
    query: str,
    *,
    scope: str = "all",
) -> dict[str, Any]:
    """Filter sections, evidence blocks, and timeline events by query string."""
    q = str(query or "").strip()
    scope_l = (scope or "all").strip().lower()
    if not q:
        return {
            "ok": True,
            "query": q,
            "scope": scope_l,
            "sections": list(workspace.get("sections") or []),
            "evidence": [],
            "timeline": (workspace.get("payload") or {}).get("timeline") or [],
        }

    sections_out: list[dict[str, Any]] = []
    evidence_out: list[dict[str, Any]] = []
    for sec in workspace.get("sections") or []:
        if not isinstance(sec, Mapping):
            continue
        key = str(sec.get("key") or "")
        title = str(sec.get("title") or "")
        sec_hit = _match(key, q) or _match(title, q)
        block_hits = []
        for b in sec.get("blocks") or []:
            if not isinstance(b, Mapping):
                continue
            text = str(b.get("text") or "")
            eids = " ".join(str(x) for x in (b.get("evidence_ids") or []))
            if _match(text, q) or _match(eids, q) or _match(str(b.get("module") or ""), q):
                block_hits.append(dict(b))
                evidence_out.append({"section": key, **dict(b)})
        if scope_l in {"all", "section", "sections"} and (sec_hit or block_hits):
            sections_out.append(dict(sec))
        elif scope_l in {"evidence"} and block_hits:
            sections_out.append({**dict(sec), "blocks": block_hits})

    timeline = (workspace.get("payload") or {}).get("timeline") or []
    timeline_out: list[dict[str, Any]] = []
    if scope_l in {"all", "timeline"}:
        for ev in timeline:
            if not isinstance(ev, Mapping):
                continue
            blob = " ".join(
                [
                    str(ev.get("event_type") or ""),
                    str(ev.get("summary") or ""),
                    str(ev.get("source") or ""),
                ]
            )
            if _match(blob, q):
                timeline_out.append(dict(ev))

    return {
        "ok": True,
        "query": q,
        "scope": scope_l,
        "sections": sections_out,
        "evidence": evidence_out if scope_l in {"all", "evidence"} else [],
        "timeline": timeline_out,
        "counts": {
            "sections": len(sections_out),
            "evidence": len(evidence_out),
            "timeline": len(timeline_out),
        },
    }


def filter_timeline(
    events: list[Mapping[str, Any]],
    *,
    event_type: Optional[str] = None,
    source: Optional[str] = None,
    query: Optional[str] = None,
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    et = (event_type or "").strip().lower()
    src = (source or "").strip().lower()
    q = (query or "").strip().lower()
    for ev in events or []:
        if not isinstance(ev, Mapping):
            continue
        if et and et not in str(ev.get("event_type") or "").lower():
            continue
        if src and src not in str(ev.get("source") or "").lower():
            continue
        if q:
            blob = f"{ev.get('event_type')} {ev.get('summary')} {ev.get('source')}".lower()
            if q not in blob:
                continue
        out.append(dict(ev))
    out.sort(key=lambda r: str(r.get("at") or ""))
    return out
