"""Quality gates — one FAIL ⇒ timeline not institutionally ready."""

from __future__ import annotations

from typing import Any

from knowledge_factory.corporate_events.objects.event import event_fingerprint
from knowledge_factory.corporate_events.timeline.build import timeline_order_ok


def detect_duplicates(events: list[dict[str, Any]]) -> list[str]:
    seen: dict[str, str] = {}
    dups: list[str] = []
    for e in events:
        fp = event_fingerprint(
            company=str(e.get("company") or ""),
            event_type=str(e.get("type") or ""),
            announcement_date=str(e.get("announcement_date") or ""),
            title=str(e.get("title") or ""),
            source=str(e.get("source") or ""),
        )
        if fp in seen:
            dups.append(e.get("event_id") or fp)
        else:
            seen[fp] = str(e.get("event_id") or fp)
    return dups


def validate_event(event: dict[str, Any]) -> dict[str, Any]:
    gates: dict[str, dict[str, Any]] = {}
    ann = event.get("announcement_date")
    gates["announcement_date"] = {
        "pass": bool(ann) and str(ann) != "UNKNOWN",
        "reason": None if ann else "missing_announcement_date",
    }
    gates["source"] = {
        "pass": bool(event.get("source")),
        "reason": None if event.get("source") else "missing_source",
    }
    gates["event_type"] = {
        "pass": bool(event.get("type")),
        "reason": None if event.get("type") else "missing_event_type",
    }
    gates["provenance"] = {
        "pass": bool(event.get("provenance")),
        "reason": None if event.get("provenance") else "missing_provenance",
    }
    failed = [k for k, v in gates.items() if not v["pass"]]
    return {
        "event_id": event.get("event_id"),
        "gates": gates,
        "failed_gates": failed,
        "gate_pass": len(failed) == 0,
        "fabricated": False,
    }


def validate_timeline(timeline: dict[str, Any]) -> dict[str, Any]:
    events = list(timeline.get("events") or [])
    event_results = [validate_event(e) for e in events]
    dups = detect_duplicates(events)
    order_ok = timeline_order_ok(events)

    gates = {
        "timeline_exists": {"pass": True, "reason": None},
        "events_present": {
            "pass": len(events) > 0,
            "reason": None if events else "empty_timeline",
        },
        "announcement_dates": {
            "pass": all(r["gates"]["announcement_date"]["pass"] for r in event_results) if event_results else False,
            "reason": None if event_results and all(r["gates"]["announcement_date"]["pass"] for r in event_results) else "missing_announcement_date",
        },
        "sources": {
            "pass": all(r["gates"]["source"]["pass"] for r in event_results) if event_results else False,
            "reason": None if event_results and all(r["gates"]["source"]["pass"] for r in event_results) else "missing_source",
        },
        "event_types": {
            "pass": all(r["gates"]["event_type"]["pass"] for r in event_results) if event_results else False,
            "reason": None if event_results and all(r["gates"]["event_type"]["pass"] for r in event_results) else "missing_event_type",
        },
        "provenance": {
            "pass": all(r["gates"]["provenance"]["pass"] for r in event_results) if event_results else False,
            "reason": None if event_results and all(r["gates"]["provenance"]["pass"] for r in event_results) else "missing_provenance",
        },
        "timeline_order": {
            "pass": order_ok,
            "reason": None if order_ok else "timeline_order_broken",
        },
        "duplicates": {
            "pass": len(dups) == 0,
            "reason": None if not dups else "duplicate_event",
        },
        "validation": {"pass": True, "reason": None},
    }
    failed = [k for k, v in gates.items() if not v["pass"]]
    return {
        "ticker": timeline.get("ticker"),
        "gates": gates,
        "failed_gates": failed,
        "gate_pass": len(failed) == 0,
        "duplicate_event_ids": dups,
        "event_count": len(events),
        "institutional_ready": len(failed) == 0 and len(events) > 0,
        "fabricated": False,
    }
