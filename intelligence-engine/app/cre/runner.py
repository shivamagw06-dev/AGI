"""CRE-001 Daily Evaluation Runner — nightly/on-demand evaluation over Historical Replay."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Any

from app.cre.dashboard import build_cre_dashboard
from app.cre.drift import detect_drift
from app.cre.flags import CREFlags
from app.cre.models import CREEvaluationResult
from app.cre.promotion import build_promotion_report
from app.cre.scorecards import build_composite_scorecard, build_engine_scorecards
from app.cre.store import CREStore
from app.validation.flags import ValidationFlags
from app.validation.golden.loader import GoldenDataset, load_golden_dataset
from app.validation.service import ValidationService
from app.validation.store import ValidationStore


def _iso(ts: datetime) -> str:
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _evaluation_id(dataset_id: str, as_of: str, started_at: str) -> str:
    raw = f"cre|{dataset_id}|{as_of}|{started_at}"
    return "cre_" + sha256(raw.encode("utf-8")).hexdigest()[:16]


class DailyEvaluationRunner:
    """Nightly CRE evaluation. Isolated validation instances only — no production influence."""

    def __init__(
        self,
        store: CREStore | None = None,
        flags: CREFlags | None = None,
    ) -> None:
        self.store = store or CREStore()
        self.flags = flags or CREFlags.from_settings()

    def run(
        self,
        dataset_id: str = "golden_p0_v1",
        *,
        dataset: GoldenDataset | None = None,
        generated_at: datetime | None = None,
    ) -> CREEvaluationResult:
        if not self.flags.cre:
            raise RuntimeError("CRE flag disabled (CRE=false)")

        started = generated_at or datetime.now(timezone.utc)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        started_at = _iso(started)

        ds = dataset or load_golden_dataset(dataset_id)
        # Isolated validation — never share production singletons / MarketData
        validation = ValidationService(
            store=ValidationStore(),
            flags=ValidationFlags(backtest=True, live=False),
        )
        replay = validation.run_replay(dataset_id, dataset=ds, generated_at=started)
        as_of = replay.days[-1].as_of if replay.days else started.date().isoformat()

        # First pass scorecards to get rolling metrics for drift
        prelim = build_engine_scorecards(result=replay, dataset=ds, as_of=as_of)
        rolling = prelim[0].rolling if prelim else {}
        drift_alerts, regression_alerts = detect_drift(
            days=replay.days,
            rolling=rolling,
            as_of=as_of,
            generated_at=started,
        )
        drift_counts: dict[str, int] = {}
        for a in drift_alerts:
            drift_counts[a.engine] = drift_counts.get(a.engine, 0) + 1
        for a in regression_alerts:
            drift_counts[a.engine] = drift_counts.get(a.engine, 0) + 1

        scorecards = build_engine_scorecards(
            result=replay,
            dataset=ds,
            as_of=as_of,
            drift_by_engine=drift_counts,
        )
        summary = replay.summary
        composite = build_composite_scorecard(
            as_of=as_of,
            scorecards=scorecards,
            parity_stability=summary.parity_stability if summary else None,
            schema_stability=1.0 if summary and summary.passed else 0.0,
        )
        promotion = build_promotion_report(
            as_of=as_of,
            scorecards=scorecards,
            composite=composite,
            flags=self.flags,
            engine_versions=replay.run.engine_versions,
            formula_versions=replay.run.formula_versions,
            drift_alert_count=len(drift_alerts),
            regression_alert_count=len(regression_alerts),
        )
        # Store intermediate so series charts can include this evaluation
        finished = started  # deterministic finish when generated_at fixed
        finished_at = _iso(finished)
        evaluation_id = _evaluation_id(dataset_id, as_of, started_at)

        # Temporary put for series, then rebuild dashboard with series
        stub = CREEvaluationResult(
            evaluation_id=evaluation_id,
            as_of=as_of,
            dataset_id=dataset_id,
            started_at=started_at,
            finished_at=finished_at,
            replay_run_id=replay.run.run_id,
            engine_scorecards=scorecards,
            composite=composite,
            drift_alerts=drift_alerts,
            regression_alerts=regression_alerts,
            promotion=promotion,
            dashboard={},
            production_influence=False,
            flags={"CRE": self.flags.cre, "PROMOTION": self.flags.promotion},
        )
        self.store.put(stub)
        dashboard = build_cre_dashboard(
            days=replay.days,
            scorecards=scorecards,
            composite=composite,
            promotion=promotion,
            series=self.store.series(),
        )
        result = stub.model_copy(update={"dashboard": dashboard})
        self.store.put(result)
        return result

    def health(self) -> dict[str, Any]:
        return {
            "ok": self.flags.cre and not self.flags.promotion,
            "service": "continuous-research-evaluation",
            "platform": "CRE",
            "production_influence": False,
            "flags": {"CRE": self.flags.cre, "PROMOTION": self.flags.promotion},
            "store": self.store.stats(),
            "inputs": [
                "Historical Replay",
                "Daily Shadow Runs",
                "EngineStates",
                "L4Opinion",
                "E10Portfolio",
            ],
            "outputs": [
                "EngineScorecard",
                "CompositeScorecard",
                "PromotionReport",
                "RegressionAlert",
                "DriftAlert",
            ],
            "windows": [30, 90, 252],
            "market_data_access": False,
            "wbs": ["CRE-001", "CRE-002", "CRE-003", "CRE-004", "CRE-005"],
        }
