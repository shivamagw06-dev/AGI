"""Universe Membership Engine — point-in-time index constituents.

Answers: As of 2025, was company inside Nifty 500?
Critical for historical replay. Soft registry only — never invents live
reconstitutions beyond fixtures + current snapshots.
"""

from __future__ import annotations

from datetime import date
from typing import Any

from universe_intelligence import store as iui_store
from universe_intelligence.fixtures.seed_universes import MEMBERSHIP_EVENTS
from universe_intelligence.provenance import provenance
from universe_intelligence.registry import bootstrap_universes, current_members
from universe_intelligence.schema import IUI_VERSION, envelope


def _parse(d: str | None) -> date | None:
    if not d:
        return None
    try:
        return date.fromisoformat(str(d)[:10])
    except Exception:
        return None


def bootstrap_membership_events() -> dict[str, Any]:
    n = 0
    for ev in MEMBERSHIP_EVENTS:
        eid = str(ev["event_id"])
        payload = {
            **ev,
            "ticker": str(ev["ticker"]).upper(),
            "universe_id": str(ev["universe_id"]).upper(),
            "provenance": provenance(
                source=str(ev.get("source") or "fixture"),
                collector="membership_engine",
                confidence=0.85,
                derived_from=["fixtures.MEMBERSHIP_EVENTS"],
            ),
            "fabricated": False,
            "iui_version": IUI_VERSION,
        }
        iui_store.put_membership_event(eid, payload)
        n += 1
    return envelope(kind="membership_bootstrap", payload={"events": n})


def _events_for(ticker: str | None = None, universe_id: str | None = None) -> list[dict[str, Any]]:
    events = iui_store.list_membership_events()
    if not events:
        bootstrap_membership_events()
        events = iui_store.list_membership_events()
    out = []
    for e in events:
        if ticker and str(e.get("ticker") or "").upper() != ticker.upper():
            continue
        if universe_id and str(e.get("universe_id") or "").upper() != universe_id.upper():
            continue
        out.append(e)
    return out


def _baseline_members(universe_id: str) -> set[str]:
    if not iui_store.list_universes():
        bootstrap_universes()
    return set(current_members(universe_id))


def _event_membership(events: list[dict[str, Any]], as_of_d: date) -> tuple[bool | None, dict[str, Any] | None]:
    """Resolve membership from explicit reconstitution events.

    join: member when effective_from <= as_of <= (effective_to or ∞)
    leave: encodes a closed historical window [effective_from, effective_to]
    """
    if not events:
        return None, None
    # Prefer the most specific matching window
    matched = None
    member: bool | None = None
    for e in sorted(events, key=lambda x: str(x.get("effective_from") or "")):
        start = _parse(e.get("effective_from"))
        end = _parse(e.get("effective_to"))
        action = e.get("action")
        if start is None:
            continue
        if action == "join":
            if as_of_d < start:
                # Before join — explicitly not yet a member via this event
                if member is None:
                    member = False
                    matched = e
            elif end is None or as_of_d <= end:
                member = True
                matched = e
            else:
                member = False
                matched = e
        elif action == "leave":
            # Closed membership window
            if start <= as_of_d and (end is None or as_of_d <= end):
                member = True
                matched = e
            elif end and as_of_d > end:
                member = False
                matched = e
    return member, matched


def was_member(*, ticker: str, universe_id: str, as_of: str) -> dict[str, Any]:
    """Point-in-time membership query."""
    t = ticker.upper()
    u = universe_id.upper()
    as_of_d = _parse(as_of)
    if not as_of_d:
        return {
            "found": False,
            "ticker": t,
            "universe_id": u,
            "as_of": as_of,
            "member": None,
            "insufficient": True,
            "reason": "invalid_as_of_date",
            "fabricated": False,
        }

    events = _events_for(ticker=t, universe_id=u)
    if events:
        member, matched = _event_membership(events, as_of_d)
        return {
            "found": True,
            "ticker": t,
            "universe_id": u,
            "as_of": as_of_d.isoformat(),
            "member": bool(member) if member is not None else False,
            "evidence_event": matched,
            "insufficient": False,
            "fabricated": False,
            "iui_version": IUI_VERSION,
        }

    baseline = _baseline_members(u)
    snap = iui_store.get_snapshot(u)
    snap_as_of = _parse((snap or {}).get("as_of"))
    if t in baseline:
        if snap_as_of and as_of_d > snap_as_of:
            return {
                "found": True,
                "ticker": t,
                "universe_id": u,
                "as_of": as_of_d.isoformat(),
                "member": None,
                "insufficient": True,
                "reason": "membership_future_of_snapshot",
                "fabricated": False,
            }
        return {
            "found": True,
            "ticker": t,
            "universe_id": u,
            "as_of": as_of_d.isoformat(),
            "member": True,
            "evidence_event": {
                "source": "current_snapshot",
                "note": "Assumed member via current snapshot; no contrary reconstitution event.",
            },
            "insufficient": False,
            "fabricated": False,
            "assumption": "current_snapshot_open_membership",
            "iui_version": IUI_VERSION,
        }

    return {
        "found": True,
        "ticker": t,
        "universe_id": u,
        "as_of": as_of_d.isoformat(),
        "member": False,
        "insufficient": False,
        "fabricated": False,
        "iui_version": IUI_VERSION,
    }


def memberships_for_company(ticker: str, *, as_of: str | None = None) -> dict[str, Any]:
    """Universe relationships — which indices is this company a member of?"""
    t = ticker.upper()
    as_of = as_of or date.today().isoformat()
    if not iui_store.list_universes():
        bootstrap_universes()
    memberships = []
    for uid in iui_store.list_universes():
        ans = was_member(ticker=t, universe_id=uid, as_of=as_of)
        if ans.get("member") is True:
            uobj = iui_store.get_universe(uid) or {}
            memberships.append(
                {
                    "universe_id": uid,
                    "display_name": uobj.get("display_name"),
                    "family": uobj.get("family"),
                    "tier": uobj.get("tier"),
                    "as_of": as_of,
                }
            )
    return envelope(
        kind="company_universe_relationships",
        payload={
            "ticker": t,
            "as_of": as_of,
            "memberships": memberships,
            "n": len(memberships),
            "queryable": True,
        },
    )


def members_as_of(universe_id: str, as_of: str) -> dict[str, Any]:
    """Full constituent list as of a date (PIT)."""
    u = universe_id.upper()
    baseline = sorted(_baseline_members(u))
    event_tickers = {e.get("ticker") for e in _events_for(universe_id=u)}
    candidates = set(baseline) | {str(t).upper() for t in event_tickers if t}
    members = set()
    for t in candidates:
        ans = was_member(ticker=t, universe_id=u, as_of=as_of)
        if ans.get("member") is True:
            members.add(t)
    return envelope(
        kind="universe_members_as_of",
        payload={
            "universe_id": u,
            "as_of": as_of,
            "members": sorted(members),
            "n": len(members),
            "baseline_n": len(baseline),
        },
    )
