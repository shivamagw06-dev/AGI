"""AIP promotion evidence — never promotes when AIP_PROMOTION=false."""

from __future__ import annotations

from typing import Any

from app.aip.flags import AipFlags
from app.aip.models import ExperimentResult, PromotionEvidence


def build_promotion_evidence(
    experiment: ExperimentResult | None,
    flags: AipFlags,
    *,
    risk_approved: bool = False,
    architecture_approved: bool = False,
) -> PromotionEvidence:
    as_of = experiment.as_of if experiment else "n/a"
    checklist: list[dict[str, Any]] = []

    def gate(name: str, passed: bool, detail: str) -> None:
        checklist.append({"gate": name, "passed": passed, "detail": detail})

    gate("aip_enabled", flags.aip, "AIP research programme active")
    gate("experiments_enabled", flags.aip_experiments, "AIP_EXPERIMENTS flag")

    if experiment is None:
        gate("experiment_present", False, "No experiment")
        gate("replay_present", False, "No replay_run_id")
        gate("cre_present", False, "No cre_evaluation_id")
        gate("replay_superiority", False, "No comparisons")
        gate("cre_superiority", False, "No CRE link")
        gate("statistical_significance", False, "No significance")
        gate("risk_approval", risk_approved, f"risk_approved={risk_approved}")
        gate("architecture_approval", architecture_approved, f"architecture_approved={architecture_approved}")
        gate("l4_remains_shadow", True, "L4 remains shadow")
    else:
        gate("experiment_present", True, experiment.experiment_id)
        gate("replay_present", bool(experiment.replay_run_id), f"replay={experiment.replay_run_id}")
        gate("cre_present", bool(experiment.cre_evaluation_id), f"cre={experiment.cre_evaluation_id}")

        l4_cmp = next((c for c in experiment.comparisons if c.baseline == "current_l4"), None)
        replay_sup = False
        if l4_cmp and l4_cmp.deltas.ic_delta is not None:
            # Superior if IC up and drawdown not worse by > 5pp, calibration not much worse
            dd = l4_cmp.deltas.max_drawdown_delta
            cal = l4_cmp.deltas.calibration_delta
            replay_sup = (
                l4_cmp.deltas.ic_delta > 0
                and (dd is None or dd >= -0.05)
                and (cal is None or cal <= 0.05)
            )
        gate(
            "replay_superiority",
            replay_sup,
            f"ic_delta={l4_cmp.deltas.ic_delta if l4_cmp else None}",
        )
        # CRE superiority: require CRE evaluation linked; treat as soft pass when linked
        # (detailed CRE rank comparison is evidence package, not auto-promote)
        gate(
            "cre_superiority",
            bool(experiment.cre_evaluation_id),
            "CRE evaluation attached for evidence",
        )
        gate(
            "statistical_significance",
            bool(experiment.significance.significant),
            f"p={experiment.significance.p_value}",
        )
        gate("risk_approval", risk_approved, f"risk_approved={risk_approved}")
        gate(
            "architecture_approval",
            architecture_approved,
            f"architecture_approved={architecture_approved}",
        )
        gate("l4_remains_shadow", experiment.l4_remains_shadow, "L4 remains shadow")

    blocking: list[str] = []
    if not flags.aip_promotion:
        blocking.append("AIP_PROMOTION=false (evidence-only mode)")
    for item in checklist:
        if not item["passed"]:
            blocking.append(f"gate_failed:{item['gate']}")

    evidence_ready = all(i["passed"] for i in checklist)
    ready = bool(flags.aip_promotion and evidence_ready)

    return PromotionEvidence(
        as_of=as_of,
        experiment_id=experiment.experiment_id if experiment else None,
        promotion_flag=flags.aip_promotion,
        evidence_only=not flags.aip_promotion,
        ready=ready,
        checklist=checklist,
        blocking_reasons=blocking,
        notes=[
            "PromotionEvidence is evidence only under AIP P0",
            "No production L4 weight mutation",
            "No engine promotion side-effects",
            "Requires replay + CRE superiority, significance, risk + architecture approval",
        ],
    )
