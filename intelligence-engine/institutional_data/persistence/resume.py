"""ResumeManager — recover backfill progress after unexpected shutdown."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from institutional_data.persistence.checkpoint import CheckpointManager
from institutional_data.persistence.queue_persistence import QueuePersistence


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ResumeManager:
    """Ensures historical backfill never restarts from zero after a crash."""

    CHUNK_CK = "chunked_backfill"
    RUN_CK = "backfill_run_state"

    def __init__(self) -> None:
        self.ck = CheckpointManager()
        self.qp = QueuePersistence()

    def recover(self) -> dict[str, Any]:
        """Reset stuck running rows and restore chunk cursors."""
        q = self.qp.load_queue()
        companies = list(q.get("companies") or [])
        reset = 0
        for row in companies:
            if str(row.get("status")) == "running":
                # Crash mid-run → re-queue with same coverage (resume, don't restart zero)
                row["status"] = "pending"
                row["resume_after_crash"] = True
                row["last_error"] = "recovered_from_unexpected_shutdown"
                reset += 1
        if reset:
            self.qp.save_queue({**q, "companies": companies})
            try:
                from knowledge_factory.historical_depth import queue as bf_queue

                bf_queue.save_queue({**q, "companies": companies})
            except Exception:
                pass

        chunks = self.ck.load(self.CHUNK_CK)
        run = self.ck.load(self.RUN_CK)
        engine = self.qp.load_engine()
        report = {
            "recovered_at": _now(),
            "stuck_running_reset": reset,
            "queue_length": len(
                [c for c in companies if str(c.get("status")) in {"pending", "failed", "cooldown", "running"}]
            ),
            "chunk_checkpoints": len((chunks.get("companies") or {})),
            "engine_mode": engine.get("mode"),
            "last_run": run.get("updated_at"),
            "resumed": True,
            "never_restart_from_zero": True,
        }
        self.ck.save(self.RUN_CK, {**run, "last_recovery": report})
        return report

    def company_chunk_state(self, company: str) -> dict[str, Any]:
        chunks = self.ck.load(self.CHUNK_CK)
        companies = chunks.get("companies") or {}
        return dict(companies.get(company.upper()) or {})

    def save_company_chunk(
        self,
        company: str,
        *,
        chunk_start_year: int | None = None,
        chunk_end_year: int | None = None,
        completed_chunks: list[str] | None = None,
        next_chunk: str | None = None,
        partial: bool = False,
        meta: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = self.ck.path_for(self.CHUNK_CK)
        from institutional_data.persistence.atomic import atomic_write_json, file_lock

        with file_lock(path):
            chunks = self.ck.load(self.CHUNK_CK)
            companies = dict(chunks.get("companies") or {})
            cur = dict(companies.get(company.upper()) or {})
            if completed_chunks is not None:
                prev = list(cur.get("completed_chunks") or [])
                for c in completed_chunks:
                    if c not in prev:
                        prev.append(c)
                cur["completed_chunks"] = prev
            if chunk_start_year is not None:
                cur["chunk_start_year"] = chunk_start_year
            if chunk_end_year is not None:
                cur["chunk_end_year"] = chunk_end_year
            if next_chunk is not None:
                cur["next_chunk"] = next_chunk
            cur["partial"] = partial
            cur["updated_at"] = _now()
            if meta:
                cur["meta"] = {**(cur.get("meta") or {}), **meta}
            companies[company.upper()] = cur
            body = {"companies": companies, "updated_at": _now()}
            atomic_write_json(path, body)
            return cur

    def status(self) -> dict[str, Any]:
        q = self.qp.load_queue()
        chunks = self.ck.load(self.CHUNK_CK)
        storage = self.ck.storage_usage()
        return {
            "queue_updated_at": q.get("updated_at"),
            "queue_companies": len(q.get("companies") or []),
            "chunk_companies": len((chunks.get("companies") or {})),
            "checkpoints": self.ck.list_checkpoints(),
            "storage": storage,
            "durable_root": str(self.ck.root),
        }
