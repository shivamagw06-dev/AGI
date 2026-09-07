"""Feature build queue with duplicate suppression (ORCH-004)."""

from __future__ import annotations

import threading
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4


@dataclass
class BuildJob:
    job_id: str
    as_of: str
    symbol: str | None
    feature_ids: set[str]
    ctx: dict[str, Any] = field(default_factory=dict)
    update_type: str = "manual"
    suppressed_duplicates: int = 0


class FeatureBuildQueue:
    """FIFO build queue keyed by (symbol, as_of) for duplicate suppression."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._pending: OrderedDict[str, BuildJob] = OrderedDict()
        self.enqueued = 0
        self.suppressed = 0
        self.drained = 0

    @staticmethod
    def _key(symbol: str | None, as_of: str) -> str:
        return f"{symbol or ''}|{as_of}"

    def enqueue(
        self,
        *,
        as_of: str,
        symbol: str | None,
        feature_ids: set[str] | list[str],
        ctx: dict[str, Any] | None = None,
        update_type: str = "manual",
    ) -> BuildJob:
        key = self._key(symbol, as_of)
        ids = set(feature_ids)
        with self._lock:
            existing = self._pending.get(key)
            if existing is not None:
                before = len(existing.feature_ids)
                existing.feature_ids |= ids
                existing.suppressed_duplicates += 1
                if ctx:
                    existing.ctx.update(ctx)
                self.suppressed += 1
                # Count only newly added ids as not fully suppressed when merge grows set
                if len(existing.feature_ids) == before:
                    pass
                return existing

            job = BuildJob(
                job_id=str(uuid4()),
                as_of=as_of,
                symbol=symbol,
                feature_ids=ids,
                ctx=dict(ctx or {}),
                update_type=update_type,
            )
            self._pending[key] = job
            self.enqueued += 1
            return job

    def pop(self) -> BuildJob | None:
        with self._lock:
            if not self._pending:
                return None
            _, job = self._pending.popitem(last=False)
            self.drained += 1
            return job

    def peek_all(self) -> list[BuildJob]:
        with self._lock:
            return list(self._pending.values())

    def size(self) -> int:
        with self._lock:
            return len(self._pending)

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "pending": len(self._pending),
                "enqueued": self.enqueued,
                "suppressed": self.suppressed,
                "drained": self.drained,
            }
