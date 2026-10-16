"""Read-only collectors — pass-through existing intelligence; never run FIRE analysis."""

from __future__ import annotations

from typing import Any, Mapping, Optional


def _pass(module: str, payload: Mapping[str, Any] | None, *, source: str) -> dict[str, Any]:
    if not isinstance(payload, Mapping) or not payload:
        return {
            "ok": False,
            "available": False,
            "module": module,
            "source": source,
            "payload": {},
            "reason": "no_cached_intelligence",
        }
    return {
        "ok": True,
        "available": True,
        "module": module,
        "source": source,
        "payload": dict(payload),
        "reason": None,
    }


def collect_module(
    ticker: str,
    module: str,
    *,
    prebuilt: Optional[Mapping[str, Mapping[str, Any]]] = None,
) -> dict[str, Any]:
    """Resolve a FIRE/IO module payload without invoking analysis engines."""
    t = str(ticker or "").strip().upper()
    mod = str(module or "").strip()
    pre = dict(prebuilt or {})

    if mod in pre and isinstance(pre[mod], Mapping):
        return _pass(mod, pre[mod], source="prebuilt")

    # Alternate keys (FIRE-01 vs fire01)
    alt_keys = [mod, mod.upper(), mod.lower(), mod.replace("-", "_"), mod.replace("_", "-")]
    for k in alt_keys:
        if k in pre and isinstance(pre[k], Mapping):
            return _pass(mod, pre[k], source="prebuilt")

    from company_workspace import store as cw_store

    cached = cw_store.get_module_cache(t)
    if mod in cached:
        return _pass(mod, cached[mod], source="workspace_cache")
    for k, v in cached.items():
        if str(k).upper().replace("_", "-") == mod.upper().replace("_", "-"):
            return _pass(mod, v, source="workspace_cache")

    return _pass(mod, None, source="none")


def collect_watchlists(ticker: str) -> dict[str, Any]:
    """WO-01 memberships for ticker — store read only."""
    t = str(ticker or "").strip().upper()
    entries: list[dict[str, Any]] = []
    try:
        from watchlist_office import store as wl_store

        for wl in wl_store.list_watchlists():
            meta = wl.get("metadata") or {}
            for e in wl.get("entries") or []:
                if str(e.get("ticker") or "").upper() != t:
                    continue
                if e.get("removed"):
                    continue
                entries.append(
                    {
                        "watchlist_id": wl.get("watchlist_id"),
                        "name": meta.get("name"),
                        "ticker": t,
                        "priority": e.get("priority"),
                        "status": e.get("status"),
                        "tags": list(e.get("tags") or []),
                        "notes": e.get("notes"),
                        "last_research_at": e.get("last_research_at"),
                        "last_event_type": e.get("last_event_type"),
                    }
                )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "available": False, "module": "WO-01", "error": str(exc), "entries": []}
    return {
        "ok": True,
        "available": bool(entries),
        "module": "WO-01",
        "source": "watchlist_office.store",
        "entries": entries,
        "count": len(entries),
    }


def collect_portfolios(ticker: str) -> dict[str, Any]:
    """PO-01 memberships for ticker — store read only."""
    t = str(ticker or "").strip().upper()
    memberships: list[dict[str, Any]] = []
    try:
        from portfolio_office import store as po_store

        for pf in po_store.list_portfolios():
            meta = pf.get("metadata") or {}
            for h in pf.get("holdings") or []:
                if str(h.get("ticker") or "").upper() != t:
                    continue
                extras = h.get("extras") if isinstance(h.get("extras"), dict) else {}
                memberships.append(
                    {
                        "portfolio_id": pf.get("portfolio_id"),
                        "name": meta.get("name"),
                        "ticker": t,
                        "weight": h.get("weight"),
                        "shares": h.get("shares") or h.get("quantity"),
                        "sector": h.get("sector"),
                        "exposure": h.get("exposure") or extras.get("exposure"),
                        "quality_contribution": (
                            h.get("quality_contribution")
                            or h.get("quality")
                            or extras.get("quality_contribution")
                        ),
                    }
                )
    except Exception as exc:  # noqa: BLE001
        return {
            "ok": False,
            "available": False,
            "module": "PO-01",
            "error": str(exc),
            "memberships": [],
        }
    return {
        "ok": True,
        "available": bool(memberships),
        "module": "PO-01",
        "source": "portfolio_office.store",
        "memberships": memberships,
        "count": len(memberships),
    }


def collect_research(ticker: str) -> dict[str, Any]:
    """Research references from CW cache (populated by IO events / seed) — never run IO."""
    from company_workspace import store as cw_store

    t = str(ticker or "").strip().upper()
    history = cw_store.list_research(t)
    latest = history[-1] if history else None
    return {
        "ok": True,
        "available": bool(history),
        "module": "IO-01",
        "source": "company_workspace.research_cache",
        "latest": latest,
        "history": history,
        "count": len(history),
    }


def profile_stub(ticker: str, *, profile: Optional[Mapping[str, Any]] = None) -> dict[str, Any]:
    """Company profile from optional input or thin ticker stub — no enrichment engine."""
    t = str(ticker or "").strip().upper()
    base = {
        "company": t,
        "ticker": t,
        "sector": None,
        "industry": None,
        "exchange": None,
    }
    if isinstance(profile, Mapping):
        for k in ("company", "name", "sector", "industry", "exchange", "isin", "country"):
            if profile.get(k) is not None:
                key = "company" if k == "name" else k
                base[key] = profile.get(k)
        if profile.get("company") or profile.get("name"):
            base["company"] = profile.get("company") or profile.get("name")
    base["ticker"] = t
    return base
