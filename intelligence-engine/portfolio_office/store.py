"""Process-local portfolio store — live state + immutable snapshots."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock
from typing import Any, Optional


_LOCK = Lock()
_PORTFOLIOS: dict[str, dict[str, Any]] = {}
# snapshots keyed by snapshot_id; also indexed by portfolio_id
_SNAPSHOTS: dict[str, dict[str, Any]] = {}
_SNAPSHOT_INDEX: dict[str, list[str]] = {}
_METRICS: dict[str, Any] = {
    "portfolios": 0,
    "total_holdings": 0,
    "snapshots": 0,
    "quality_coverage": 0,
    "exposure_coverage": 0,
    "last_mean_confidence": None,
}


def put_portfolio(pf: dict[str, Any]) -> dict[str, Any]:
    pid = str(pf.get("portfolio_id") or (pf.get("metadata") or {}).get("portfolio_id") or "").strip()
    if not pid:
        raise ValueError("portfolio_id required")
    with _LOCK:
        _PORTFOLIOS[pid] = deepcopy(pf)
        _METRICS["portfolios"] = len(_PORTFOLIOS)
        _METRICS["total_holdings"] = sum(len(p.get("holdings") or []) for p in _PORTFOLIOS.values())
    return get_portfolio(pid)  # type: ignore[return-value]


def get_portfolio(portfolio_id: str) -> Optional[dict[str, Any]]:
    with _LOCK:
        p = _PORTFOLIOS.get(str(portfolio_id).strip())
        return deepcopy(p) if p else None


def list_portfolios() -> list[dict[str, Any]]:
    with _LOCK:
        return [deepcopy(p) for p in _PORTFOLIOS.values()]


def resolve_portfolio(name_or_id: str) -> Optional[dict[str, Any]]:
    key = str(name_or_id or "").strip()
    if not key:
        return None
    with _LOCK:
        if key in _PORTFOLIOS:
            return deepcopy(_PORTFOLIOS[key])
        # case-insensitive id / name match
        key_l = key.lower()
        for pid, p in _PORTFOLIOS.items():
            if pid.lower() == key_l:
                return deepcopy(p)
            meta = p.get("metadata") or {}
            if str(meta.get("name") or "").lower() == key_l:
                return deepcopy(p)
    return None


def put_snapshot(snap: dict[str, Any]) -> dict[str, Any]:
    """Store immutable snapshot. Existing snapshot_ids are never overwritten."""
    sid = str(snap.get("snapshot_id") or "").strip()
    pid = str(snap.get("portfolio_id") or "").strip()
    if not sid or not pid:
        raise ValueError("snapshot_id and portfolio_id required")
    with _LOCK:
        if sid in _SNAPSHOTS:
            # Immutability: return existing, do not replace
            return deepcopy(_SNAPSHOTS[sid])
        _SNAPSHOTS[sid] = deepcopy(snap)
        _SNAPSHOT_INDEX.setdefault(pid, []).append(sid)
        _METRICS["snapshots"] = len(_SNAPSHOTS)
    return deepcopy(snap)


def get_snapshot(snapshot_id: str) -> Optional[dict[str, Any]]:
    with _LOCK:
        s = _SNAPSHOTS.get(str(snapshot_id).strip())
        return deepcopy(s) if s else None


def list_snapshots(portfolio_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        ids = list(_SNAPSHOT_INDEX.get(str(portfolio_id).strip()) or [])
        return [deepcopy(_SNAPSHOTS[i]) for i in ids if i in _SNAPSHOTS]


def record_metrics(*, quality_covered: bool = False, exposure_covered: bool = False, mean_confidence: float | None = None) -> None:
    with _LOCK:
        if quality_covered:
            _METRICS["quality_coverage"] = int(_METRICS["quality_coverage"]) + 1
        if exposure_covered:
            _METRICS["exposure_coverage"] = int(_METRICS["exposure_coverage"]) + 1
        if mean_confidence is not None:
            _METRICS["last_mean_confidence"] = float(mean_confidence)
        _METRICS["portfolios"] = len(_PORTFOLIOS)
        _METRICS["total_holdings"] = sum(len(p.get("holdings") or []) for p in _PORTFOLIOS.values())
        _METRICS["snapshots"] = len(_SNAPSHOTS)


def metrics() -> dict[str, Any]:
    with _LOCK:
        m = deepcopy(_METRICS)
    return {
        **m,
        "panels": {
            "portfolios": m.get("portfolios"),
            "total_holdings": m.get("total_holdings"),
            "snapshots": m.get("snapshots"),
            "exposure_coverage": m.get("exposure_coverage"),
            "quality_coverage": m.get("quality_coverage"),
            "confidence": {"last_mean_confidence": m.get("last_mean_confidence")},
        },
    }


def reset_for_tests() -> None:
    with _LOCK:
        _PORTFOLIOS.clear()
        _SNAPSHOTS.clear()
        _SNAPSHOT_INDEX.clear()
        _METRICS["portfolios"] = 0
        _METRICS["total_holdings"] = 0
        _METRICS["snapshots"] = 0
        _METRICS["quality_coverage"] = 0
        _METRICS["exposure_coverage"] = 0
        _METRICS["last_mean_confidence"] = None
