"""In-memory Monitoring Event registry (Sprint 5.4)."""

from __future__ import annotations

from copy import deepcopy
from threading import RLock
from typing import Any

from institutional_monitoring_office.schema import (
    EVENT_FIELDS,
    MONITOR_DOMAINS,
    RECOMMENDED_ACTIONS,
    SEVERITIES,
)


class MonitoringEventStore:
    def __init__(self) -> None:
        self._lock = RLock()
        self._by_id: dict[str, dict[str, Any]] = {}
        self._by_idea: dict[str, list[str]] = {}
        self._by_thesis: dict[str, list[str]] = {}
        self._by_decision: dict[str, list[str]] = {}
        self._prior_confidence: dict[str, float] = {}
        self._runs: list[dict[str, Any]] = []

    def upsert(self, event: dict[str, Any]) -> dict[str, Any]:
        with self._lock:
            eid = str(event.get("event_id") or "").strip()
            if not eid:
                raise ValueError("event_id is required")
            stored = {k: deepcopy(event.get(k)) for k in EVENT_FIELDS if k in event}
            for key in EVENT_FIELDS:
                stored.setdefault(key, None if key != "requires_review" else True)
            stored["event_id"] = eid
            stored.setdefault("schema_version", "1.0.0")
            # Preserve optional explainability fields outside core schema
            for extra in ("explanation", "domains_covered", "mutates_thesis", "mutates_decision", "mutates_portfolio"):
                if extra in event:
                    stored[extra] = deepcopy(event[extra])
            self._by_id[eid] = stored
            idea = str(stored.get("portfolio_idea") or "").strip()
            if idea:
                bucket = self._by_idea.setdefault(idea, [])
                if eid not in bucket:
                    bucket.append(eid)
            thesis = str(stored.get("affected_thesis") or "").strip()
            if thesis:
                bucket = self._by_thesis.setdefault(thesis, [])
                if eid not in bucket:
                    bucket.append(eid)
            decision = str(stored.get("affected_decision") or "").strip()
            if decision:
                bucket = self._by_decision.setdefault(decision, [])
                if eid not in bucket:
                    bucket.append(eid)
            return deepcopy(stored)

    def get(self, event_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._by_id.get(str(event_id or "").strip())
            return deepcopy(row) if row else None

    def list_for_idea(self, idea_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            ids = list(self._by_idea.get(str(idea_id or "").strip(), []))
            out = [deepcopy(self._by_id[i]) for i in ids if i in self._by_id]
        out.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def list_for_thesis(self, thesis_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            ids = list(self._by_thesis.get(str(thesis_id or "").strip(), []))
            out = [deepcopy(self._by_id[i]) for i in ids if i in self._by_id]
        out.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def list_for_decision(self, decision_id: str, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            ids = list(self._by_decision.get(str(decision_id or "").strip(), []))
            out = [deepcopy(self._by_id[i]) for i in ids if i in self._by_id]
        out.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def list_requiring_review(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            out = [deepcopy(v) for v in self._by_id.values() if bool(v.get("requires_review"))]
        out.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def list_recent(self, *, limit: int = 50) -> list[dict[str, Any]]:
        with self._lock:
            out = [deepcopy(v) for v in self._by_id.values()]
        out.sort(key=lambda r: str(r.get("timestamp") or ""), reverse=True)
        return out[: max(1, int(limit))]

    def get_prior_confidence(self, idea_id: str) -> float | None:
        with self._lock:
            key = str(idea_id or "").strip()
            if key not in self._prior_confidence:
                return None
            return float(self._prior_confidence[key])

    def set_prior_confidence(self, idea_id: str, confidence: float) -> None:
        with self._lock:
            self._prior_confidence[str(idea_id or "").strip()] = float(confidence)

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
            ideas_covered = len(self._by_idea)
        by_severity = {s: 0 for s in SEVERITIES}
        by_action = {a: 0 for a in RECOMMENDED_ACTIONS}
        by_domain = {d: 0 for d in MONITOR_DOMAINS}
        review_n = 0
        for row in rows:
            sev = str(row.get("severity") or "")
            if sev in by_severity:
                by_severity[sev] += 1
            act = str(row.get("recommended_action") or "")
            if act in by_action:
                by_action[act] += 1
            trig = row.get("trigger") if isinstance(row.get("trigger"), dict) else {}
            domain = str(trig.get("domain") or "")
            if domain in by_domain:
                by_domain[domain] += 1
            if bool(row.get("requires_review")):
                review_n += 1
        return {
            "events": len(rows),
            "requires_review": review_n,
            "by_severity": by_severity,
            "by_recommended_action": by_action,
            "by_domain": by_domain,
            "ideas_covered": ideas_covered,
            "domains_defined": len(MONITOR_DOMAINS),
        }

    def telemetry_snapshot(self) -> dict[str, Any]:
        s = self.summary()
        return {
            **s,
            "recent": self.list_recent(limit=8),
            "review_queue": self.list_requiring_review(limit=8),
        }


_STORE: MonitoringEventStore | None = None
_STORE_LOCK = RLock()


def get_monitoring_store() -> MonitoringEventStore:
    global _STORE
    with _STORE_LOCK:
        if _STORE is None:
            _STORE = MonitoringEventStore()
        return _STORE


def reset_monitoring_store_for_tests() -> None:
    global _STORE
    with _STORE_LOCK:
        _STORE = MonitoringEventStore()
