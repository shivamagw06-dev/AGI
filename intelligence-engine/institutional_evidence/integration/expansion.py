"""Coverage expansion — after Top-20 complete, expand to next Nifty 500.

Do not expand during KIL Phase-1 integration. Gate is explicit.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .schema import (
    EXPANSION_NEXT_SIZE,
    EXPANSION_NEXT_UNIVERSE,
    EXPANSION_REQUIRES_STATE,
    KIL_PHASE1_DEMO,
)


def _nifty_500() -> List[str]:
    try:
        from knowledge_factory.coverage import NIFTY_500

        return [str(t).upper() for t in NIFTY_500]
    except Exception:
        try:
            from knowledge_factory.historical_depth.universe_priority import nifty_500

            return [str(t).upper() for t in nifty_500()]
        except Exception:
            return []


def expansion_status(*, top20_complete_count: int = 0, top20_total: int = 20) -> Dict[str, Any]:
    unlocked = top20_complete_count >= top20_total and top20_total > 0
    universe = _nifty_500()
    # "next 500" after current CGL ~500 means the Nifty 500 set as expansion target;
    # if already covering ~500, remaining = not yet Institutional Coverage Complete.
    return {
        "ok": True,
        "unlocked": unlocked,
        "requires": EXPANSION_REQUIRES_STATE,
        "top20_complete_count": top20_complete_count,
        "top20_total": top20_total,
        "next_universe": EXPANSION_NEXT_UNIVERSE,
        "next_size": EXPANSION_NEXT_SIZE,
        "nifty_500_symbols": len(universe),
        "phase1_demo": list(KIL_PHASE1_DEMO),
        "phase1_rule": "Complete KIL integration + demo companies before remaining Top-20; expand to Nifty 500 only after Top-20 Institutional Coverage Complete",
        "action_if_unlocked": "Enqueue Nifty 500 symbols into CGL/KF HD priority queue for continuous gather",
        "action_if_locked": "Do not expand coverage — finish Knowledge Integration first",
    }


def maybe_enqueue_next_500(*, force: bool = False) -> Dict[str, Any]:
    """Enqueue Nifty 500 into HD/CGL queue only when unlocked (or force for ops)."""
    from ...schema import PHASE1_TOP20
    from ...phase1_acceptance import evaluate_institutional_coverage

    complete = 0
    for c in PHASE1_TOP20:
        try:
            if evaluate_institutional_coverage(c["ticker"]).get("institutional_coverage_complete"):
                complete += 1
        except Exception:
            pass
    status = expansion_status(top20_complete_count=complete, top20_total=len(PHASE1_TOP20))
    if not status["unlocked"] and not force:
        return {
            "ok": True,
            "enqueued": False,
            "reason": "expansion_locked",
            "status": status,
        }

    symbols = _nifty_500()
    enqueued = 0
    try:
        from knowledge_factory.historical_depth import queue as bf_queue

        for sym in symbols:
            try:
                bf_queue.enqueue(sym)  # soft — API may differ
                enqueued += 1
            except Exception:
                try:
                    bf_queue.add_symbol(sym)
                    enqueued += 1
                except Exception:
                    pass
    except Exception as exc:
        return {
            "ok": False,
            "enqueued": False,
            "error": str(exc)[:200],
            "status": status,
            "symbols_available": len(symbols),
        }

    return {
        "ok": True,
        "enqueued": True,
        "count": enqueued,
        "universe": EXPANSION_NEXT_UNIVERSE,
        "status": status,
    }
