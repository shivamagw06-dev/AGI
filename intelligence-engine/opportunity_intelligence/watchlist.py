"""Deterministic watchlist rankings over covered companies."""

from __future__ import annotations

from typing import Any, Callable

from opportunity_intelligence.schema import IC10_UNIVERSE, WATCHLIST_VIEWS
from opportunity_intelligence.score import priority_rank
from opportunity_intelligence.util import as_float


def _row(pack: dict[str, Any]) -> dict[str, Any]:
    opp = pack.get("opportunity") or {}
    return {
        "ticker": pack.get("display") or pack.get("entity"),
        "entity": pack.get("entity"),
        "ok": pack.get("ok"),
        "score": pack.get("score"),
        "research_priority": pack.get("research_priority"),
        "why_now": pack.get("why_now"),
        "confidence": pack.get("confidence"),
        "catalyst_n": len(pack.get("catalysts") or []),
        "blocker_n": len(pack.get("blockers") or []),
        "valuation_score": as_float(((pack.get("dimensions") or {}).get("valuation") or {}).get("score")),
        "financial_score": as_float(
            ((pack.get("dimensions") or {}).get("financial_momentum") or {}).get("score")
        ),
        "ownership_score": as_float(
            ((pack.get("dimensions") or {}).get("ownership_momentum") or {}).get("score")
        ),
        "delta_status": ((opp.get("knowledge_delta") or {}).get("status")),
        "delta_changes": as_float((opp.get("knowledge_delta") or {}).get("n_field_changes")) or 0,
    }


def _sort_key_top(r: dict[str, Any]) -> tuple:
    return (-(as_float(r.get("score")) or 0), priority_rank(r.get("research_priority") or "Monitor"), r.get("entity") or "")


def _sort_financial(r: dict[str, Any]) -> tuple:
    return (-(as_float(r.get("financial_score")) or 0), -(as_float(r.get("score")) or 0), r.get("entity") or "")


def _sort_valuation(r: dict[str, Any]) -> tuple:
    # Higher valuation opportunity score = larger compression / discount signal
    return (-(as_float(r.get("valuation_score")) or 0), -(as_float(r.get("score")) or 0), r.get("entity") or "")


def _sort_ownership(r: dict[str, Any]) -> tuple:
    return (-(as_float(r.get("ownership_score")) or 0), -(as_float(r.get("score")) or 0), r.get("entity") or "")


def _sort_catalysts(r: dict[str, Any]) -> tuple:
    return (-int(r.get("catalyst_n") or 0), -(as_float(r.get("score")) or 0), r.get("entity") or "")


def _sort_delta(r: dict[str, Any]) -> tuple:
    status = r.get("delta_status") or "UNCHANGED"
    status_rank = 0 if status == "UPDATED" else (1 if status not in {None, "UNCHANGED"} else 2)
    return (status_rank, -(as_float(r.get("delta_changes")) or 0), -(as_float(r.get("score")) or 0), r.get("entity") or "")


def _sort_priority(r: dict[str, Any]) -> tuple:
    return (priority_rank(r.get("research_priority") or "Monitor"), -(as_float(r.get("score")) or 0), r.get("entity") or "")


_VIEW_SORTERS: dict[str, Callable[[dict[str, Any]], tuple]] = {
    "top_emerging": _sort_key_top,
    "highest_improving_fundamentals": _sort_financial,
    "largest_valuation_compression": _sort_valuation,
    "strongest_ownership_improvement": _sort_ownership,
    "highest_catalyst_density": _sort_catalysts,
    "most_positive_knowledge_delta": _sort_delta,
    "highest_research_priority": _sort_priority,
}


def build_watchlists(packs: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_row(p) for p in packs if p.get("ok")]
    views: dict[str, list[dict[str, Any]]] = {}
    for view in WATCHLIST_VIEWS:
        sorter = _VIEW_SORTERS[view]
        views[view] = sorted(rows, key=sorter)

    return {
        "universe_n": len(packs),
        "ok_n": len(rows),
        "views": views,
        "top": views.get("top_emerging") or [],
        "research_priority": views.get("highest_research_priority") or [],
    }


def default_universe() -> tuple[str, ...]:
    return IC10_UNIVERSE
