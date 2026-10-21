"""Validation platform service facade (BT-001–005)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.validation.flags import ValidationFlags
from app.validation.golden.loader import GoldenDataset, load_golden_dataset
from app.validation.models import ReplayResult, ReplayRun
from app.validation.replay.engine import ReplayEngine
from app.validation.store import ValidationStore


class ValidationService:
    """P0 Validation & Backtesting platform — no MarketDataClient, no live mode."""

    def __init__(
        self,
        store: ValidationStore | None = None,
        flags: ValidationFlags | None = None,
    ) -> None:
        self.flags = flags or ValidationFlags.from_settings()
        self.store = store or ValidationStore()
        self.engine = ReplayEngine(store=self.store, flags=self.flags)

    def run_replay(
        self,
        dataset_id: str = "golden_p0_v1",
        *,
        dataset: GoldenDataset | None = None,
        generated_at: datetime | None = None,
    ) -> ReplayResult:
        return self.engine.run(dataset_id, dataset=dataset, generated_at=generated_at)

    def get_run(self, run_id: str) -> ReplayRun | None:
        return self.store.get_run(run_id)

    def get_result(self, run_id: str) -> ReplayResult | None:
        return self.store.get_result(run_id)

    def list_runs(self, limit: int = 50) -> list[ReplayRun]:
        return self.store.list_runs(limit=limit)

    def get_dashboard(self, run_id: str) -> dict[str, Any] | None:
        result = self.store.get_result(run_id)
        if result is None:
            return None
        return result.dashboard

    def list_datasets(self) -> list[dict[str, str]]:
        ds = load_golden_dataset("golden_p0_v1")
        return [
            {
                "dataset_id": ds.dataset_id,
                "version": ds.version,
                "universe_id": ds.universe_id,
                "n_days": str(len(ds.days)),
                "n_symbols": str(len(ds.symbols)),
            }
        ]

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.backtest and not self.flags.live,
            "service": "validation-backtesting",
            "platform": "BT",
            "mode": "backtest",
            "production_influence": False,
            "live": self.flags.live,
            "flags": {"BACKTEST": self.flags.backtest, "LIVE": self.flags.live},
            "store": self.store.stats(),
            "consumes": [
                "Historical FeatureSnapshots",
                "Historical EngineStates",
                "Historical L4Opinion",
                "Historical E10Portfolio",
            ],
            "market_data_access": False,
            "pipeline": [
                "Snapshot",
                "ORCH Replay",
                "E01",
                "E14",
                "E02",
                "E13",
                "E08",
                "E09",
                "E05",
                "E11",
                "E03",
                "E04",
                "L4",
                "E10",
                "Metrics",
            ],
        }
