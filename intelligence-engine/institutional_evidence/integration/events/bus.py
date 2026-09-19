"""CGL Event Integration — immutable events from every successful CGL cycle."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema import CGL_EVENT_TYPES

EVENT_TYPES = CGL_EVENT_TYPES

_EVENTS: List[Dict[str, Any]] = []


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def emit_cgl_events(
    cgl_run: Dict[str, Any],
    *,
    companies_updated: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Derive immutable events from a CGL run result."""
    run_id = str(cgl_run.get("run_id") or f"cgl_{uuid.uuid4().hex[:10]}")
    slot = str(cgl_run.get("slot") or "unknown")
    companies = [str(t).upper() for t in (companies_updated or [])]
    volumes = cgl_run.get("volumes") or {}
    emitted: List[Dict[str, Any]] = []

    base = {
        "run_id": run_id,
        "slot": slot,
        "timestamp": _now(),
        "immutable": True,
        "source": "continuous_gather_learn",
    }

    def _emit(event_type: str, **extra: Any) -> None:
        if event_type not in CGL_EVENT_TYPES:
            return
        ev = {
            "event_id": f"evt_{uuid.uuid4().hex[:16]}",
            "event_type": event_type,
            **base,
            **extra,
        }
        _EVENTS.append(ev)
        emitted.append(ev)

    if cgl_run.get("ok"):
        _emit(
            "KnowledgeCollected",
            companies=companies,
            volumes=volumes,
        )

    if int(volumes.get("knowledge_extracts") or 0) > 0 or int(
        volumes.get("backfill_extracts") or 0
    ) > 0:
        _emit("FinancialStatementsUpdated", companies=companies)

    # Infer document-class events from phases/volumes when present
    phases = cgl_run.get("phases") or []
    phase_names = {
        str(p.get("name") or p.get("phase") or "").lower()
        for p in phases
        if isinstance(p, dict)
    }
    if any("annual" in n or "report" in n for n in phase_names):
        _emit("AnnualReportDownloaded", companies=companies)
    if any("transcript" in n for n in phase_names):
        _emit("TranscriptAvailable", companies=companies)
    if any("corporate" in n or "action" in n for n in phase_names):
        _emit("CorporateActionDetected", companies=companies)
    if any("sharehold" in n for n in phase_names):
        _emit("ShareholdingUpdated", companies=companies)
    if any("macro" in n for n in phase_names):
        _emit("MacroSeriesUpdated", companies=companies)
    if any("forecast" in n or "calibrat" in n for n in phase_names):
        _emit("ForecastCalibrated", companies=companies)

    # Always emit at least KnowledgeCollected on ok; if thin run, still signal collect
    if not emitted and cgl_run.get("ok"):
        _emit("KnowledgeCollected", companies=companies, volumes=volumes)

    if emitted:
        try:
            from ..persist import append_events

            append_events(emitted)
        except Exception:
            pass

    return emitted


def list_events(*, limit: int = 100, event_type: Optional[str] = None) -> Dict[str, Any]:
    rows = list(_EVENTS)
    if event_type:
        rows = [e for e in rows if e.get("event_type") == event_type]
    rows = rows[-max(1, min(limit, 500)) :]
    if not rows:
        try:
            from ..persist import list_events as disk_list

            rows = disk_list(limit=limit, event_type=event_type)
        except Exception:
            rows = []
    return {
        "ok": True,
        "count": len(rows),
        "events": rows,
        "event_types": list(CGL_EVENT_TYPES),
        "rule": "Every event is immutable",
    }
