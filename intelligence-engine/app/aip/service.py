"""AIP service facade — Alpha Improvement Programme research layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from app.aip.contribution import analyze_contributions, contribution_summary
from app.aip.experiment import ExperimentRunner, default_hypothesis
from app.aip.flags import AipFlags
from app.aip.house_view import track_house_view_evolution
from app.aip.models import (
    ExperimentHypothesis,
    ExperimentRequest,
    ExperimentResult,
    QualityScore,
    WeightSet,
)
from app.aip.promotion import build_promotion_evidence
from app.aip.quality import quality_from_payload
from app.aip.registry import DynamicWeightRegistry
from app.aip.reports import build_dashboard
from app.aip.roadmap import roadmap
from app.aip.store import AipStore
from app.validation.flags import ValidationFlags
from app.validation.golden.loader import load_golden_dataset
from app.validation.service import ValidationService
from app.validation.store import ValidationStore


class AipService:
    """Research programme facade. No production influence. L4 remains shadow."""

    def __init__(
        self,
        store: AipStore | None = None,
        registry: DynamicWeightRegistry | None = None,
        flags: AipFlags | None = None,
    ) -> None:
        self.flags = flags or AipFlags.from_settings()
        self.store = store or AipStore()
        self.registry = registry or DynamicWeightRegistry()
        self.runner = ExperimentRunner(
            store=self.store, registry=self.registry, flags=self.flags
        )

    def health(self) -> dict[str, Any]:
        return self.runner.health()

    def roadmap(self) -> dict[str, Any]:
        return roadmap()

    def list_weights(self) -> list[WeightSet]:
        self._require()
        return self.registry.list()

    def get_weight(self, weight_set_id: str) -> WeightSet | None:
        self._require()
        return self.registry.get(weight_set_id)

    def register_weight(
        self,
        *,
        weight_set_id: str,
        name: str,
        weights: dict[str, float],
        description: str = "",
        regime: str | None = None,
        sector: str | None = None,
        notes: list[str] | None = None,
    ) -> WeightSet:
        self._require()
        return self.registry.register(
            weight_set_id=weight_set_id,
            name=name,
            weights=weights,
            description=description,
            regime=regime,
            sector=sector,
            notes=notes,
        )

    def run_experiment(
        self,
        request: ExperimentRequest | None = None,
        *,
        generated_at: datetime | None = None,
        risk_approved: bool = False,
        architecture_approved: bool = False,
    ) -> ExperimentResult:
        self._require()
        req = request or ExperimentRequest(
            hypothesis=default_hypothesis("AIP-02"),
            candidate_weight_set_id="aip_e03_heavier_v1",
            dataset_id="golden_p0_v1",
            name="Default AIP-02 weight experiment",
        )
        if req.hypothesis is None:
            req = req.model_copy(update={"hypothesis": default_hypothesis()})
        return self.runner.run(
            req,
            generated_at=generated_at,
            risk_approved=risk_approved,
            architecture_approved=architecture_approved,
        )

    def list_experiments(self, limit: int = 50) -> list[ExperimentResult]:
        self._require()
        return self.store.list_experiments(limit=limit)

    def get_experiment(self, experiment_id: str) -> ExperimentResult | None:
        self._require()
        return self.store.get_experiment(experiment_id)

    def contribution(
        self,
        dataset_id: str = "golden_p0_v1",
        *,
        weight_set_id: str | None = None,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        self._require()
        latest = self.store.get_contribution()
        if latest and latest.dataset_id == dataset_id and (
            weight_set_id is None or latest.weight_set_id == weight_set_id
        ):
            return {
                "report": latest.model_dump(mode="json"),
                "summary": contribution_summary(latest),
            }
        # Run lightweight analysis via experiment defaults
        ws = self.registry.get(weight_set_id or "l4_p0_shadow_voters_v1")
        if ws is None:
            ws = self.registry.baseline()
        ds = load_golden_dataset(dataset_id)
        validation = ValidationService(
            store=ValidationStore(),
            flags=ValidationFlags(backtest=True, live=False),
        )
        replay = validation.run_replay(dataset_id, dataset=ds, generated_at=generated_at)
        as_of = replay.days[-1].as_of if replay.days else "n/a"
        report = analyze_contributions(
            days=replay.days,
            dataset=ds,
            weights=ws.weights,
            weight_set_id=ws.weight_set_id,
            as_of=as_of,
        )
        # stash via a stub experiment put is not needed; keep on store by piggybacking
        # through temporary field — store only updates contribution via experiments.
        # Return computed report directly.
        return {
            "report": report.model_dump(mode="json"),
            "summary": contribution_summary(report),
        }

    def calibration(self) -> dict[str, Any] | None:
        self._require()
        plan = self.store.get_calibration()
        return plan.model_dump(mode="json") if plan else None

    def attribution(self) -> dict[str, Any] | None:
        self._require()
        report = self.store.get_attribution()
        return report.model_dump(mode="json") if report else None

    def house_view_evolution(
        self,
        ticker: str,
        dataset_id: str = "golden_p0_v1",
        *,
        generated_at: datetime | None = None,
    ) -> dict[str, Any]:
        self._require()
        ds = load_golden_dataset(dataset_id)
        validation = ValidationService(
            store=ValidationStore(),
            flags=ValidationFlags(backtest=True, live=False),
        )
        replay = validation.run_replay(dataset_id, dataset=ds, generated_at=generated_at)
        evo = track_house_view_evolution(ticker, replay.days)
        return evo.model_dump(mode="json")

    def score_quality(self, payload: dict[str, Any]) -> QualityScore:
        self._require()
        return quality_from_payload(payload)

    def promotion(self) -> dict[str, Any]:
        self._require()
        evidence = self.store.get_promotion()
        if evidence is None:
            evidence = build_promotion_evidence(self.store.latest(), self.flags)
            self.store.put_promotion(evidence)
        return evidence.model_dump(mode="json")

    def dashboard(self) -> dict[str, Any]:
        self._require()
        dash = build_dashboard(
            store=self.store,
            registry=self.registry,
            flags=self.flags,
            latest=self.store.latest(),
        )
        return dash.model_dump(mode="json")

    def _require(self) -> None:
        if not self.flags.aip:
            raise RuntimeError("AIP flag disabled (AIP=false)")
