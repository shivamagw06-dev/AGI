"""Production usage store for FAPI — retrieval, engine consumption, reasoning traces."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from threading import Lock
from typing import Any


class ProductionUsageStore:
    """In-memory production usage metrics for Admin + audit."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.retrieval_counts: Counter[str] = Counter()
        self.engine_counts: Counter[str] = Counter()
        self.course_counts: Counter[str] = Counter()
        self.traces: list[dict[str, Any]] = []
        self.ab_runs: list[dict[str, Any]] = []
        self.queries_total = 0
        self.finance_queries = 0
        self.bypassed = 0
        self.influenced_answers = 0

    def record_retrieval(
        self,
        *,
        query: str,
        engine: str,
        concept_ids: list[str],
        courses: list[str],
        causal_ids: list[str] | None = None,
        mental_ids: list[str] | None = None,
        influenced: bool = True,
        bypassed: bool = False,
        trace: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            self.queries_total += 1
            if concept_ids or courses:
                self.finance_queries += 1
            if bypassed:
                self.bypassed += 1
            if influenced and concept_ids:
                self.influenced_answers += 1
            eng = (engine or "unknown").lower()
            self.engine_counts[eng] += 1
            for cid in concept_ids:
                self.retrieval_counts[cid] += 1
            for course in courses:
                self.course_counts[course] += 1
            row = {
                "ts": datetime.now(timezone.utc).isoformat(),
                "query": (query or "")[:240],
                "engine": eng,
                "concept_ids": list(concept_ids)[:24],
                "courses": list(courses),
                "causal_ids": list(causal_ids or [])[:12],
                "mental_ids": list(mental_ids or [])[:12],
                "influenced": influenced,
                "bypassed": bypassed,
                "trace": trace or {},
            }
            self.traces.append(row)
            self.traces = self.traces[-200:]

    def record_ab(self, result: dict[str, Any]) -> None:
        with self._lock:
            self.ab_runs.append({"ts": datetime.now(timezone.utc).isoformat(), **result})
            self.ab_runs = self.ab_runs[-50:]

    def most_retrieved(self, limit: int = 25) -> list[dict[str, Any]]:
        with self._lock:
            return [{"concept_id": k, "count": v} for k, v in self.retrieval_counts.most_common(limit)]

    def unused_concepts(self, all_ids: list[str], limit: int = 50) -> list[str]:
        with self._lock:
            used = set(self.retrieval_counts)
        unused = [cid for cid in all_ids if cid not in used]
        return unused[:limit]

    def engine_consumption(self) -> dict[str, int]:
        with self._lock:
            return dict(self.engine_counts)

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return {
                "queries_total": self.queries_total,
                "finance_queries": self.finance_queries,
                "bypassed": self.bypassed,
                "influenced_answers": self.influenced_answers,
                "influence_rate": round(
                    self.influenced_answers / max(self.finance_queries, 1), 4
                ),
                "most_retrieved": [{"concept_id": k, "count": v} for k, v in self.retrieval_counts.most_common(25)],
                "engine_consumption": dict(self.engine_counts),
                "course_counts": dict(self.course_counts),
                "recent_traces": list(reversed(self.traces[-20:])),
                "ab_runs": list(reversed(self.ab_runs[-10:])),
            }

    def reset(self) -> None:
        with self._lock:
            self.retrieval_counts = Counter()
            self.engine_counts = Counter()
            self.course_counts = Counter()
            self.traces = []
            self.ab_runs = []
            self.queries_total = 0
            self.finance_queries = 0
            self.bypassed = 0
            self.influenced_answers = 0


_STORE = ProductionUsageStore()


def get_usage_store() -> ProductionUsageStore:
    return _STORE


def reset_usage_store() -> None:
    get_usage_store().reset()
