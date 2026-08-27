"""Where a desk request spends its time, without becoming the problem it measures.

The first version cleared every cache and rebuilt each stage from cold inside
the request. It produced the numbers that found the real bottleneck - two
unbounded price queries reading back to 2006 - and then took the engine down
with a 502, because forcing 140 seconds of database work onto the request path
is precisely the anti-pattern the rest of this work removes.

So it no longer forces builds. Serving costs are measured live because they are
milliseconds; build costs are read from what the artifacts recorded when they
last built, which is the same number without the outage.

The one heavy measurement left is opt-in and named accordingly.
"""

from __future__ import annotations

import time
from typing import Any, Callable

from hedge_fund_lab import desk_snapshot


def _timed(label: str, fn: Callable[[], Any]) -> dict[str, Any]:
    started = time.time()
    try:
        out = fn()
        size = len(out) if hasattr(out, "__len__") else None
        return {"stage": label, "seconds": round(time.time() - started, 3),
                "size": size, "measured": "live", "ok": True}
    except Exception as exc:
        return {"stage": label, "seconds": round(time.time() - started, 3),
                "measured": "live", "ok": False, "error": str(exc)[:200]}


def measure(*, include_builds: bool = False) -> dict[str, Any]:
    """What a request pays, and what a rebuild costs behind it.

    ``include_builds`` re-runs the expensive builders and will make the engine
    unresponsive for minutes. It exists for a maintenance window and is off by
    default for the obvious reason.
    """
    from hedge_fund_lab import scanner, terminal

    served: list[dict[str, Any]] = [
        _timed("universe_served", scanner._universe),
        _timed("ratio_history_served", scanner._history_index),
        _timed("latest_close_by_symbol", scanner._latest_close_by_symbol),
        _timed("return_1y_by_symbol", scanner._return_1y_by_symbol),
        _timed("forward_eps", scanner._forward_eps_by_symbol),
    ]
    universe = scanner._universe()
    served.append(_timed("industry_medians", lambda: terminal._industry_medians(universe)))
    served.append(_timed("run_all_scans", lambda: terminal.run_all(limit=1000)))

    # Recorded when each artifact last built, rather than rebuilt to find out.
    builds = [{"stage": f"{a['name']}_build", "seconds": a.get("build_seconds"),
               "size": a.get("size"), "measured": "recorded",
               "age_seconds": a.get("age_seconds")}
              for a in desk_snapshot.status_all() if a.get("build_seconds")]

    if include_builds:
        served.append(_timed("universe_build_forced", scanner._build_universe))
        served.append(_timed("ratio_history_build_forced",
                             scanner._valuation_history_by_symbol))

    request_total = round(sum(s["seconds"] for s in served), 2)
    return {
        "ok": True,
        "request_path_seconds": request_total,
        "served": sorted(served, key=lambda s: -s["seconds"]),
        "background_builds": builds,
        "note": ("serving costs measured live; build costs read from what the "
                 "artifacts recorded, because forcing them here once returned a 502"),
    }
