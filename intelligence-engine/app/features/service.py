"""Feature Registry Service — registration, compute, PIT lookup, scheduler."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from app.core.logging import get_logger
from app.features.cache import FeatureCache
from app.features.calculators import register_builtin_calculators
from app.features.calculators.base import FeatureCalculator, FeatureContext
from app.features.graph import FeatureDependencyGraph
from app.features.metrics import FeatureMetrics, Timer
from app.features.models import (
    FeatureMetadata,
    FeatureSnapshot,
    FeatureValue,
    HistoricalFeatureSeries,
    utcnow,
)
from app.features.scheduler import CalculationScheduler
from app.features.store import FeatureStore

log = get_logger(__name__)


class FeatureRegistryService:
    def __init__(
        self,
        *,
        store: FeatureStore | None = None,
        cache: FeatureCache | None = None,
        cache_ttl_s: float = 60.0,
        register_builtins: bool = True,
    ) -> None:
        self.store = store or FeatureStore()
        self.cache = cache or FeatureCache()
        self.graph = FeatureDependencyGraph()
        self.metrics = FeatureMetrics()
        self.cache_ttl_s = cache_ttl_s
        self._calculators: dict[str, FeatureCalculator] = {}
        self.scheduler = CalculationScheduler(self)
        if register_builtins:
            register_builtin_calculators(self)

    def register_calculator(self, calculator: FeatureCalculator) -> None:
        meta = calculator.metadata
        self._calculators[meta.feature_id] = calculator
        self.store.upsert_metadata(meta)
        self.graph.set_dependencies(meta.feature_id, meta.dependencies)
        # Dependency invalidation on formula change
        self.cache.invalidate_prefix(meta.feature_id)
        for dep in self.graph.transitive_dependents(meta.feature_id):
            self.cache.invalidate_prefix(dep)
        log.info(
            "feature_registered",
            extra={"extra": {"feature_id": meta.feature_id, "version": meta.formula_version}},
        )

    def register_metadata(self, meta: FeatureMetadata) -> None:
        """Register metadata without calculator (external/materialized features)."""
        self.store.upsert_metadata(meta)
        self.graph.set_dependencies(meta.feature_id, meta.dependencies)

    def list_features(self) -> list[FeatureMetadata]:
        return self.store.list_metadata()

    def get_metadata(self, feature_id: str) -> FeatureMetadata | None:
        return self.store.get_metadata(feature_id)

    def dependency_order(self, feature_ids: list[str] | None = None) -> list[str]:
        return self.graph.topological_order(feature_ids)

    def compute(
        self,
        feature_id: str,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        ctx: FeatureContext | dict[str, Any] | None = None,
        available_at: datetime | None = None,
        persist: bool = True,
        use_cache: bool = True,
    ) -> FeatureValue:
        """Compute feature and dependencies in topo order (no duplicate work in one call)."""
        context = FeatureContext(ctx or {})
        as_of_s = _as_of_str(as_of)
        # For historical as_of computes, default available_at to as_of (PIT), not wall clock.
        available = available_at or _as_of_datetime(as_of)
        order = self.graph.topological_order([feature_id])
        computed: dict[str, FeatureValue] = {}

        for fid in order:
            meta = self.store.get_metadata(fid)
            if meta is None:
                raise KeyError(f"unknown feature_id: {fid}")
            cache_key = FeatureCache.key(fid, symbol, as_of_s, meta.formula_version)
            if use_cache:
                timer = Timer()
                cached = self.cache.get(cache_key)
                self.metrics.record_lookup(timer.ms())
                if cached is not None:
                    computed[fid] = cached
                    continue
            # Reuse already computed deps in this batch
            if fid in computed:
                continue
            calc = self._calculators.get(fid)
            if calc is None:
                stored = self.store.get_value(fid, symbol=symbol, as_of=as_of, pit_mode=True)
                if stored is None:
                    raise KeyError(f"no calculator or stored value for {fid}")
                computed[fid] = stored
                continue

            timer = Timer()
            try:
                dep_vals = {d: computed[d] for d in meta.dependencies if d in computed}
                value = calc.compute(
                    symbol=symbol,
                    as_of=as_of,
                    available_at=available,
                    ctx=context,
                    dep_values=dep_vals,
                )
                # PIT guard: reject future-available values
                if _date_str(value.available_at) > as_of_s:
                    value = value.model_copy(
                        update={"value": None, "quality_flag": "error", "confidence": 0.0}
                    )
                computed[fid] = value
                if use_cache:
                    self.cache.set(cache_key, value, self.cache_ttl_s)
                if persist:
                    self.store.put_value(value)
                self.metrics.record_compute(fid, timer.ms(), ok=True)
            except Exception:
                self.metrics.record_compute(fid, timer.ms(), ok=False)
                raise

        return computed[feature_id]

    def compute_many(
        self,
        feature_ids: list[str],
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        ctx: FeatureContext | dict[str, Any] | None = None,
    ) -> FeatureSnapshot:
        values: dict[str, FeatureValue] = {}
        # Single topo pass covering all requested ids
        order = self.graph.topological_order(feature_ids)
        context = FeatureContext(ctx or {})
        as_of_s = _as_of_str(as_of)
        available = _as_of_datetime(as_of)
        computed: dict[str, FeatureValue] = {}
        for fid in order:
            meta = self.store.get_metadata(fid)
            if meta is None:
                continue
            cache_key = FeatureCache.key(fid, symbol, as_of_s, meta.formula_version)
            cached = self.cache.get(cache_key)
            if cached is not None:
                computed[fid] = cached
                continue
            calc = self._calculators.get(fid)
            if calc is None:
                continue
            dep_vals = {d: computed[d] for d in meta.dependencies if d in computed}
            value = calc.compute(
                symbol=symbol,
                as_of=as_of,
                available_at=available,
                ctx=context,
                dep_values=dep_vals,
            )
            computed[fid] = value
            self.cache.set(cache_key, value, self.cache_ttl_s)
            self.store.put_value(value)
        for fid in feature_ids:
            if fid in computed:
                values[fid] = computed[fid]
        return FeatureSnapshot(
            snapshot_id=str(uuid4()),
            as_of=as_of,
            symbol=symbol,
            values=values,
        )

    def get(
        self,
        feature_id: str,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        pit_mode: bool = True,
    ) -> FeatureValue | None:
        timer = Timer()
        meta = self.store.get_metadata(feature_id)
        if meta:
            cached = self.cache.get(FeatureCache.key(feature_id, symbol, _as_of_str(as_of), meta.formula_version))
            if cached is not None:
                self.metrics.record_lookup(timer.ms())
                return cached
        value = self.store.get_value(feature_id, symbol=symbol, as_of=as_of, pit_mode=pit_mode)
        self.metrics.record_lookup(timer.ms())
        return value

    def history(self, feature_id: str, *, symbol: str | None = None) -> HistoricalFeatureSeries:
        return self.store.history(feature_id, symbol=symbol)

    def invalidate(self, feature_id: str) -> dict[str, int]:
        removed = self.cache.invalidate_prefix(feature_id)
        dep_removed = 0
        for dep in self.graph.transitive_dependents(feature_id):
            dep_removed += self.cache.invalidate_prefix(dep)
        return {"feature": removed, "dependents": dep_removed}

    def recompute_impacted(
        self,
        feature_ids: list[str] | set[str],
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        ctx: FeatureContext | dict[str, Any] | None = None,
        persist: bool = True,
    ) -> FeatureSnapshot:
        """Recompute only the given closed impacted set (no unrelated features).

        Ancestors outside the set are loaded from cache/store — not rebuilt.
        """
        context = FeatureContext(ctx or {})
        as_of_s = _as_of_str(as_of)
        available = _as_of_datetime(as_of)
        impacted = set(feature_ids)
        order = self.graph.order_closed_set(impacted)
        computed: dict[str, FeatureValue] = {}
        values: dict[str, FeatureValue] = {}

        for fid in order:
            meta = self.store.get_metadata(fid)
            if meta is None:
                continue
            calc = self._calculators.get(fid)
            if calc is None:
                stored = self.store.get_value(fid, symbol=symbol, as_of=as_of, pit_mode=True)
                if stored is not None:
                    computed[fid] = stored
                    values[fid] = stored
                continue

            dep_vals: dict[str, FeatureValue] = {}
            for dep in meta.dependencies:
                if dep in computed:
                    dep_vals[dep] = computed[dep]
                    continue
                # Ancestor outside impacted set — reuse cache/store (incremental)
                cached = self.get(dep, symbol=symbol, as_of=as_of, pit_mode=True)
                if cached is not None:
                    dep_vals[dep] = cached
                    computed[dep] = cached

            timer = Timer()
            try:
                value = calc.compute(
                    symbol=symbol,
                    as_of=as_of,
                    available_at=available,
                    ctx=context,
                    dep_values=dep_vals,
                )
                if _date_str(value.available_at) > as_of_s:
                    value = value.model_copy(
                        update={"value": None, "quality_flag": "error", "confidence": 0.0}
                    )
                computed[fid] = value
                values[fid] = value
                self.cache.set(
                    FeatureCache.key(fid, symbol, as_of_s, meta.formula_version),
                    value,
                    self.cache_ttl_s,
                )
                if persist:
                    self.store.put_value(value)
                self.metrics.record_compute(fid, timer.ms(), ok=True)
            except Exception:
                self.metrics.record_compute(fid, timer.ms(), ok=False)
                raise

        return FeatureSnapshot(
            snapshot_id=str(uuid4()),
            as_of=as_of,
            symbol=symbol,
            values=values,
        )

    def health(self) -> dict[str, Any]:
        return {
            "ok": True,
            "service": "feature-registry",
            "feature_count": len(self.list_features()),
            "calculator_count": len(self._calculators),
            "schedule_frequencies": {
                freq: len(ids) for freq, ids in self.scheduler.frequencies().items()
            },
            "cache": self.cache.stats(),
            "metrics": self.metrics.snapshot(),
        }


def _as_of_str(as_of: date | datetime | str) -> str:
    if isinstance(as_of, datetime):
        return as_of.date().isoformat()
    if isinstance(as_of, date):
        return as_of.isoformat()
    return str(as_of)[:10]


def _as_of_datetime(as_of: date | datetime | str) -> datetime:
    if isinstance(as_of, datetime):
        return as_of if as_of.tzinfo else as_of.replace(tzinfo=timezone.utc)
    if isinstance(as_of, date):
        return datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc)
    day = date.fromisoformat(str(as_of)[:10])
    return datetime(day.year, day.month, day.day, tzinfo=timezone.utc)


def _date_str(value: datetime | date | str) -> str:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date().isoformat() if value.tzinfo else value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)[:10]
