"""In-process ORCH run ledger (WBS ORCH-001).

Persists to memory for unit tests; SQL schema lives in supabase migrations.
Full DB-backed executor arrives in later ORCH-* tasks.
"""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

DAG_PATH = Path(__file__).resolve().parent / "dag" / "orch-1.0.0.json"

RunStatus = Literal[
    "queued",
    "running",
    "succeeded",
    "degraded",
    "failed",
    "timed_out",
    "skipped",
    "already_running",
]


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class OrchNodeRecord:
    node_id: str
    status: RunStatus
    attempt: int = 1
    latency_ms: int | None = None
    input_hash: str | None = None
    output_hash: str | None = None
    error_code: str | None = None
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass
class OrchRunRecord:
    run_id: str
    run_kind: str
    dag_version: str
    status: RunStatus
    started_at: datetime
    finished_at: datetime | None = None
    as_of: str | None = None
    trigger_reason: str | None = None
    nodes: dict[str, OrchNodeRecord] = field(default_factory=dict)


class OrchLedger:
    """Thread-safe in-memory ledger with EOD lock semantics."""

    def __init__(self, dag_path: Path | None = None) -> None:
        self._dag_path = dag_path or DAG_PATH
        self._lock = threading.RLock()
        self._runs: dict[str, OrchRunRecord] = {}
        self._active_kinds: set[str] = set()
        self._dag = json.loads(self._dag_path.read_text(encoding="utf-8"))

    @property
    def dag_version(self) -> str:
        return str(self._dag["dag_version"])

    def dag_node_ids(self) -> list[str]:
        return [str(node["node_id"]) for node in self._dag["nodes"]]

    def trigger(
        self,
        run_kind: str,
        *,
        as_of: str | None = None,
        trigger_reason: str | None = None,
        allow_parallel: bool = False,
    ) -> OrchRunRecord:
        """Create a run. Duplicate non-parallel kinds return already_running."""
        with self._lock:
            if not allow_parallel and run_kind in self._active_kinds:
                existing = next(
                    (
                        run
                        for run in reversed(list(self._runs.values()))
                        if run.run_kind == run_kind and run.status == "running"
                    ),
                    None,
                )
                if existing:
                    return OrchRunRecord(
                        run_id=existing.run_id,
                        run_kind=run_kind,
                        dag_version=self.dag_version,
                        status="already_running",
                        started_at=existing.started_at,
                        as_of=as_of,
                        trigger_reason=trigger_reason or "duplicate_trigger",
                    )

            run_id = str(uuid4())
            run = OrchRunRecord(
                run_id=run_id,
                run_kind=run_kind,
                dag_version=self.dag_version,
                status="running",
                started_at=_utcnow(),
                as_of=as_of,
                trigger_reason=trigger_reason,
            )
            self._runs[run_id] = run
            if not allow_parallel:
                self._active_kinds.add(run_kind)
            return run

    def complete_node(
        self,
        run_id: str,
        node_id: str,
        status: RunStatus,
        *,
        latency_ms: int | None = None,
        input_hash: str | None = None,
        output_hash: str | None = None,
        error_code: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> OrchNodeRecord:
        with self._lock:
            run = self._runs[run_id]
            if node_id not in self.dag_node_ids():
                raise KeyError(f"Unknown ORCH node_id: {node_id}")
            record = OrchNodeRecord(
                node_id=node_id,
                status=status,
                latency_ms=latency_ms,
                input_hash=input_hash,
                output_hash=output_hash,
                error_code=error_code,
                detail=detail or {},
            )
            run.nodes[node_id] = record
            return record

    def finish(self, run_id: str, status: RunStatus) -> OrchRunRecord:
        with self._lock:
            run = self._runs[run_id]
            run.status = status
            run.finished_at = _utcnow()
            self._active_kinds.discard(run.run_kind)
            return run

    def get(self, run_id: str) -> OrchRunRecord | None:
        with self._lock:
            return self._runs.get(run_id)

    def status_summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "ok": True,
                "service": "orch",
                "document_id": "ORCH",
                "dag_version": self.dag_version,
                "active_run_kinds": sorted(self._active_kinds),
                "runs_tracked": len(self._runs),
                "node_count": len(self.dag_node_ids()),
            }
