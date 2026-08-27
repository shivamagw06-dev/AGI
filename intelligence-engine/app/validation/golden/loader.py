"""BT-002 Golden Dataset Loader — historical PIT panels for replay."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_FIXTURES = Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "validation"


@dataclass(frozen=True)
class GoldenDay:
    as_of: str
    macro_features: dict[str, float]
    risk_features: dict[str, float]
    e02_panels: dict[str, dict[str, Any]]
    e03_panels: dict[str, dict[str, Any]]
    forward_returns: dict[str, float]
    benchmark_return: float


@dataclass
class GoldenDataset:
    dataset_id: str
    version: str
    universe_id: str
    description: str
    symbols: list[str]
    days: list[GoldenDay] = field(default_factory=list)

    @property
    def as_of_dates(self) -> list[str]:
        return [d.as_of for d in self.days]


def load_golden_dataset(
    dataset_id: str = "golden_p0_v1",
    *,
    path: Path | None = None,
) -> GoldenDataset:
    """Load a frozen golden JSON dataset. Deterministic file contents only."""
    file_path = path or (DEFAULT_FIXTURES / f"{dataset_id}.json")
    if not file_path.exists():
        raise FileNotFoundError(f"Golden dataset not found: {file_path}")
    raw = json.loads(file_path.read_text(encoding="utf-8"))
    days = [
        GoldenDay(
            as_of=str(day["as_of"]),
            macro_features={k: float(v) for k, v in (day.get("macro_features") or {}).items()},
            risk_features={k: float(v) for k, v in (day.get("risk_features") or {}).items()},
            e02_panels=dict(day.get("e02_panels") or {}),
            e03_panels=dict(day.get("e03_panels") or {}),
            forward_returns={k: float(v) for k, v in (day.get("forward_returns") or {}).items()},
            benchmark_return=float(day.get("benchmark_return") or 0.0),
        )
        for day in raw.get("days") or []
    ]
    days.sort(key=lambda d: d.as_of)
    return GoldenDataset(
        dataset_id=str(raw.get("dataset_id") or dataset_id),
        version=str(raw.get("version") or "1.0.0"),
        universe_id=str(raw.get("universe_id") or "NIFTY500"),
        description=str(raw.get("description") or ""),
        symbols=list(raw.get("symbols") or []),
        days=days,
    )
