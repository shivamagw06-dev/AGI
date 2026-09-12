"""In-process IFAC metrics for admin / debug."""

from __future__ import annotations

import threading
from collections import deque
from typing import Any

_LOCK = threading.Lock()
_RECENT: deque[dict[str, Any]] = deque(maxlen=100)
_STATS: dict[str, Any] = {
    "composes": 0,
    "consensus_demoted": 0,
    "conflicts": 0,
    "dqiv_fail": 0,
    "templates": {},
    "families": {},
    "primary_engines": {},
    "compose_ms_total": 0.0,
}


def record(payload: dict[str, Any]) -> None:
    with _LOCK:
        _STATS["composes"] += 1
        if payload.get("consensus_demoted"):
            _STATS["consensus_demoted"] += 1
        if payload.get("conflicts"):
            _STATS["conflicts"] += 1
        if not (payload.get("dqiv") or {}).get("ok", True):
            _STATS["dqiv_fail"] += 1
        tmpl = str(payload.get("template") or "unknown")
        _STATS["templates"][tmpl] = int(_STATS["templates"].get(tmpl) or 0) + 1
        fam = str(payload.get("family") or "unknown")
        _STATS["families"][fam] = int(_STATS["families"].get(fam) or 0) + 1
        primary = str(payload.get("primary_engine") or "none")
        _STATS["primary_engines"][primary] = int(_STATS["primary_engines"].get(primary) or 0) + 1
        ms = float(((payload.get("debug") or {}).get("compose_ms") or 0.0))
        _STATS["compose_ms_total"] += ms
        _RECENT.appendleft(
            {
                "template": tmpl,
                "family": fam,
                "primary_engine": primary,
                "consensus_demoted": bool(payload.get("consensus_demoted")),
                "conflicts": len(payload.get("conflicts") or []),
                "dqiv_ok": bool((payload.get("dqiv") or {}).get("ok", True)),
                "compose_ms": ms,
                "engines_used": list(payload.get("engines_used") or [])[:10],
                "summary": str(payload.get("summary") or "")[:240],
            }
        )


def stats() -> dict[str, Any]:
    with _LOCK:
        n = max(1, int(_STATS["composes"]))
        return {
            **{k: v for k, v in _STATS.items() if k != "compose_ms_total"},
            "avg_compose_ms": round(_STATS["compose_ms_total"] / n, 2),
            "consensus_first_rate": round(_STATS["consensus_demoted"] / n, 4),
            "conflict_rate": round(_STATS["conflicts"] / n, 4),
            "dqiv_fail_rate": round(_STATS["dqiv_fail"] / n, 4),
        }


def recent(limit: int = 20) -> list[dict[str, Any]]:
    with _LOCK:
        return list(_RECENT)[: max(1, min(int(limit), 100))]
