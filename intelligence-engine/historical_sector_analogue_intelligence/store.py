"""Published Historical Sector Analogues + regime history store."""

from __future__ import annotations

import copy
import time
from typing import Any

from historical_sector_analogue_intelligence.schema import (
    HistoricalSectorAnalogue,
    SectorRegime,
)


class SectorAnalogueStore:
    def __init__(self) -> None:
        self._analogues: dict[str, HistoricalSectorAnalogue] = {}
        self._by_sector: dict[str, list[str]] = {}
        self._current_regimes: dict[str, SectorRegime] = {}
        self._regime_history: dict[str, list[SectorRegime]] = {}
        self._runs: list[dict[str, Any]] = []
        self._built_at: float | None = None

    def clear(self) -> None:
        self._analogues.clear()
        self._by_sector.clear()
        self._current_regimes.clear()
        self._regime_history.clear()
        self._runs.clear()
        self._built_at = None

    def set_current_regime(self, regime: SectorRegime) -> None:
        frozen = SectorRegime.model_validate(copy.deepcopy(regime.model_dump(mode="json")))
        self._current_regimes[frozen.sector] = frozen

    def current_regime(self, sector: str | None = None) -> SectorRegime | None:
        if sector:
            return self._current_regimes.get(sector)
        if len(self._current_regimes) == 1:
            return next(iter(self._current_regimes.values()))
        return None

    def set_regime_history(self, sector: str, regimes: list[SectorRegime]) -> None:
        self._regime_history[sector] = [
            SectorRegime.model_validate(copy.deepcopy(r.model_dump(mode="json"))) for r in regimes
        ]

    def regime_history(self, sector: str | None = None, *, limit: int = 50) -> list[SectorRegime]:
        if sector:
            return list((self._regime_history.get(sector) or [])[:limit])
        rows: list[SectorRegime] = []
        for hist in self._regime_history.values():
            rows.extend(hist)
        return rows[:limit]

    def publish(self, analogue: HistoricalSectorAnalogue) -> HistoricalSectorAnalogue:
        from historical_sector_analogue_intelligence.schema import utc_now

        frozen = HistoricalSectorAnalogue.model_validate(
            copy.deepcopy(analogue.model_dump(mode="json"))
        )
        existing = self._analogues.get(frozen.analogue_id)
        if existing:
            frozen.version = existing.version + 1
        frozen.published = True
        frozen.published_at = utc_now()
        self._analogues[frozen.analogue_id] = frozen
        key = frozen.sector
        ids = self._by_sector.setdefault(key, [])
        if frozen.analogue_id not in ids:
            ids.append(frozen.analogue_id)
        self._built_at = time.time()
        return frozen

    def list_all(
        self, *, limit: int = 50, sector: str | None = None
    ) -> list[HistoricalSectorAnalogue]:
        if sector:
            ids = self._by_sector.get(sector) or []
            rows = [self._analogues[i] for i in ids if i in self._analogues]
        else:
            rows = list(self._analogues.values())
        rows = [r for r in rows if r.published]
        rows.sort(key=lambda r: (r.rank or 999, -r.similarity_score))
        return rows[:limit]

    def record_run(self, row: dict[str, Any]) -> None:
        self._runs.append({**row, "ts": time.time()})
        if len(self._runs) > 200:
            del self._runs[:-200]

    def recent_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        return list(self._runs[-limit:])

    def coverage(self) -> dict[str, Any]:
        rows = [r for r in self._analogues.values() if r.published]
        by_conf: dict[str, int] = {"High": 0, "Medium": 0, "Low": 0}
        scores: list[float] = []
        periods: set[str] = set()
        sectors: set[str] = set()
        for r in rows:
            by_conf[r.confidence] = by_conf.get(r.confidence, 0) + 1
            scores.append(r.similarity_score)
            periods.add(r.matched_period)
            sectors.add(r.sector)
        freshness_s = (time.time() - self._built_at) if self._built_at else None
        return {
            "total_analogues": len(rows),
            "sectors_covered": sorted(sectors),
            "confidence_distribution": by_conf,
            "matched_periods": sorted(periods),
            "historical_regimes": sum(len(v) for v in self._regime_history.values()),
            "has_current_regime": bool(self._current_regimes),
            "current_regimes": sorted(self._current_regimes.keys()),
            "similarity_distribution": {
                "min": round(min(scores), 2) if scores else None,
                "max": round(max(scores), 2) if scores else None,
                "mean": round(sum(scores) / len(scores), 2) if scores else None,
                "buckets": {
                    "90_plus": sum(1 for s in scores if s >= 90),
                    "80_89": sum(1 for s in scores if 80 <= s < 90),
                    "70_79": sum(1 for s in scores if 70 <= s < 80),
                    "below_70": sum(1 for s in scores if s < 70),
                },
            },
            "analogue_freshness_seconds": round(freshness_s, 2) if freshness_s is not None else None,
        }


STORE = SectorAnalogueStore()


def reset() -> None:
    STORE.clear()
