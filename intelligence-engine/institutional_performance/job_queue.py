"""In-process background job queue with optional Redis-backed depth signal (PRP-01)."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Dict, List, Optional

from institutional_performance.flags import async_publication_enabled, max_workers
from institutional_performance.schema import JOB_KINDS, PRP_01_ID

logger = logging.getLogger(__name__)

Handler = Callable[[Dict[str, Any]], Any]


@dataclass
class JobRecord:
    job_id: str
    kind: str
    status: str  # queued | running | completed | failed
    payload: Dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BackgroundJobQueue:
    """Thread-pool job queue for async publication and graph updates."""

    def __init__(self, workers: Optional[int] = None) -> None:
        self._workers = int(workers or max_workers())
        self._executor = ThreadPoolExecutor(
            max_workers=self._workers, thread_name_prefix="prp01-worker"
        )
        self._lock = threading.Lock()
        self._jobs: Dict[str, JobRecord] = {}
        self._handlers: Dict[str, Handler] = {}
        self._queued = 0
        self._active = 0
        self._completed = 0
        self._failed = 0

    def register(self, kind: str, handler: Handler) -> None:
        if kind not in JOB_KINDS:
            raise ValueError(f"unknown job kind: {kind}")
        self._handlers[kind] = handler

    def enqueue(self, kind: str, payload: Optional[Dict[str, Any]] = None) -> JobRecord:
        if kind not in self._handlers:
            raise ValueError(f"no handler registered for kind={kind}")
        job = JobRecord(
            job_id=f"job_{uuid.uuid4().hex[:12]}",
            kind=kind,
            status="queued",
            payload=dict(payload or {}),
        )
        with self._lock:
            self._jobs[job.job_id] = job
            self._queued += 1
        fut: Future = self._executor.submit(self._run, job.job_id)
        fut.add_done_callback(lambda _f: None)
        return job

    def _run(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if not job:
                return
            job.status = "running"
            job.started_at = time.time()
            self._queued = max(0, self._queued - 1)
            self._active += 1
            handler = self._handlers.get(job.kind)
            payload = dict(job.payload)
        try:
            assert handler is not None
            result = handler(payload)
            with self._lock:
                job.result = result
                job.status = "completed"
                job.completed_at = time.time()
                self._active = max(0, self._active - 1)
                self._completed += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "PRP-01 job failed kind=%s id=%s",
                job.kind if job else "?",
                job_id,
            )
            with self._lock:
                job = self._jobs.get(job_id)
                if job:
                    job.status = "failed"
                    job.error = str(exc)
                    job.completed_at = time.time()
                self._active = max(0, self._active - 1)
                self._failed += 1

    def get(self, job_id: str) -> Optional[JobRecord]:
        with self._lock:
            return self._jobs.get(job_id)

    def list_jobs(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock:
            rows = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)
        return [j.to_dict() for j in rows[:limit]]

    def depth(self) -> int:
        with self._lock:
            return self._queued

    def active_workers(self) -> int:
        with self._lock:
            return self._active

    def stats(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "id": PRP_01_ID,
                "max_workers": self._workers,
                "queue_depth": self._queued,
                "active_workers": self._active,
                "completed": self._completed,
                "failed": self._failed,
                "job_count": len(self._jobs),
                "async_publication_enabled": async_publication_enabled(),
                "registered_kinds": sorted(self._handlers.keys()),
            }

    def shutdown(self, wait: bool = False) -> None:
        self._executor.shutdown(wait=wait)


_QUEUE: Optional[BackgroundJobQueue] = None
_QUEUE_LOCK = threading.Lock()


def get_queue() -> BackgroundJobQueue:
    global _QUEUE
    with _QUEUE_LOCK:
        if _QUEUE is None:
            _QUEUE = BackgroundJobQueue()
            _register_default_handlers(_QUEUE)
        return _QUEUE


def reset_queue_for_tests() -> None:
    global _QUEUE
    with _QUEUE_LOCK:
        if _QUEUE is not None:
            _QUEUE.shutdown(wait=False)
        _QUEUE = None


def _register_default_handlers(q: BackgroundJobQueue) -> None:
    def _publication(payload: Dict[str, Any]) -> Any:
        from institutional_publishing.production import generate

        # Force sync path inside worker to avoid re-enqueue loops
        body = dict(payload)
        body["async"] = False
        body["_prp_worker"] = True
        return generate(body)

    def _graph_incremental(payload: Dict[str, Any]) -> Any:
        from institutional_performance.graph_incremental import apply_incremental_update

        return apply_incremental_update(payload)

    def _cache_warmup(payload: Dict[str, Any]) -> Any:
        from institutional_performance.cache import object_cache, workspace_cache

        ns = str(payload.get("namespace") or "object")
        key = payload.get("key") or "warm"
        value = payload.get("value") or {"warmed": True}
        ttl = int(payload.get("ttl_seconds") or 300)
        if ns == "workspace":
            workspace_cache().set(key, value, ttl_seconds=ttl)
        else:
            object_cache().set(key, value, ttl_seconds=ttl)
        return {"warmed": True, "namespace": ns, "key": key}

    def _orchestrate_parallel(payload: Dict[str, Any]) -> Any:
        from institutional_performance.parallel import run_parallel

        # Payload carries named no-op markers for queue smoke tests
        names = list(payload.get("tasks") or ["a", "b"])
        tasks = {n: (lambda name=n: {"task": name, "ok": True}) for n in names}
        return run_parallel(tasks)

    q.register("publication_generate", _publication)
    q.register("graph_incremental", _graph_incremental)
    q.register("cache_warmup", _cache_warmup)
    q.register("orchestrate_parallel", _orchestrate_parallel)


def enqueue_publication(payload: Dict[str, Any]) -> Dict[str, Any]:
    job = get_queue().enqueue("publication_generate", payload)
    return job.to_dict()


def job_status(job_id: str) -> Optional[Dict[str, Any]]:
    job = get_queue().get(job_id)
    return job.to_dict() if job else None
