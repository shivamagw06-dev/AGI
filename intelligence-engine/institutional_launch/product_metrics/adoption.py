"""Adoption + domain product metrics (L-01)."""

from __future__ import annotations

import threading
from typing import Any, Dict

from institutional_launch.analytics.events import adoption_counts, recent_events
from institutional_launch.analytics.journey import journey_funnel, stage_metrics

_LOCK = threading.Lock()
_COUNTERS: Dict[str, int] = {
    "ask_questions": 0,
    "ask_success": 0,
    "ask_sources": 0,
    "workspace_sessions": 0,
    "notes_created": 0,
    "research_opened": 0,
    "companies_viewed": 0,
    "publications_generated": 0,
    "publications_exported": 0,
    "publications_shared": 0,
    "decisions_reviewed": 0,
    "committee_sessions": 0,
    "risk_updates": 0,
}
_ASK_LATENCY: list[float] = []


def reset_for_tests() -> None:
    with _LOCK:
        for k in _COUNTERS:
            _COUNTERS[k] = 0
        _ASK_LATENCY.clear()


def incr(metric: str, amount: int = 1) -> None:
    with _LOCK:
        if metric in _COUNTERS:
            _COUNTERS[metric] += amount


def record_ask(*, ok: bool, latency_ms: float = 0.0, sources: int = 0) -> None:
    with _LOCK:
        _COUNTERS["ask_questions"] += 1
        if ok:
            _COUNTERS["ask_success"] += 1
        _COUNTERS["ask_sources"] += max(0, int(sources))
        if latency_ms:
            _ASK_LATENCY.append(float(latency_ms))
            if len(_ASK_LATENCY) > 2000:
                del _ASK_LATENCY[:500]


def _percentile(vals: list[float], p: float) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    idx = max(0, min(len(s) - 1, int(p * (len(s) - 1))))
    return round(s[idx], 3)


def product_dashboard() -> dict[str, Any]:
    with _LOCK:
        c = dict(_COUNTERS)
        lat = list(_ASK_LATENCY)
    adopt = adoption_counts()
    ask_q = c["ask_questions"]
    return {
        "adoption": adopt,
        "ask_agi": {
            "questions_day": ask_q,  # session-window proxy in-process
            "median_response_ms": _percentile(lat, 0.50),
            "p95_response_ms": _percentile(lat, 0.95),
            "successful_completions": c["ask_success"],
            "success_rate": round(c["ask_success"] / ask_q, 4) if ask_q else None,
            "sources_consulted": c["ask_sources"],
        },
        "workspace": {
            "sessions": c["workspace_sessions"],
            "notes_created": c["notes_created"],
            "research_opened": c["research_opened"],
            "companies_viewed": c["companies_viewed"],
        },
        "publications": {
            "generated": c["publications_generated"],
            "exported": c["publications_exported"],
            "shared": c["publications_shared"],
            "success_rate": round(
                (c["publications_generated"] - 0) / max(c["publications_generated"], 1),
                4,
            )
            if c["publications_generated"]
            else None,
        },
        "portfolio_office": {
            "decisions_reviewed": c["decisions_reviewed"],
            "committee_sessions": c["committee_sessions"],
            "risk_updates": c["risk_updates"],
        },
        "journey": journey_funnel(),
        "stage_metrics": stage_metrics(),
        "recent_events": recent_events(limit=8),
    }
