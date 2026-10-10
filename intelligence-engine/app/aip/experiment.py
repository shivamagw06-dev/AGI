"""AIP experiment framework — hypothesis, metrics, replay, CRE, significance, rollback."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256

from app.aip.attribution import build_attribution
from app.aip.calibration import build_calibration_plan
from app.aip.contribution import analyze_contributions
from app.aip.flags import AipFlags
from app.aip.fusion_shadow import baseline_weights, score_universe
from app.aip.metrics import (
    bootstrap_ic_pvalue,
    delta,
    metrics_from_replay_e03,
    metrics_from_replay_l4,
    metrics_from_scored,
)
from app.aip.models import (
    BaselineComparison,
    ExperimentHypothesis,
    ExperimentRequest,
    ExperimentResult,
    RollbackPlan,
    SignificanceResult,
    WeightSet,
)
from app.aip.promotion import build_promotion_evidence
from app.aip.registry import DynamicWeightRegistry
from app.aip.store import AipStore
from app.cre.flags import CREFlags
from app.cre.service import CREService
from app.cre.store import CREStore
from app.engines.l4.mapping import WEIGHT_SET_ID
from app.validation.flags import ValidationFlags
from app.validation.golden.loader import GoldenDataset, load_golden_dataset
from app.validation.service import ValidationService
from app.validation.store import ValidationStore


def _iso(ts: datetime) -> str:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _experiment_id(
    dataset_id: str,
    candidate_id: str,
    started_at: str,
    hypothesis: str,
) -> str:
    raw = f"aip|{dataset_id}|{candidate_id}|{started_at}|{hypothesis}"
    return "aip_" + sha256(raw.encode("utf-8")).hexdigest()[:16]


class ExperimentRunner:
    """Run AIP shadow experiments. Never mutates production L4 weights."""

    def __init__(
        self,
        *,
        store: AipStore | None = None,
        registry: DynamicWeightRegistry | None = None,
        flags: AipFlags | None = None,
    ) -> None:
        self.store = store or AipStore()
        self.registry = registry or DynamicWeightRegistry()
        self.flags = flags or AipFlags.from_settings()

    def run(
        self,
        request: ExperimentRequest,
        *,
        dataset: GoldenDataset | None = None,
        generated_at: datetime | None = None,
        risk_approved: bool = False,
        architecture_approved: bool = False,
    ) -> ExperimentResult:
        if not self.flags.aip:
            raise RuntimeError("AIP flag disabled (AIP=false)")
        if not self.flags.aip_experiments:
            raise RuntimeError("AIP_EXPERIMENTS disabled")

        started = generated_at or datetime.now(timezone.utc)
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        started_at = _iso(started)

        ds = dataset or load_golden_dataset(request.dataset_id)
        candidate = self._resolve_candidate(request)

        # Isolated validation + CRE — no production singletons
        validation = ValidationService(
            store=ValidationStore(),
            flags=ValidationFlags(backtest=True, live=False),
        )
        replay = validation.run_replay(request.dataset_id, dataset=ds, generated_at=started)
        as_of = replay.days[-1].as_of if replay.days else started.date().isoformat()

        cre = CREService(store=CREStore(), flags=CREFlags(cre=True, promotion=False))
        cre_result = cre.evaluate(request.dataset_id, dataset=ds, generated_at=started)

        candidate_scored = score_universe(
            replay.days,
            candidate.weights,
            regime_filter=request.regime or candidate.regime,
            sector_filter=request.sector or candidate.sector,
        )
        # For fair baseline compare, score full universe with baseline weights too
        baseline_scored = score_universe(replay.days, baseline_weights())

        candidate_metrics = metrics_from_scored(candidate_scored, ds)
        current_l4 = metrics_from_replay_l4(replay.days, ds)
        current_e03 = metrics_from_replay_e03(replay.days, ds)
        # historical_replay / golden_dataset / paper_portfolio use L4 replay book as anchor
        historical = current_l4
        golden = current_l4
        paper = metrics_from_scored(baseline_scored, ds)

        comparisons = [
            BaselineComparison(
                baseline="current_l4",
                metrics=current_l4,
                deltas=delta(candidate_metrics, current_l4),
            ),
            BaselineComparison(
                baseline="current_e03",
                metrics=current_e03,
                deltas=delta(candidate_metrics, current_e03),
            ),
            BaselineComparison(
                baseline="historical_replay",
                metrics=historical,
                deltas=delta(candidate_metrics, historical),
            ),
            BaselineComparison(
                baseline="golden_dataset",
                metrics=golden,
                deltas=delta(candidate_metrics, golden),
            ),
            BaselineComparison(
                baseline="paper_portfolio",
                metrics=paper,
                deltas=delta(candidate_metrics, paper),
            ),
        ]

        p_value, significant = bootstrap_ic_pvalue(
            candidate_scored, baseline_scored, ds, n_bootstrap=200, seed=42
        )
        significance = SignificanceResult(
            method="paired_bootstrap_ic",
            n_bootstrap=200,
            p_value=p_value,
            significant=significant,
            alpha=0.05,
            detail="One-sided bootstrap on daily IC(candidate) - IC(baseline_weights)",
        )

        contribution = analyze_contributions(
            days=replay.days,
            dataset=ds,
            weights=candidate.weights,
            weight_set_id=candidate.weight_set_id,
            as_of=as_of,
        )
        calibration = build_calibration_plan(candidate_scored, ds, as_of=as_of)
        attribution = build_attribution(
            candidate_scored, ds, weight_set_id=candidate.weight_set_id
        )

        finished_at = _iso(started)
        experiment_id = _experiment_id(
            request.dataset_id,
            candidate.weight_set_id,
            started_at,
            request.hypothesis.statement,
        )
        name = request.name or f"{request.hypothesis.workstream}:{candidate.weight_set_id}"

        result = ExperimentResult(
            experiment_id=experiment_id,
            name=name,
            workstream=request.hypothesis.workstream,
            hypothesis=request.hypothesis,
            dataset_id=request.dataset_id,
            as_of=as_of,
            started_at=started_at,
            finished_at=finished_at,
            replay_run_id=replay.run.run_id,
            cre_evaluation_id=cre_result.evaluation_id,
            baseline_weight_set_id=WEIGHT_SET_ID,
            candidate_weight_set_id=candidate.weight_set_id,
            candidate_metrics=candidate_metrics,
            comparisons=comparisons,
            contribution=contribution,
            calibration=calibration,
            attribution=attribution,
            significance=significance,
            rollback=RollbackPlan(
                rollback_to_weight_set_id=WEIGHT_SET_ID,
                automatic=True,
                production_touched=False,
                notes=[
                    "Rollback is a no-op for production — experiments never mutate L4",
                    f"Shadow candidate {candidate.weight_set_id} discarded on rollback",
                ],
            ),
            promotion_ready=False,
            production_influence=False,
            l4_remains_shadow=True,
            flags=self.flags.as_dict(),
            notes=[
                "L4 remains shadow",
                "No production weight mutation",
                "Compared against current L4, E03, historical replay, golden dataset, paper portfolio",
            ],
        )

        evidence = build_promotion_evidence(
            result,
            self.flags,
            risk_approved=risk_approved,
            architecture_approved=architecture_approved,
        )
        result = result.model_copy(update={"promotion_ready": evidence.ready})
        self.store.put_experiment(result)
        self.store.put_promotion(evidence)
        return result

    def _resolve_candidate(self, request: ExperimentRequest) -> WeightSet:
        if request.candidate_weight_set_id:
            ws = self.registry.get(request.candidate_weight_set_id)
            if ws is None:
                raise ValueError(f"Unknown weight set: {request.candidate_weight_set_id}")
            return ws
        if request.candidate_weights:
            wid = "aip_adhoc_" + sha256(
                str(sorted(request.candidate_weights.items())).encode("utf-8")
            ).hexdigest()[:10]
            return self.registry.register(
                weight_set_id=wid,
                name=request.name or "Ad-hoc AIP candidate",
                weights=request.candidate_weights,
                description=request.hypothesis.statement,
                regime=request.regime,
                sector=request.sector,
                notes=["Registered from experiment request"],
            )
        # Default candidate for workstream experiments
        default_id = "aip_e03_heavier_v1"
        ws = self.registry.get(default_id)
        if ws is None:
            raise RuntimeError("Default AIP candidate missing from registry")
        return ws

    def health(self) -> dict:
        return {
            "status": "ok" if self.flags.aip else "disabled",
            "programme": "Alpha Improvement Programme",
            "l4_shadow": True,
            "production_influence": False,
            "flags": self.flags.as_dict(),
            "store": self.store.stats(),
            "n_weight_sets": len(self.registry.list()),
        }


def default_hypothesis(workstream: str = "AIP-02") -> ExperimentHypothesis:
    return ExperimentHypothesis(
        statement=(
            "Candidate L4 shadow weights improve IC and prediction accuracy "
            "versus current L4 without worsening max drawdown or calibration."
        ),
        workstream=workstream,
        expected_effect="Positive IC / hit-rate deltas with non-inferior risk",
    )
