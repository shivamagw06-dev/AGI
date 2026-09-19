"""In-memory Institutional Learning registry (Sprint 5.5) — process memory only."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

from institutional_learning_office.schema import LEARNING_CATEGORIES, LEARNING_FIELDS, OUTCOME_LABELS


class LearningStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._by_id: dict[str, dict[str, Any]] = {}
        self._by_thesis: dict[str, list[str]] = {}
        self._by_decision: dict[str, list[str]] = {}
        self._by_portfolio: dict[str, list[str]] = {}
        self._runs: list[dict[str, Any]] = []

    def upsert(self, learning: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            lid = str(learning.get("learning_id") or "").strip()
            if not lid:
                raise ValueError("learning_id is required")
            stored = {k: deepcopy(learning.get(k)) for k in LEARNING_FIELDS if k in learning}
            for key in LEARNING_FIELDS:
                stored.setdefault(key, None)
            stored["learning_id"] = lid
            for extra in (
                "category",
                "company",
                "ticker",
                "questions_answered",
                "process_memory",
                "knowledge_factory_updated",
                "explanation",
                "schema_version",
                "ilo_version",
                "timestamp",
                "owner",
                "mutates_thesis",
                "mutates_decision",
                "mutates_portfolio",
                "mutates_monitoring",
            ):
                if extra in learning:
                    stored[extra] = deepcopy(learning[extra])
            self._by_id[lid] = stored
            for key, index in (
                ("thesis_id", self._by_thesis),
                ("decision_id", self._by_decision),
                ("portfolio_id", self._by_portfolio),
            ):
                ref = str(stored.get(key) or "").strip()
                if ref:
                    bucket = index.setdefault(ref, [])
                    if lid not in bucket:
                        bucket.append(lid)
            return deepcopy(stored)

    def get(self, learning_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._by_id.get(str(learning_id or "").strip())
            return deepcopy(row) if row else None

    def list_for_thesis(self, thesis_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._list_index(self._by_thesis, thesis_id, limit=limit)

    def list_for_decision(self, decision_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._list_index(self._by_decision, decision_id, limit=limit)

    def list_for_portfolio(self, portfolio_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        return self._list_index(self._by_portfolio, portfolio_id, limit=limit)

    def _list_index(self, index: dict[str, list[str]], key: str, *, limit: int) -> list[dict[str, Any]]:
        with self._lock:
            ids = list(index.get(str(key or "").strip(), []))
            out = [deepcopy(self._by_id[i]) for i in ids if i in self._by_id]
        out.sort(key=lambda r: str(r.get("timestamp") or r.get("learning_id") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def list_recent(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            out = [deepcopy(v) for v in self._by_id.values()]
        out.sort(key=lambda r: str(r.get("timestamp") or r.get("learning_id") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def list_by_category(self, category: str, *, limit: int = 50) -> list[dict[str, Any]]:
        cat = str(category or "").strip()
        with self._lock:
            out = [deepcopy(v) for v in self._by_id.values() if str(v.get("category") or "") == cat]
        out.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def record_run(self, run: dict[str, Any]) -> None:
        with self._lock:
            self._runs.insert(0, deepcopy(run))
            self._runs = self._runs[:100]

    def latest_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._lock:
            return deepcopy(self._runs[: max(1, int(limit))])

    def summary(self) -> dict[str, Any]:
        with self._lock:
            rows = list(self._by_id.values())
        by_cat = {c: 0 for c in LEARNING_CATEGORIES}
        by_outcome = {o: 0 for o in OUTCOME_LABELS}
        for row in rows:
            cat = str(row.get("category") or "")
            if cat in by_cat:
                by_cat[cat] += 1
            out = str(row.get("outcome") or "")
            if out in by_outcome:
                by_outcome[out] += 1
        return {
            "learnings": len(rows),
            "by_category": by_cat,
            "by_outcome": by_outcome,
            "theses_covered": len(self._by_thesis),
            "knowledge_factory_updates": 0,
            "process_memory_only": True,
        }

    def telemetry_snapshot(self) -> dict[str, Any]:
        s = self.summary()
        return {**s, "recent": self.list_recent(limit=8)}


_STORE: LearningStore | None = None
_STORE_LOCK = RLock()


def get_learning_store() -> LearningStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = LearningStore()
        return _STORE


def reset_learning_store_for_tests() -> None:
    global _STORE
    with _STORE_LOCK:
        _STORE = LearningStore()
