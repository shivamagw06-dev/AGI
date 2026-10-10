"""Research Lifecycle — living object, not a static document.

Draft → Analyst Review → Published → Evidence Changes → Marked Stale
→ Auto Refresh → Republished
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..schema import RESEARCH_LIFECYCLE_STATES

_STORE: Dict[str, Dict[str, Any]] = {}
_BY_TICKER: Dict[str, List[str]] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def create_research_object(
    ticker: str,
    *,
    entity_id: str = "",
    title: str = "",
    state: str = "draft",
) -> Dict[str, Any]:
    rid = f"res_{uuid.uuid4().hex[:14]}"
    st = state if state in RESEARCH_LIFECYCLE_STATES else "draft"
    obj = {
        "research_id": rid,
        "ticker": ticker.upper(),
        "entity_id": entity_id,
        "title": title or f"{ticker.upper()} institutional research",
        "state": st,
        "history": [{"state": st, "at": _now(), "note": "created"}],
        "stale": False,
        "version": 1,
        "schema": "ResearchLifecycleObject.v1",
    }
    _STORE[rid] = obj
    _BY_TICKER.setdefault(ticker.upper(), []).append(rid)
    return dict(obj)


_TRANSITIONS = {
    "draft": {"analyst_review", "published"},
    "analyst_review": {"published", "draft"},
    "published": {"evidence_changed", "marked_stale"},
    "evidence_changed": {"marked_stale", "auto_refresh"},
    "marked_stale": {"auto_refresh"},
    "auto_refresh": {"republished", "analyst_review"},
    "republished": {"evidence_changed", "marked_stale"},
}


def transition_research(
    research_id: str,
    new_state: str,
    *,
    note: str = "",
) -> Dict[str, Any]:
    obj = _STORE.get(research_id)
    if not obj:
        return {"ok": False, "error": "research_not_found"}
    cur = obj["state"]
    nxt = str(new_state)
    if nxt not in RESEARCH_LIFECYCLE_STATES:
        return {"ok": False, "error": f"invalid_state:{nxt}"}
    allowed = _TRANSITIONS.get(cur, set())
    if nxt not in allowed and nxt != cur:
        return {
            "ok": False,
            "error": f"illegal_transition:{cur}->{nxt}",
            "allowed": sorted(allowed),
        }
    obj["state"] = nxt
    obj["stale"] = nxt in {"marked_stale", "evidence_changed"}
    if nxt in {"republished", "auto_refresh"}:
        obj["version"] = int(obj.get("version") or 1) + (1 if nxt == "republished" else 0)
    obj["history"].append({"state": nxt, "at": _now(), "note": note})
    _STORE[research_id] = obj
    return {"ok": True, "research": dict(obj)}


def mark_stale_for_ticker(ticker: str, *, reason: str = "") -> Dict[str, Any]:
    t = ticker.upper()
    updated = []
    for rid in _BY_TICKER.get(t, []):
        obj = _STORE.get(rid)
        if not obj:
            continue
        if obj.get("state") == "published":
            transition_research(rid, "evidence_changed", note=reason)
            transition_research(rid, "marked_stale", note=reason)
            updated.append(rid)
        elif obj.get("state") in {"republished"}:
            transition_research(rid, "evidence_changed", note=reason)
            transition_research(rid, "marked_stale", note=reason)
            updated.append(rid)
    return {"ok": True, "ticker": t, "marked_stale": updated, "reason": reason}


def get_research_lifecycle(ticker: str) -> Dict[str, Any]:
    t = ticker.upper()
    items = [dict(_STORE[rid]) for rid in _BY_TICKER.get(t, []) if rid in _STORE]
    return {
        "ok": True,
        "ticker": t,
        "states": list(RESEARCH_LIFECYCLE_STATES),
        "objects": items,
        "count": len(items),
        "rule": "Institutional research should evolve with new evidence",
    }
