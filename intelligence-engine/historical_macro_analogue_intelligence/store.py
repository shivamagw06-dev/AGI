"""Published Historical Macro Analogues + regime history store."""

from __future__ import annotations

import copy
import time
from typing import Any

from historical_macro_analogue_intelligence.schema import HistoricalMacroAnalogue, MacroRegime


class MacroAnalogueStore:
    def __init__(self) -> None:
        self._analogues: dict[str, HistoricalMacroAnalogue] = {}
        self._by_country: dict[str, list[str]] = {}
        self._current_regime: MacroRegime | None = None
        self._regime_history: list[MacroRegime] = []
        self._runs: list[dict[str, Any]] = []
        self._built_at: float | None = None

    def clear(self) -> None:
        self._analogues.clear()
        self._by_country.clear()
        self._current_regime = None
        self._regime_history.clear()
        self._runs.clear()
        self._built_at = None

    def set_current_regime(self, regime: MacroRegime) -> None:
        self._current_regime = MacroRegime.model_validate(
            copy.deepcopy(regime.model_dump(mode="json"))
        )

    def current_regime(self) -> MacroRegime | None:
        return self._current_regime

    def set_regime_history(self, regimes: list[MacroRegime]) -> None:
        self._regime_history = [
            MacroRegime.model_validate(copy.deepcopy(r.model_dump(mode="json"))) for r in regimes
        ]

    def regime_history(self, *, limit: int = 50) -> list[MacroRegime]:
        return list(self._regime_history[:limit])

    def publish(self, analogue: HistoricalMacroAnalogue) -> HistoricalMacroAnalogue:
        from historical_macro_analogue_intelligence.schema import utc_now

        frozen = HistoricalMacroAnalogue.model_validate(
            copy.deepcopy(analogue.model_dump(mode="json"))
        )
        frozen.published = True
        frozen.published_at = utc_now()
        self._analogues[frozen.analogue_id] = frozen
        key = frozen.country.upper()
        ids = self._by_country.setdefault(key, [])
        if frozen.analogue_id not in ids:
            ids.append(frozen.analogue_id)
        self._built_at = time.time()
        return frozen

    def list_all(self, *, limit: int = 50, country: str | None = None) -> list[HistoricalMacroAnalogue]:
        if country:
            ids = self._by_country.get(country.upper()) or []
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
        for r in rows:
            by_conf[r.confidence] = by_conf.get(r.confidence, 0) + 1
            scores.append(r.similarity_score)
            periods.add(r.matched_period)
        freshness_s = (time.time() - self._built_at) if self._built_at else None
        return {
            "total_analogues": len(rows),
            "countries": sorted(self._by_country.keys()),
            "confidence_distribution": by_conf,
            "matched_periods": sorted(periods),
            "historical_regimes": len(self._regime_history),
            "has_current_regime": self._current_regime is not None,
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


STORE = MacroAnalogueStore()


def reset() -> None:
    STORE.clear()
