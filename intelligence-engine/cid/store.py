"""In-process CID store — permanent living dossiers (never overwrite timeline history)."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from typing import Any

from cid.schema import empty_dossier


class CidStore:
    def __init__(self) -> None:
        self._lock = Lock()
        self._dossiers: dict[str, dict[str, Any]] = {}

    def get(self, ticker: str) -> dict[str, Any] | None:
        t = (ticker or "").upper()
        with self._lock:
            d = self._dossiers.get(t)
            if d:
                return deepcopy(d)
        try:
            from cid.persistence import load_latest

            persisted = load_latest(t)
        except Exception:
            persisted = None
        if persisted:
            with self._lock:
                self._dossiers[t] = persisted
            return deepcopy(persisted)
        return None

    def ensure(self, ticker: str, *, company: str | None = None) -> dict[str, Any]:
        t = (ticker or "").upper()
        if not t:
            return empty_dossier("", company=company)
        now = datetime.now(timezone.utc).isoformat()
        with self._lock:
            if t not in self._dossiers:
                d = empty_dossier(t, company=company)
                d["created_at"] = now
                d["updated_at"] = now
                self._dossiers[t] = d
            return deepcopy(self._dossiers[t])

    def put(self, dossier: dict[str, Any]) -> dict[str, Any]:
        t = (dossier.get("ticker") or "").upper()
        if not t:
            return dossier
        now = datetime.now(timezone.utc).isoformat()
        dossier = dict(dossier)
        dossier["ticker"] = t
        dossier["updated_at"] = now
        if not dossier.get("created_at"):
            dossier["created_at"] = now
        with self._lock:
            self._dossiers[t] = dossier
            return deepcopy(dossier)

    def list(self, limit: int = 100) -> list[dict[str, Any]]:
        with self._lock:
            rows = sorted(
                self._dossiers.values(),
                key=lambda d: d.get("updated_at") or "",
                reverse=True,
            )
            return [deepcopy(r) for r in rows[:limit]]

    def summary_rows(self, limit: int = 100) -> list[dict[str, Any]]:
        rows = []
        for d in self.list(limit=limit):
            rows.append(
                {
                    "ticker": d.get("ticker"),
                    "company_name": (d.get("identity") or {}).get("company_name"),
                    "sector": (d.get("identity") or {}).get("sector"),
                    "sector_id": (d.get("identity") or {}).get("sector_id")
                    or (d.get("sector_framework") or {}).get("sector_id"),
                    "coverage_score": d.get("coverage_score"),
                    "coverage_grade": d.get("coverage_grade"),
                    "missing_evidence": d.get("missing_evidence") or [],
                    "latest_announcement": d.get("latest_announcement"),
                    "latest_filing": d.get("latest_filing"),
                    "latest_presentation": d.get("latest_presentation"),
                    "updated_at": d.get("updated_at"),
                    "forecast_accuracy": (d.get("forecasts") or {}).get("accuracy") or {},
                    "risk_score": (d.get("risks") or {}).get("risk_score"),
                    "timeline_events": len(d.get("evidence_timeline") or []),
                }
            )
        return rows


_STORE: CidStore | None = None


def get_cid_store() -> CidStore:
    global _STORE
    if _STORE is None:
        _STORE = CidStore()
    return _STORE
