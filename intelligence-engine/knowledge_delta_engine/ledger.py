"""Event ledger — append significant memory changes; never lose history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from knowledge_delta_engine.util import deep_get


def _now_date() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _significant_events(memory_delta: dict[str, Any], next_memory: dict[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    as_of = _now_date()
    sections = memory_delta.get("sections") or {}

    # Financial results style
    fin = sections.get("financial") or {}
    if fin.get("changed"):
        events.append(
            {
                "date": as_of,
                "type": "financial_update",
                "title": "Financial memory updated",
                "detail": ", ".join(
                    f"{c.get('field')} {c.get('before')}→{c.get('after')}" for c in (fin.get("changes") or [])[:4]
                ),
                "source": "knowledge_delta_engine",
            }
        )

    own = sections.get("ownership") or {}
    for ch in own.get("changes") or []:
        if ch.get("field") in {"promoter", "fii", "dii", "mutual_funds"} and ch.get("delta_type") == "UPDATED":
            direction = "increased" if (
                isinstance(ch.get("before"), (int, float))
                and isinstance(ch.get("after"), (int, float))
                and ch["after"] > ch["before"]
            ) else "changed"
            events.append(
                {
                    "date": as_of,
                    "type": "ownership_change",
                    "title": f"{str(ch.get('field')).upper()} holding {direction}",
                    "detail": f"{ch.get('before')} → {ch.get('after')}",
                    "source": "knowledge_delta_engine",
                }
            )

    val = sections.get("valuation") or {}
    if val.get("changed"):
        events.append(
            {
                "date": as_of,
                "type": "valuation_update",
                "title": "Valuation memory updated",
                "detail": (next_memory.get("valuation_history") or {}).get("stance"),
                "source": "knowledge_delta_engine",
            }
        )

    corp = sections.get("corporate") or {}
    if corp.get("changed"):
        obs = (next_memory.get("corporate_history") or {}).get("observations") or []
        events.append(
            {
                "date": as_of,
                "type": "strategy_update",
                "title": "Strategy / corporate themes updated",
                "detail": "; ".join(str(x) for x in obs[-2:]),
                "source": "knowledge_delta_engine",
            }
        )

    # Surface latest filing milestone from event timeline if n increased
    ev = sections.get("events") or {}
    if ev.get("changed"):
        n = deep_get(next_memory, "event_timeline.n")
        events.append(
            {
                "date": as_of,
                "type": "event_ledger_growth",
                "title": f"Event timeline now {n} items",
                "detail": None,
                "source": "knowledge_delta_engine",
            }
        )

    return events


def append_ledger(entity: str, memory_delta: dict[str, Any], next_memory: dict[str, Any]) -> dict[str, Any]:
    """Append significant deltas to HD timeline series (append-only)."""
    entity = entity.upper()
    new_events = _significant_events(memory_delta, next_memory)
    if not new_events or memory_delta.get("status") == "UNCHANGED":
        return {"written": 0, "entity": entity, "skipped": True}

    try:
        from knowledge_factory.historical_depth import store as hd_store
        from knowledge_factory.historical_depth.schema import timeline_event

        pits = []
        for e in new_events:
            pits.append(
                timeline_event(
                    entity=entity,
                    date=str(e.get("date") or _now_date()),
                    event_type=str(e.get("type") or "memory_delta"),
                    title=str(e.get("title") or "Memory change"),
                    source=str(e.get("source") or "knowledge_delta_engine"),
                    evidence=str(e.get("detail") or e.get("title") or ""),
                    confidence=0.85,
                )
            )
        hd_store.put_series("timeline", entity, pits)

        # Also maintain a dedicated delta ledger object (append)
        ledger = hd_store.get_object("memory_event_ledger", entity) or {
            "entity": entity,
            "kind": "memory_event_ledger",
            "events": [],
        }
        events = list(ledger.get("events") or [])
        events.extend(new_events)
        ledger["events"] = events[-500:]
        ledger["updated_at"] = datetime.now(timezone.utc).isoformat()
        hd_store.put_object("memory_event_ledger", entity, ledger)
        return {"written": len(new_events), "entity": entity, "events": new_events}
    except Exception as exc:  # noqa: BLE001
        return {"written": 0, "entity": entity, "error": str(exc)[:160]}


def load_ledger(entity: str) -> dict[str, Any]:
    try:
        from knowledge_factory.historical_depth import store as hd_store

        return hd_store.get_object("memory_event_ledger", entity.upper()) or {
            "entity": entity.upper(),
            "events": [],
            "found": False,
        }
    except Exception:
        return {"entity": entity.upper(), "events": [], "found": False}
