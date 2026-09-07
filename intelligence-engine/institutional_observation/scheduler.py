"""Scheduler — batch observation runs over tickers / watchlists."""

from __future__ import annotations

from typing import Any, Iterable, List, Optional


def tickers_from_watchlists() -> List[str]:
    """High-priority tickers from WO-01 watchlists when available."""
    try:
        from watchlist_office import store as wl_store

        out: list[str] = []
        for wl in wl_store.list_watchlists():
            for entry in wl.get("entries") or wl.get("companies") or []:
                if isinstance(entry, str):
                    t = entry.strip().upper()
                else:
                    t = str((entry or {}).get("ticker") or "").strip().upper()
                if t and t not in out:
                    out.append(t)
        return out
    except Exception:  # noqa: BLE001
        return []


def schedule_observe(
    tickers: Optional[Iterable[str]] = None,
    *,
    include_watchlists: bool = True,
) -> list[str]:
    """Return ordered ticker list for an observation cycle."""
    ordered: list[str] = []
    if include_watchlists:
        for t in tickers_from_watchlists():
            if t not in ordered:
                ordered.append(t)
    for t in tickers or ():
        u = str(t or "").strip().upper()
        if u and u not in ordered:
            ordered.append(u)
    return ordered


def run_observation_cycle(
    tickers: Optional[Iterable[str]] = None,
    *,
    include_watchlists: bool = True,
) -> dict[str, Any]:
    from institutional_observation.production import observe_company

    queue = schedule_observe(tickers, include_watchlists=include_watchlists)
    results = []
    for ticker in queue:
        results.append(observe_company(ticker))
    return {
        "tickers": queue,
        "results": results,
        "observations": sum(len(r.get("observations") or []) for r in results),
        "critical": sum(
            1
            for r in results
            for o in r.get("observations") or []
            if o.get("severity") in {"critical", "high"}
        ),
    }
