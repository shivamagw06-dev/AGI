"""ORCH Layer 2 — Feature Build DAG executor (ORCH-003–005).

MarketData updates → dirty detection → dependency-aware incremental recompute.
Research engines remain passive consumers of FeatureSnapshots.
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from dataclasses import dataclass, field
from typing import Any, Callable
from uuid import uuid4

from app.core.logging import get_logger
from app.features.graph import DependencyCycleError
from app.features.models import FeatureSnapshot, FeatureValue
from app.features.service import FeatureRegistryService
from app.orch.l2.dirty import DirtyFeatureTracker
from app.orch.l2.ledger import FeatureBuildLedger
from app.orch.l2.metrics import L2Metrics
from app.orch.l2.models import (
    FeatureBuildRecord,
    FeatureReadyEvent,
    MarketDataUpdateEvent,
)
from app.orch.l2.queue import FeatureBuildQueue
from app.orch.ledger import OrchLedger

log = get_logger(__name__)

ReadyHandler = Callable[[FeatureReadyEvent], None]


@dataclass
class BatchResult:
    batch_id: str
    orch_run_id: str | None
    as_of: str
    symbol: str | None
    impacted: list[str]
    snapshot: FeatureSnapshot | None
    builds: list[FeatureBuildRecord] = field(default_factory=list)
    ready: FeatureReadyEvent | None = None
    status: str = "succeeded"


class L2FeatureBuildService:
    """ORCH L2 scheduler: dirty tracking, queue, topo/parallel builds, ledger, retry."""

    NODE_ID = "L2_FEATURES"

    def __init__(
        self,
        features: FeatureRegistryService,
        *,
        orch_ledger: OrchLedger | None = None,
        max_attempts: int = 3,
        feature_timeout_s: float = 5.0,
        default_workers: int = 4,
    ) -> None:
        self.features = features
        self.orch_ledger = orch_ledger or OrchLedger()
        self.dirty = DirtyFeatureTracker(features)
        self.queue = FeatureBuildQueue()
        self.build_ledger = FeatureBuildLedger()
        self.metrics = L2Metrics()
        self.max_attempts = max_attempts
        self.feature_timeout_s = feature_timeout_s
        self.default_workers = default_workers
        self._ready_handlers: list[ReadyHandler] = []
        self._lock = threading.Lock()
        # Latest batch snapshots for passive engine consumers (E01, …)
        self._last_snapshots: dict[str, FeatureSnapshot] = {}

    def on_ready(self, handler: ReadyHandler) -> None:
        self._ready_handlers.append(handler)

    def on_market_data_update(
        self,
        event: MarketDataUpdateEvent,
        *,
        ctx: dict[str, Any] | None = None,
        drain: bool = True,
        parallel: bool = True,
        max_workers: int | None = None,
    ) -> BatchResult | None:
        """MarketDataClient → ORCH trigger → dirty → schedule."""
        seeds = self.dirty.seeds_for_update(event)
        self.dirty.mark(event, seeds)
        if not seeds:
            log.info(
                "l2_no_dirty_seeds",
                extra={"extra": {"update_type": event.update_type, "symbol": event.symbol}},
            )
            return None
        self.queue.enqueue(
            as_of=event.as_of,
            symbol=event.symbol,
            feature_ids=seeds,
            ctx=ctx,
            update_type=event.update_type,
        )
        if not drain:
            return None
        return self.drain(parallel=parallel, max_workers=max_workers or self.default_workers)

    def enqueue_manual(
        self,
        *,
        as_of: str,
        symbol: str | None,
        feature_ids: list[str] | None = None,
        ctx: dict[str, Any] | None = None,
    ) -> str:
        if feature_ids is None:
            feature_ids = list(self.features._calculators.keys())
        self.dirty.mark_features(symbol=symbol, as_of=as_of, feature_ids=feature_ids)
        job = self.queue.enqueue(
            as_of=as_of,
            symbol=symbol,
            feature_ids=feature_ids,
            ctx=ctx,
            update_type="manual",
        )
        return job.job_id

    def drain(self, *, parallel: bool = True, max_workers: int | None = None) -> BatchResult | None:
        job = self.queue.pop()
        if job is None:
            return None
        return self.execute_job(job, parallel=parallel, max_workers=max_workers or self.default_workers)

    def execute_job(
        self,
        job: Any,
        *,
        parallel: bool = True,
        max_workers: int = 4,
    ) -> BatchResult:
        batch_id = str(uuid4())
        timer0 = time.perf_counter()
        seeds = set(job.feature_ids) | self.dirty.snapshot(symbol=job.symbol, as_of=job.as_of)
        impacted = self.features.graph.impacted_set(seeds)
        # Only calculators
        impacted = {fid for fid in impacted if fid in self.features._calculators}
        try:
            waves = self.features.graph.parallel_waves(impacted) if impacted else []
        except DependencyCycleError:
            raise

        # Invalidate only impacted (not unrelated)
        for fid in impacted:
            self.features.cache.invalidate_prefix(fid)

        orch_run = self.orch_ledger.trigger(
            "l2_feature_build",
            as_of=job.as_of,
            trigger_reason=f"update:{job.update_type}",
            allow_parallel=True,
        )

        builds: list[FeatureBuildRecord] = []
        succeeded: list[str] = []
        failed: list[str] = []
        skipped: list[str] = []
        values: dict[str, FeatureValue] = {}
        blocked: set[str] = set()

        input_snapshot = {
            "update_type": job.update_type,
            "ctx_keys": sorted((job.ctx or {}).keys()),
            "ctx_fingerprint": _fingerprint(job.ctx or {}),
            "seeds": sorted(seeds),
            "impacted": sorted(impacted),
        }

        for wave in waves:
            runnable = [fid for fid in wave if fid not in blocked]
            for fid in wave:
                if fid in blocked:
                    skipped.append(fid)
                    builds.append(
                        self._ledger_row(
                            batch_id=batch_id,
                            orch_run_id=orch_run.run_id,
                            feature_id=fid,
                            symbol=job.symbol,
                            as_of=job.as_of,
                            status="skipped",
                            error="upstream_failed",
                            input_snapshot=input_snapshot,
                            attempt=1,
                        )
                    )

            if not runnable:
                continue

            if parallel and len(runnable) > 1:
                results = self._run_wave_parallel(
                    runnable,
                    symbol=job.symbol,
                    as_of=job.as_of,
                    ctx=job.ctx,
                    batch_id=batch_id,
                    orch_run_id=orch_run.run_id,
                    input_snapshot=input_snapshot,
                    max_workers=max_workers,
                )
            else:
                results = [
                    self._run_one_with_retry(
                        fid,
                        symbol=job.symbol,
                        as_of=job.as_of,
                        ctx=job.ctx,
                        batch_id=batch_id,
                        orch_run_id=orch_run.run_id,
                        input_snapshot=input_snapshot,
                    )
                    for fid in runnable
                ]

            for fid, record, value in results:
                builds.append(record)
                if record.status == "succeeded" and value is not None:
                    succeeded.append(fid)
                    values[fid] = value
                elif record.status == "timed_out":
                    failed.append(fid)
                    blocked |= self.features.graph.transitive_dependents(fid)
                else:
                    failed.append(fid)
                    blocked |= self.features.graph.transitive_dependents(fid)

        snapshot = FeatureSnapshot(
            snapshot_id=str(uuid4()),
            as_of=job.as_of,
            symbol=job.symbol,
            values=values,
        )
        self._last_snapshots[snapshot.snapshot_id] = snapshot
        while len(self._last_snapshots) > 32:
            oldest = next(iter(self._last_snapshots))
            del self._last_snapshots[oldest]

        status = "succeeded"
        if failed and succeeded:
            status = "degraded"
        elif failed and not succeeded:
            status = "failed"

        self.orch_ledger.complete_node(
            orch_run.run_id,
            self.NODE_ID,
            "succeeded" if status == "succeeded" else ("degraded" if status == "degraded" else "failed"),
            latency_ms=int((time.perf_counter() - timer0) * 1000),
            detail={
                "batch_id": batch_id,
                "impacted": sorted(impacted),
                "succeeded": succeeded,
                "failed": failed,
                "skipped": skipped,
            },
        )
        self.orch_ledger.finish(
            orch_run.run_id,
            "succeeded" if status == "succeeded" else ("degraded" if status == "degraded" else "failed"),
        )

        ready = FeatureReadyEvent(
            batch_id=batch_id,
            as_of=job.as_of,
            symbol=job.symbol,
            feature_ids=sorted(impacted),
            snapshot_id=snapshot.snapshot_id,
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
        )
        self.metrics.record_ready()
        for handler in self._ready_handlers:
            try:
                handler(ready)
            except Exception as exc:  # isolation: ready handlers must not break L2
                log.warning("l2_ready_handler_failed", extra={"extra": {"error": str(exc)}})

        self.dirty.clear(symbol=job.symbol, as_of=job.as_of, feature_ids=impacted)
        duration_ms = (time.perf_counter() - timer0) * 1000
        self.metrics.record_batch(
            built=len(succeeded),
            failed=len(failed),
            skipped=len(skipped),
            duration_ms=duration_ms,
        )

        return BatchResult(
            batch_id=batch_id,
            orch_run_id=orch_run.run_id,
            as_of=job.as_of,
            symbol=job.symbol,
            impacted=sorted(impacted),
            snapshot=snapshot,
            builds=builds,
            ready=ready,
            status=status,
        )

    def _run_wave_parallel(
        self,
        feature_ids: list[str],
        *,
        symbol: str | None,
        as_of: str,
        ctx: dict[str, Any],
        batch_id: str,
        orch_run_id: str,
        input_snapshot: dict[str, Any],
        max_workers: int,
    ) -> list[tuple[str, FeatureBuildRecord, FeatureValue | None]]:
        out: list[tuple[str, FeatureBuildRecord, FeatureValue | None]] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futures = {
                pool.submit(
                    self._run_one_with_retry,
                    fid,
                    symbol=symbol,
                    as_of=as_of,
                    ctx=ctx,
                    batch_id=batch_id,
                    orch_run_id=orch_run_id,
                    input_snapshot=input_snapshot,
                ): fid
                for fid in feature_ids
            }
            for fut, fid in futures.items():
                try:
                    out.append(fut.result())
                except Exception as exc:
                    record = self._ledger_row(
                        batch_id=batch_id,
                        orch_run_id=orch_run_id,
                        feature_id=fid,
                        symbol=symbol,
                        as_of=as_of,
                        status="failed",
                        error=str(exc),
                        input_snapshot=input_snapshot,
                        attempt=self.max_attempts,
                    )
                    out.append((fid, record, None))
        return out

    def _run_one_with_retry(
        self,
        feature_id: str,
        *,
        symbol: str | None,
        as_of: str,
        ctx: dict[str, Any],
        batch_id: str,
        orch_run_id: str,
        input_snapshot: dict[str, Any],
    ) -> tuple[str, FeatureBuildRecord, FeatureValue | None]:
        last_error: str | None = None
        for attempt in range(1, self.max_attempts + 1):
            t0 = time.perf_counter()
            try:
                with ThreadPoolExecutor(max_workers=1) as pool:
                    fut = pool.submit(
                        self.features.recompute_impacted,
                        {feature_id},
                        symbol=symbol,
                        as_of=as_of,
                        ctx=ctx,
                    )
                    try:
                        snap = fut.result(timeout=self.feature_timeout_s)
                    except FuturesTimeout:
                        self.metrics.record_timeout()
                        duration = (time.perf_counter() - t0) * 1000
                        record = self._ledger_row(
                            batch_id=batch_id,
                            orch_run_id=orch_run_id,
                            feature_id=feature_id,
                            symbol=symbol,
                            as_of=as_of,
                            status="timed_out",
                            error=f"timeout>{self.feature_timeout_s}s",
                            input_snapshot=input_snapshot,
                            attempt=attempt,
                            duration_ms=duration,
                        )
                        return feature_id, record, None

                value = snap.values.get(feature_id)
                duration = (time.perf_counter() - t0) * 1000
                record = self._ledger_row(
                    batch_id=batch_id,
                    orch_run_id=orch_run_id,
                    feature_id=feature_id,
                    symbol=symbol,
                    as_of=as_of,
                    status="succeeded",
                    error=None,
                    input_snapshot=input_snapshot,
                    attempt=attempt,
                    duration_ms=duration,
                )
                return feature_id, record, value
            except Exception as exc:
                last_error = str(exc)
                if attempt < self.max_attempts:
                    self.metrics.record_retry()
                    continue
                duration = (time.perf_counter() - t0) * 1000
                record = self._ledger_row(
                    batch_id=batch_id,
                    orch_run_id=orch_run_id,
                    feature_id=feature_id,
                    symbol=symbol,
                    as_of=as_of,
                    status="failed",
                    error=last_error,
                    input_snapshot=input_snapshot,
                    attempt=attempt,
                    duration_ms=duration,
                )
                return feature_id, record, None

        record = self._ledger_row(
            batch_id=batch_id,
            orch_run_id=orch_run_id,
            feature_id=feature_id,
            symbol=symbol,
            as_of=as_of,
            status="failed",
            error=last_error or "unknown",
            input_snapshot=input_snapshot,
            attempt=self.max_attempts,
        )
        return feature_id, record, None

    def _ledger_row(
        self,
        *,
        batch_id: str,
        orch_run_id: str,
        feature_id: str,
        symbol: str | None,
        as_of: str,
        status: str,
        error: str | None,
        input_snapshot: dict[str, Any],
        attempt: int,
        duration_ms: float | None = None,
    ) -> FeatureBuildRecord:
        meta = self.features.get_metadata(feature_id)
        row = FeatureBuildRecord(
            build_id=str(uuid4()),
            feature_id=feature_id,
            formula_version=meta.formula_version if meta else "unknown",
            input_snapshot=input_snapshot,
            duration_ms=duration_ms,
            status=status,  # type: ignore[arg-type]
            error=error,
            symbol=symbol,
            as_of=as_of,
            attempt=attempt,
            batch_id=batch_id,
            orch_run_id=orch_run_id,
        )
        self.build_ledger.record(row)
        return row

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "orch-l2-features",
            "node_id": self.NODE_ID,
            "dirty": self.dirty.stats(),
            "queue": self.queue.stats(),
            "ledger": self.build_ledger.stats(),
            "metrics": self.metrics.snapshot(),
            "orch": self.orch_ledger.status_summary(),
        }


def _fingerprint(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
