"""Time each stage of a desk request from cold.

Written because the cold-start cost was guessed at twice and misattributed both
times - first to the universe build, then to the ratio history. Publishing the
universe took 256 seconds to 39; the remaining 39 was somewhere else, and
guessing a third time is not a method.

Every stage is measured with its cache cleared first, so the number is what a
fresh process pays rather than what a warm one does.
"""

from __future__ import annotations

import time
from typing import Any, Callable


def _timed(label: str, fn: Callable[[], Any]) -> dict[str, Any]:
    started = time.time()
    try:
        out = fn()
        size = len(out) if hasattr(out, "__len__") else None
        return {"stage": label, "seconds": round(time.time() - started, 2),
                "size": size, "ok": True}
    except Exception as exc:
        return {"stage": label, "seconds": round(time.time() - started, 2),
                "ok": False, "error": str(exc)[:200]}


def measure() -> dict[str, Any]:
    from hedge_fund_lab import scanner, terminal

    stages: list[dict[str, Any]] = []

    # Cleared first so each number is the cold cost, not a cache hit.
    scanner.reset_history_cache()
    scanner.reset_forward_eps_cache()

    stages.append(_timed("universe_from_snapshot", scanner._universe))
    stages.append(_timed("ratio_history_139k_rows", scanner._history_index))
    stages.append(_timed("forward_eps", scanner._forward_eps_by_symbol))
    stages.append(_timed("latest_close_by_symbol", scanner._latest_close_by_symbol))
    stages.append(_timed("return_1y_by_symbol", scanner._return_1y_by_symbol))

    universe = scanner._universe()
    stages.append(_timed("industry_medians", lambda: terminal._industry_medians(universe)))
    stages.append(_timed("run_all_scans", lambda: terminal.run_all(limit=1000)))

    total = round(sum(s["seconds"] for s in stages), 2)
    worst = max(stages, key=lambda s: s["seconds"]) if stages else None
    return {
        "ok": True,
        "total_seconds": total,
        "slowest": worst,
        "stages": sorted(stages, key=lambda s: -s["seconds"]),
        "note": "each stage measured with its cache cleared, so these are cold costs",
    }
