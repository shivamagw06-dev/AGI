"""Event Timeline — structured ledger from corporate actions + HD timeline."""

from __future__ import annotations

from typing import Any


def derive_event_timeline(entity: str, *, earnings_pack: dict[str, Any] | None = None) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    try:
        from knowledge_factory.historical_depth import store as hd_store

        for kind in ("timeline", "corporate_actions"):
            series = hd_store.get_series(kind, entity) or {}
            for r in series.get("records") or []:
                payload = r.get("payload") or {}
                events.append(
                    {
                        "date": str(r.get("period_end") or r.get("date") or r.get("period") or "")[:10],
                        "type": r.get("type") or payload.get("type") or kind,
                        "title": r.get("title") or payload.get("title") or payload.get("action") or kind,
                        "source": r.get("source") or kind,
                        "evidence": payload.get("evidence") or payload.get("description"),
                        "confidence": r.get("confidence"),
                    }
                )
    except Exception:
        pass

    # Soft: earnings period ends as filing milestones
    if isinstance(earnings_pack, dict):
        for row in (earnings_pack.get("annual_history") or [])[:8]:
            pe = row.get("period_end")
            if pe:
                events.append(
                    {
                        "date": str(pe)[:10],
                        "type": "financial_result",
                        "title": f"Annual results {row.get('fiscal_year_label') or pe}",
                        "source": "earnings_intelligence",
                        "evidence": "annual_filing",
                        "confidence": 0.9,
                    }
                )

    # Deduplicate by date+title
    seen: set[str] = set()
    uniq: list[dict[str, Any]] = []
    for e in sorted(events, key=lambda x: x.get("date") or ""):
        key = f"{e.get('date')}|{e.get('title')}"
        if key in seen or not e.get("date"):
            continue
        seen.add(key)
        uniq.append(e)

    # Year buckets for strategic narrative
    by_year: dict[str, list[dict[str, Any]]] = {}
    for e in uniq:
        y = str(e["date"])[:4]
        by_year.setdefault(y, []).append(e)

    return {
        "available": bool(uniq),
        "entity": entity,
        "events": uniq[-80:],
        "by_year": {y: rows[:12] for y, rows in sorted(by_year.items())},
        "n": len(uniq),
        "lineage": [{"source": "historical_depth.timeline|corporate_actions|earnings", "n": len(uniq)}],
    }
