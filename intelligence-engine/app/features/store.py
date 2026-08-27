"""In-memory historical / PIT feature store (FEAT-001 store layer)."""

from __future__ import annotations

import threading
from datetime import date, datetime

from app.features.models import FeatureMetadata, FeatureValue, HistoricalFeatureSeries


def _as_of_key(as_of: date | datetime | str) -> str:
    if isinstance(as_of, datetime):
        return as_of.date().isoformat()
    if isinstance(as_of, date):
        return as_of.isoformat()
    return str(as_of)[:10]


class FeatureStore:
    """PIT store: (feature_id, symbol, as_of, formula_version) -> FeatureValue."""

    def __init__(self) -> None:
        self._meta: dict[str, FeatureMetadata] = {}
        self._values: dict[tuple[str, str, str, str], FeatureValue] = {}
        self._lock = threading.Lock()

    def upsert_metadata(self, meta: FeatureMetadata) -> None:
        with self._lock:
            self._meta[meta.feature_id] = meta

    def get_metadata(self, feature_id: str) -> FeatureMetadata | None:
        with self._lock:
            return self._meta.get(feature_id)

    def list_metadata(self) -> list[FeatureMetadata]:
        with self._lock:
            return sorted(self._meta.values(), key=lambda m: m.feature_id)

    def put_value(self, value: FeatureValue) -> None:
        symbol = value.symbol or ""
        key = (value.feature_id, symbol, _as_of_key(value.as_of), value.formula_version)
        with self._lock:
            self._values[key] = value

    def get_value(
        self,
        feature_id: str,
        *,
        symbol: str | None,
        as_of: date | datetime | str,
        pit_mode: bool = True,
        formula_version: str | None = None,
    ) -> FeatureValue | None:
        """Return value as-of. Prefers metadata/current formula_version when set."""
        symbol_key = symbol or ""
        as_of_s = _as_of_key(as_of)
        with self._lock:
            version = formula_version
            if version is None:
                meta = self._meta.get(feature_id)
                if meta is not None:
                    version = meta.formula_version
            value: FeatureValue | None = None
            if version is not None:
                value = self._values.get((feature_id, symbol_key, as_of_s, version))
            if value is None:
                # Fallback: latest matching as_of across versions
                candidates = [
                    v
                    for (fid, sym, day, _), v in self._values.items()
                    if fid == feature_id and sym == symbol_key and day == as_of_s
                ]
                if candidates:
                    value = sorted(candidates, key=lambda v: v.formula_version)[-1]
            if value is None:
                return None
            if pit_mode:
                available = value.available_at
                if isinstance(available, datetime):
                    available_day = available.date().isoformat()
                else:
                    available_day = str(available)[:10]
                if available_day > as_of_s:
                    return None
            return value

    def history(
        self,
        feature_id: str,
        *,
        symbol: str | None = None,
        formula_version: str | None = None,
    ) -> HistoricalFeatureSeries:
        symbol_key = symbol or ""
        with self._lock:
            points = [
                v
                for (fid, sym, _, ver), v in self._values.items()
                if fid == feature_id
                and sym == symbol_key
                and (formula_version is None or ver == formula_version)
            ]
        points.sort(key=lambda p: (_as_of_key(p.as_of), p.formula_version))
        version = formula_version or (points[-1].formula_version if points else "")
        return HistoricalFeatureSeries(
            feature_id=feature_id,
            formula_version=version,
            symbol=symbol,
            points=points,
        )
