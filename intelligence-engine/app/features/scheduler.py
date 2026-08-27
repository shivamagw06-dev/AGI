"""Calculation Scheduler — topo-ordered feature builds by refresh frequency (FEAT-004)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any, Callable, Iterable

from app.features.calculators.base import FeatureContext
from app.features.models import FeatureSnapshot


@dataclass(frozen=True)
class SchedulePlan:
    """Ordered compute plan. Dependencies appear before dependents — no duplicate IDs."""

    as_of: str
    refresh_frequency: str | None
    feature_ids: list[str]
    symbols: list[str | None] = field(default_factory=lambda: [None])


@dataclass
class ScheduleRunResult:
    plans_executed: int
    features_computed: int
    snapshots: list[FeatureSnapshot]
    invalidated: dict[str, int] = field(default_factory=dict)


class CalculationScheduler:
    """
    Schedules Feature Registry recomputation.

    - Groups by metadata.refresh_frequency
    - Expands transitive dependencies once (topo order)
    - Incremental: cache + store reuse inside FeatureRegistryService.compute*
    - Invalidation: callers may invalidate seeds before run
    """

    def __init__(self, service: Any) -> None:
        self._service = service
        self._last_run: dict[str, datetime] = {}

    def features_for_frequency(self, refresh_frequency: str) -> list[str]:
        ids = [
            m.feature_id
            for m in self._service.list_features()
            if m.refresh_frequency == refresh_frequency and m.feature_id in self._service._calculators
        ]
        return self._service.dependency_order(ids)

    def plan(
        self,
        *,
        as_of: date | datetime | str,
        refresh_frequency: str | None = None,
        feature_ids: list[str] | None = None,
        symbols: Iterable[str | None] | None = None,
    ) -> SchedulePlan:
        as_of_s = _as_of_str(as_of)
        if feature_ids is not None:
            seeds = list(feature_ids)
        elif refresh_frequency is not None:
            seeds = [
                m.feature_id
                for m in self._service.list_features()
                if m.refresh_frequency == refresh_frequency
                and m.feature_id in self._service._calculators
            ]
        else:
            seeds = list(self._service._calculators.keys())
        order = self._service.dependency_order(seeds) if seeds else []
        syms = list(symbols) if symbols is not None else [None]
        return SchedulePlan(
            as_of=as_of_s,
            refresh_frequency=refresh_frequency,
            feature_ids=order,
            symbols=syms or [None],
        )

    def run(
        self,
        plan: SchedulePlan,
        *,
        ctx: FeatureContext | dict[str, Any] | None = None,
        ctx_for_symbol: Callable[[str | None], FeatureContext | dict[str, Any]] | None = None,
        invalidate_seeds: list[str] | None = None,
    ) -> ScheduleRunResult:
        """Execute plan: optional seed invalidation, then compute_many per symbol."""
        invalidated: dict[str, int] = {}
        if invalidate_seeds:
            for seed in invalidate_seeds:
                stats = self._service.invalidate(seed)
                invalidated[seed] = stats["feature"] + stats["dependents"]

        snapshots: list[FeatureSnapshot] = []
        computed = 0
        if not plan.feature_ids:
            return ScheduleRunResult(
                plans_executed=0,
                features_computed=0,
                snapshots=[],
                invalidated=invalidated,
            )

        for symbol in plan.symbols:
            local_ctx = ctx_for_symbol(symbol) if ctx_for_symbol else ctx
            snap = self._service.compute_many(
                plan.feature_ids,
                symbol=symbol,
                as_of=plan.as_of,
                ctx=local_ctx,
            )
            snapshots.append(snap)
            computed += len(snap.values)

        now = datetime.now(timezone.utc)
        for fid in plan.feature_ids:
            self._last_run[fid] = now

        return ScheduleRunResult(
            plans_executed=len(snapshots),
            features_computed=computed,
            snapshots=snapshots,
            invalidated=invalidated,
        )

    def last_run(self, feature_id: str) -> datetime | None:
        return self._last_run.get(feature_id)

    def frequencies(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {}
        for m in self._service.list_features():
            if m.feature_id not in self._service._calculators:
                continue
            out.setdefault(m.refresh_frequency, []).append(m.feature_id)
        for freq, ids in out.items():
            out[freq] = self._service.dependency_order(ids)
        return out


def _as_of_str(as_of: date | datetime | str) -> str:
    if isinstance(as_of, datetime):
        return as_of.date().isoformat()
    if isinstance(as_of, date):
        return as_of.isoformat()
    return str(as_of)[:10]
