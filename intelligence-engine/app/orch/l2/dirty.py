"""Dirty feature tracking from market-data updates (ORCH-003)."""

from __future__ import annotations

import threading
from typing import Any

from app.orch.l2.models import MarketDataUpdateEvent, UpdateType


class DirtyFeatureTracker:
    """Maps MarketData updates → seed feature IDs that must recompute."""

    _TYPE_INPUT_PREFIXES: dict[UpdateType, tuple[str, ...]] = {
        "ohlcv": ("ohlcv.",),
        "quote": ("ohlcv.", "quote."),
        "macro": ("macro.",),
        "fundamentals": ("fundamentals.",),
        "universe": ("universe.",),
        "manual": (),
    }

    _TYPE_CATEGORIES: dict[UpdateType, tuple[str, ...]] = {
        "ohlcv": ("TECH_", "VOL_"),
        "quote": ("TECH_", "VOL_"),
        "macro": ("MACRO_",),
        "fundamentals": ("FUND_",),
        "universe": ("UNIV_",),
        "manual": (),
    }

    def __init__(self, feature_service: Any) -> None:
        self._features = feature_service
        self._lock = threading.Lock()
        # key: (symbol or "", as_of) -> set[feature_id]
        self._dirty: dict[tuple[str, str], set[str]] = {}

    def seeds_for_update(self, event: MarketDataUpdateEvent) -> set[str]:
        """Determine dirty seed feature IDs (calculators only)."""
        prefixes = self._TYPE_INPUT_PREFIXES.get(event.update_type, ())
        categories = self._TYPE_CATEGORIES.get(event.update_type, ())
        explicit = list(event.input_keys)
        seeds: set[str] = set()

        for meta in self._features.list_features():
            if meta.feature_id not in self._features._calculators:
                continue
            if explicit:
                if _inputs_match(meta.inputs, explicit):
                    seeds.add(meta.feature_id)
                continue
            if categories and meta.category in categories:
                seeds.add(meta.feature_id)
                continue
            if prefixes and any(any(inp.startswith(p) for p in prefixes) for inp in meta.inputs):
                seeds.add(meta.feature_id)
        return seeds

    def mark(self, event: MarketDataUpdateEvent, seeds: set[str] | None = None) -> set[str]:
        resolved = seeds if seeds is not None else self.seeds_for_update(event)
        key = (event.symbol or "", event.as_of)
        with self._lock:
            bucket = self._dirty.setdefault(key, set())
            bucket |= resolved
            return set(bucket)

    def mark_features(
        self,
        *,
        symbol: str | None,
        as_of: str,
        feature_ids: list[str] | set[str],
    ) -> set[str]:
        key = (symbol or "", as_of)
        with self._lock:
            bucket = self._dirty.setdefault(key, set())
            bucket |= set(feature_ids)
            return set(bucket)

    def snapshot(self, *, symbol: str | None, as_of: str) -> set[str]:
        key = (symbol or "", as_of)
        with self._lock:
            return set(self._dirty.get(key, ()))

    def clear(self, *, symbol: str | None, as_of: str, feature_ids: set[str] | None = None) -> None:
        key = (symbol or "", as_of)
        with self._lock:
            if key not in self._dirty:
                return
            if feature_ids is None:
                del self._dirty[key]
                return
            self._dirty[key] -= feature_ids
            if not self._dirty[key]:
                del self._dirty[key]

    def stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "dirty_buckets": len(self._dirty),
                "dirty_features": sum(len(v) for v in self._dirty.values()),
            }


def _inputs_match(meta_inputs: list[str], explicit_keys: list[str]) -> bool:
    for inp in meta_inputs:
        for key in explicit_keys:
            if inp == key or inp.startswith(key) or key.startswith(inp):
                return True
            # prefix family match: ohlcv <-> ohlcv.close
            if inp.split(".", 1)[0] == key.split(".", 1)[0]:
                return True
    return False
