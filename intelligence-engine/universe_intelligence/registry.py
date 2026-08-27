"""Universe Registry — manage any institutional investment universe.

Not a ticker list. A versioned, cross-market registry with parents, families,
and quality standards. Soft layer only.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from universe_intelligence import store as iui_store
from universe_intelligence.fixtures.seed_universes import universe_definitions
from universe_intelligence.provenance import attach_object_provenance, provenance
from universe_intelligence.schema import IUI_VERSION, envelope


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def bootstrap_universes() -> dict[str, Any]:
    """Register all defined universes + take current snapshots."""
    registered = []
    for u in universe_definitions():
        uid = str(u["universe_id"]).upper()
        obj = attach_object_provenance(
            {
                "universe_id": uid,
                "family": u.get("family"),
                "region": u.get("region"),
                "market": u.get("market"),
                "parent": u.get("parent"),
                "display_name": u.get("display_name"),
                "tier": u.get("tier"),
                "status": u.get("status"),
                "quality_standard": u.get("quality_standard"),
                "member_count": len(u.get("members") or []),
                "note": u.get("note"),
                "iui_version": IUI_VERSION,
            },
            source="iui_seed",
            collector="universe_registry",
            confidence=1.0,
            derived_from=["fixtures.seed_universes"],
        )
        iui_store.put_universe(uid, obj)
        # Versioned snapshot of current membership
        version = f"v{_now().replace(':', '').replace('-', '')}"
        snap = {
            "universe_id": uid,
            "version": version,
            "as_of": _now()[:10],
            "members": list(u.get("members") or []),
            "n": len(u.get("members") or []),
            "status": u.get("status"),
            "provenance": provenance(
                source="iui_seed",
                collector="universe_registry.snapshot",
                confidence=1.0,
                derived_from=[f"universe:{uid}"],
            ),
            "fabricated": False,
            "iui_version": IUI_VERSION,
        }
        iui_store.put_snapshot(uid, version, snap)
        registered.append(uid)
    return envelope(
        kind="universe_registry_bootstrap",
        payload={"registered": registered, "n": len(registered)},
    )


def get_universe(universe_id: str) -> dict[str, Any]:
    uid = universe_id.upper()
    obj = iui_store.get_universe(uid)
    if not obj:
        # Lazy bootstrap if empty
        if not iui_store.list_universes():
            bootstrap_universes()
            obj = iui_store.get_universe(uid)
    if not obj:
        return {
            "found": False,
            "universe_id": uid,
            "insufficient": True,
            "reason": "universe_not_registered",
            "fabricated": False,
        }
    snap = iui_store.get_snapshot(uid)
    return {
        "found": True,
        "universe": obj,
        "latest_snapshot": snap,
        "snapshot_versions": iui_store.list_snapshots(uid),
        "fabricated": False,
    }


def list_universes(*, family: str | None = None, status: str | None = None) -> dict[str, Any]:
    if not iui_store.list_universes():
        bootstrap_universes()
    rows = []
    for uid in iui_store.list_universes():
        obj = iui_store.get_universe(uid) or {}
        if family and obj.get("family") != family:
            continue
        if status and obj.get("status") != status:
            continue
        rows.append(obj)
    return envelope(
        kind="universe_registry",
        payload={
            "n": len(rows),
            "universes": rows,
            "families": sorted({r.get("family") for r in rows if r.get("family")}),
        },
    )


def universe_tree() -> dict[str, Any]:
    """Parent/child relationships across registered universes."""
    board = list_universes()
    by_id = {u["universe_id"]: u for u in board.get("universes") or []}
    children: dict[str, list[str]] = {}
    roots = []
    for uid, u in by_id.items():
        parent = u.get("parent")
        if parent and parent in by_id:
            children.setdefault(parent, []).append(uid)
        else:
            roots.append(uid)
    return envelope(
        kind="universe_tree",
        payload={"roots": roots, "children": children, "by_id": {k: {"display_name": v.get("display_name"), "tier": v.get("tier"), "status": v.get("status")} for k, v in by_id.items()}},
    )


def current_members(universe_id: str) -> list[str]:
    snap = iui_store.get_snapshot(universe_id.upper())
    if snap and snap.get("members"):
        return [str(m).upper() for m in snap["members"]]
    # Fallback to seed definitions
    for u in universe_definitions():
        if str(u["universe_id"]).upper() == universe_id.upper():
            return [str(m).upper() for m in (u.get("members") or [])]
    return []
