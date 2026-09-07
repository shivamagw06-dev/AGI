"""Incremental daily updates — detect changes, rebuild only what changed."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from universe_intelligence import store as iui_store
from universe_intelligence.provenance import provenance
from universe_intelligence.registry import current_members, get_universe
from universe_intelligence.schema import IUI_VERSION, envelope


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _fingerprint(ticker: str) -> str:
    """Content fingerprint of soft KF company/pack state for change detection."""
    payload: dict[str, Any] = {"ticker": ticker.upper()}
    try:
        from knowledge_factory.store import repository as kf

        obj = kf.get_object("company", ticker) or {}
        pack = kf.get_pack(ticker) or {}
        payload["obj_keys"] = sorted(obj.keys())
        payload["quality"] = obj.get("quality_score") or pack.get("quality")
        payload["pack_pe"] = pack.get("historical_pe")
        payload["timeline_n"] = (obj.get("timeline") or {}).get("n")
        payload["sector"] = obj.get("sector")
    except Exception:
        payload["missing_kf"] = True
    try:
        from institutional_reasoning.fundamentals.primitives import has_primitives
        from institutional_reasoning.fundamentals.market_series import monthly_returns

        payload["primitives"] = has_primitives(ticker)
        payload["risk"] = bool(monthly_returns(ticker))
    except Exception:
        pass
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def detect_changes(universe_id: str = "NIFTY_500") -> dict[str, Any]:
    """Compare current fingerprints vs last change-set; classify new/removed/changed/stale."""
    uid = universe_id.upper()
    members = set(current_members(uid))
    prev = iui_store.get_report(f"fingerprints_{uid}") or {"fingerprints": {}, "members": []}
    prev_fp: dict[str, str] = dict(prev.get("fingerprints") or {})
    prev_members = set(str(m).upper() for m in (prev.get("members") or []))

    new = sorted(members - prev_members)
    removed = sorted(prev_members - members)
    changed = []
    unchanged = []
    fingerprints = {}
    for t in sorted(members):
        fp = _fingerprint(t)
        fingerprints[t] = fp
        if t in prev_fp and prev_fp[t] == fp and t not in new:
            unchanged.append(t)
        else:
            if t not in new:
                changed.append(t)

    # Stale: institutional coverage False or ICI band needs_improvement
    stale = []
    missing = []
    for t in sorted(members):
        co = iui_store.get_company(t)
        if not co:
            missing.append(t)
            continue
        if not co.get("institutional_coverage"):
            stale.append(t)

    change_id = f"{uid}_{_now().replace(':', '').replace('-', '')}"
    changeset = {
        "change_id": change_id,
        "universe_id": uid,
        "detected_at": _now(),
        "new": new,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
        "stale": stale,
        "missing_registry": missing,
        "rebuild_targets": sorted(set(new) | set(changed) | set(missing) | set(stale)),
        "n_members": len(members),
        "n_rebuild": 0,  # filled by apply
        "provenance": provenance(
            source="iui_incremental",
            collector="detect_changes",
            confidence=1.0,
            derived_from=[f"universe:{uid}"],
        ),
        "fabricated": False,
        "iui_version": IUI_VERSION,
    }
    changeset["n_rebuild"] = len(changeset["rebuild_targets"])
    iui_store.put_change_set(change_id, changeset)
    iui_store.put_report(
        f"fingerprints_{uid}",
        {"fingerprints": fingerprints, "members": sorted(members), "updated_at": _now()},
    )
    return changeset


def apply_incremental(
    universe_id: str = "NIFTY_500",
    *,
    force_full: bool = False,
    ensure_kf: bool = True,
) -> dict[str, Any]:
    """Rebuild knowledge only for changed companies; recompute packs via KF soft call."""
    from universe_intelligence.company_registry import compile_company

    uid = universe_id.upper()
    if force_full or not (iui_store.get_report(f"fingerprints_{uid}") or {}).get("fingerprints"):
        targets = current_members(uid)
        changeset = {
            "change_id": f"{uid}_full_{_now().replace(':', '')}",
            "universe_id": uid,
            "full_rebuild": True,
            "rebuild_targets": targets,
            "new": targets,
            "removed": [],
            "changed": [],
            "unchanged": [],
            "stale": [],
            "missing_registry": [],
            "n_members": len(targets),
            "n_rebuild": len(targets),
            "fabricated": False,
        }
    else:
        changeset = detect_changes(uid)
        targets = list(changeset.get("rebuild_targets") or [])

    # Soft KF rebuild for targets only (not full universe nightly).
    kf_result = None
    if ensure_kf and targets:
        try:
            from knowledge_factory.production import run_daily_pipeline

            kf_result = run_daily_pipeline(entities=list(targets))
        except Exception as exc:
            kf_result = {"status": "error", "error": str(exc)}

    compiled = []
    for t in targets:
        compile_company(t)
        compiled.append(t.upper())

    # Refresh fingerprints after rebuild
    fps = {}
    for t in current_members(uid):
        fps[t] = _fingerprint(t)
    iui_store.put_report(
        f"fingerprints_{uid}",
        {"fingerprints": fps, "members": current_members(uid), "updated_at": _now()},
    )

    result = envelope(
        kind="incremental_update",
        payload={
            "universe_id": uid,
            "changeset": {k: changeset.get(k) for k in ("change_id", "new", "removed", "changed", "stale", "n_rebuild", "full_rebuild")},
            "compiled": len(compiled),
            "kf": {"ok": bool(kf_result and kf_result.get("ok")), "companies": (kf_result or {}).get("companies_covered")},
            "mode": "full" if changeset.get("full_rebuild") else "incremental",
        },
    )
    iui_store.put_report("last_incremental", result)
    return result
