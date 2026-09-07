"""BT-001 Replay Engine — orchestrate golden → historical runner → metrics."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.validation.dashboard import build_dashboard
from app.validation.flags import ValidationFlags
from app.validation.golden.loader import GoldenDataset, load_golden_dataset
from app.validation.metrics.calculator import compute_metrics
from app.validation.models import ReplayResult, ReplayRun
from app.validation.runner.historical import FIXED_TS, HistoricalEngineRunner
from app.validation.store import ValidationStore


class ReplayEngine:
    """Institutional validation replay. LIVE=false. No production influence."""

    def __init__(
        self,
        store: ValidationStore | None = None,
        flags: ValidationFlags | None = None,
    ) -> None:
        self.store = store or ValidationStore()
        self.flags = flags or ValidationFlags.from_settings()

    def run(
        self,
        dataset_id: str = "golden_p0_v1",
        *,
        dataset: GoldenDataset | None = None,
        generated_at: datetime | None = None,
    ) -> ReplayResult:
        if not self.flags.backtest:
            raise RuntimeError("BACKTEST is disabled")
        if self.flags.live:
            raise RuntimeError("LIVE must remain false for validation replay")

        ds = dataset or load_golden_dataset(dataset_id)
        run_id = f"replay_{uuid.uuid4().hex[:12]}"
        started = datetime.now(timezone.utc).isoformat()
        runner = HistoricalEngineRunner(universe_id=ds.universe_id)
        engine_versions = runner.engine_versions()
        formula_versions = runner.formula_versions()

        run = ReplayRun(
            run_id=run_id,
            dataset_id=ds.dataset_id,
            dataset_version=ds.version,
            universe_id=ds.universe_id,
            status="running",
            started_at=started,
            n_days=len(ds.days),
            n_symbols=len(ds.symbols),
            engine_versions=engine_versions,
            formula_versions=formula_versions,
            flags={"BACKTEST": True, "LIVE": False},
            production_influence=False,
            live=False,
        )

        try:
            ts = generated_at or FIXED_TS
            day_slices = [runner.run_day(day, generated_at=ts) for day in ds.days]

            # Determinism / parity stability: re-run with fresh runner, compare hashes
            runner2 = HistoricalEngineRunner(universe_id=ds.universe_id)
            day_slices_b = [runner2.run_day(day, generated_at=ts) for day in ds.days]
            matches = 0
            total = 0
            for a, b in zip(day_slices, day_slices_b):
                total += 1
                if (
                    a.e01_hash == b.e01_hash
                    and a.e14_hash == b.e14_hash
                    and a.portfolio_hash == b.portfolio_hash
                    and a.e03_hashes == b.e03_hashes
                    and a.l4_hashes == b.l4_hashes
                ):
                    matches += 1
            parity = matches / total if total else 0.0
            deterministic = parity >= 0.999

            summary = compute_metrics(
                run_id=run_id,
                dataset=ds,
                days=day_slices,
                engine_versions=engine_versions,
                formula_versions=formula_versions,
                parity_stability=round(parity, 6),
                deterministic=deterministic,
            )
            dashboard = build_dashboard(day_slices, summary)
            finished = datetime.now(timezone.utc).isoformat()
            run = run.model_copy(
                update={"status": "succeeded", "finished_at": finished}
            )
            result = ReplayResult(run=run, days=day_slices, summary=summary, dashboard=dashboard)
            self.store.put(result)
            return result
        except Exception as exc:
            failed = run.model_copy(
                update={
                    "status": "failed",
                    "finished_at": datetime.now(timezone.utc).isoformat(),
                    "error": str(exc),
                }
            )
            result = ReplayResult(run=failed, days=[], summary=None, dashboard={})
            self.store.put(result)
            raise
