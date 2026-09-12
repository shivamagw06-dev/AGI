"""In-memory DVC store — validated fields, conflicts, quality, learning."""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from dvc.learning import empty_provider_stats, provider_health_row
from dvc.schema import DVC_VERSION

_LOCK = threading.RLock()
_COMPANIES: Dict[str, Dict[str, Any]] = {}
_PROVIDER_STATS: Dict[str, Dict[str, Any]] = {}
_CONFLICTS: List[Dict[str, Any]] = []
_LATEST_UPDATES: List[Dict[str, Any]] = []
_VALIDATION_ERRORS: List[Dict[str, Any]] = []
_MAX_UPDATES = 200
_MAX_ERRORS = 200
_MAX_CONFLICTS = 500


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_company_validation(company_id: str, package: Dict[str, Any]) -> Dict[str, Any]:
    cid = (company_id or "").strip().upper()
    if not cid:
        raise ValueError("company_id required")
    with _LOCK:
        prev = dict(_COMPANIES.get(cid) or {})
        # Preserve previous field values for change history
        prev_fields = dict(prev.get("validated_fields") or {})
        new_fields = dict(package.get("validated_fields") or {})
        for fname, field in new_fields.items():
            if not isinstance(field, dict):
                continue
            old = prev_fields.get(fname)
            if isinstance(old, dict) and old.get("value") is not None:
                field = dict(field)
                field["previous_value"] = old.get("value")
                # recompute change if both numeric
                try:
                    ov = float(old.get("value"))
                    nv = float(field.get("value"))
                    if ov != 0:
                        field["changed"] = nv - ov
                        field["change_percent"] = round(((nv - ov) / abs(ov)) * 100.0, 4)
                    history = list(old.get("change_history") or [])
                    history.append(
                        {
                            "from": old.get("value"),
                            "to": field.get("value"),
                            "at": field.get("verified_at") or _now(),
                            "provider": field.get("provider"),
                        }
                    )
                    field["change_history"] = history[-20:]
                except (TypeError, ValueError):
                    pass
                new_fields[fname] = field
        row = {
            **prev,
            **package,
            "company_id": cid,
            "validated_fields": new_fields,
            "updated_at": _now(),
            "dvc_version": DVC_VERSION,
        }
        _COMPANIES[cid] = row
        _LATEST_UPDATES.insert(
            0,
            {
                "company_id": cid,
                "at": row["updated_at"],
                "overall_quality": (row.get("quality") or {}).get("overall"),
                "conflicts": len(row.get("conflicts") or []),
                "canonical_provider": row.get("winning_provider_summary"),
            },
        )
        del _LATEST_UPDATES[_MAX_UPDATES:]
        # Merge conflicts into global queue
        for c in row.get("conflicts") or []:
            if not isinstance(c, dict):
                continue
            entry = dict(c)
            entry["company_id"] = cid
            _CONFLICTS.insert(0, entry)
        del _CONFLICTS[_MAX_CONFLICTS:]
        return dict(row)


def get_company(company_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        row = _COMPANIES.get((company_id or "").strip().upper())
        return dict(row) if row else None


def list_companies(*, limit: int = 100) -> List[Dict[str, Any]]:
    with _LOCK:
        rows = sorted(
            _COMPANIES.values(),
            key=lambda r: float((r.get("quality") or {}).get("overall") or 0),
        )
        return [dict(r) for r in rows[: max(1, min(int(limit), 500))]]


def get_provider_stats(provider: str) -> Dict[str, Any]:
    key = (provider or "").strip().lower()
    with _LOCK:
        if key not in _PROVIDER_STATS:
            _PROVIDER_STATS[key] = empty_provider_stats(key)
        return dict(_PROVIDER_STATS[key])


def save_provider_stats(stats: Dict[str, Any]) -> Dict[str, Any]:
    key = str(stats.get("provider") or "").strip().lower()
    with _LOCK:
        _PROVIDER_STATS[key] = dict(stats)
        return dict(_PROVIDER_STATS[key])


def list_provider_health() -> List[Dict[str, Any]]:
    with _LOCK:
        rows = [provider_health_row(s) for s in _PROVIDER_STATS.values()]
        return sorted(rows, key=lambda r: int(r.get("priority") or 99))


def list_conflicts(*, limit: int = 50, severity: Optional[str] = None) -> List[Dict[str, Any]]:
    with _LOCK:
        rows = list(_CONFLICTS)
    if severity:
        rows = [r for r in rows if str(r.get("severity")) == severity]
    return rows[: max(1, min(int(limit), 200))]


def list_latest_updates(*, limit: int = 30) -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_LATEST_UPDATES[: max(1, min(int(limit), 100))])


def record_validation_error(company_id: str, error: str, detail: Any = None) -> None:
    with _LOCK:
        _VALIDATION_ERRORS.insert(
            0,
            {
                "company_id": (company_id or "").strip().upper(),
                "error": error,
                "detail": detail,
                "at": _now(),
            },
        )
        del _VALIDATION_ERRORS[_MAX_ERRORS:]


def list_validation_errors(*, limit: int = 50) -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_VALIDATION_ERRORS[: max(1, min(int(limit), 200))])


def incomplete_companies(*, limit: int = 30) -> List[Dict[str, Any]]:
    with _LOCK:
        rows = []
        for r in _COMPANIES.values():
            q = r.get("quality") or {}
            cov = float(q.get("coverage") or 0)
            if cov < 0.85:
                rows.append(
                    {
                        "company_id": r.get("company_id"),
                        "coverage": cov,
                        "overall": q.get("overall"),
                        "missing_fields": r.get("missing_fields") or [],
                        "needs_refresh": bool(r.get("needs_refresh")),
                    }
                )
        rows.sort(key=lambda x: float(x.get("coverage") or 0))
        return rows[: max(1, min(int(limit), 100))]


def needing_refresh(*, limit: int = 30) -> List[Dict[str, Any]]:
    with _LOCK:
        rows = [
            {
                "company_id": r.get("company_id"),
                "freshness": (r.get("quality") or {}).get("freshness"),
                "overall": (r.get("quality") or {}).get("overall"),
                "updated_at": r.get("updated_at"),
                "recommended_refresh": r.get("recommended_refresh"),
            }
            for r in _COMPANIES.values()
            if r.get("needs_refresh")
        ]
        return rows[: max(1, min(int(limit), 100))]


def reset_for_tests() -> None:
    with _LOCK:
        _COMPANIES.clear()
        _PROVIDER_STATS.clear()
        _CONFLICTS.clear()
        _LATEST_UPDATES.clear()
        _VALIDATION_ERRORS.clear()
