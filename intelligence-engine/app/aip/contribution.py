"""AIP-03 Engine contribution analysis + marginal information gain."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from app.aip.fusion_shadow import score_universe
from app.aip.metrics import delta, metrics_from_scored
from app.aip.models import ContributionReport, EngineContribution
from app.validation.golden.loader import GoldenDataset
from app.validation.models import ReplayDaySlice


def _report_id(dataset_id: str, weight_set_id: str, as_of: str) -> str:
    raw = f"aip_contrib|{dataset_id}|{weight_set_id}|{as_of}"
    return "contrib_" + sha256(raw.encode("utf-8")).hexdigest()[:16]


def analyze_contributions(
    *,
    days: list[ReplayDaySlice],
    dataset: GoldenDataset,
    weights: dict[str, float],
    weight_set_id: str,
    as_of: str,
) -> ContributionReport:
    """Leave-one-out: contribution ≈ metrics(full) − metrics(without engine)."""
    full_scored = score_universe(days, weights)
    full = metrics_from_scored(full_scored, dataset)
    engines: list[EngineContribution] = []

    for eng, w in weights.items():
        if eng == "E02":
            engines.append(
                EngineContribution(
                    engine=eng,
                    baseline_weight=float(w),
                    notes=["Context-only voter (weight 0 by design)"],
                )
            )
            continue
        ablated = dict(weights)
        ablated[eng] = 0.0
        scored = score_universe(days, ablated)
        m = metrics_from_scored(scored, dataset)
        d = delta(full, m)  # positive => engine helps when present
        mig = d.ic_delta
        alpha = d.prediction_accuracy_delta
        helps_alpha = (alpha or 0.0) > 0
        helps_sharpe = (d.sharpe_delta or 0.0) > 0
        helps_dd = (d.max_drawdown_delta or 0.0) > 0  # less negative / higher
        helps_cal = (d.calibration_delta or 0.0) < 0  # lower error better
        hurts = (alpha or 0.0) < 0 and (d.sharpe_delta or 0.0) < 0
        engines.append(
            EngineContribution(
                engine=eng,
                baseline_weight=float(w),
                alpha_delta=alpha,
                sharpe_delta=d.sharpe_delta,
                sortino_delta=d.sortino_delta,
                max_drawdown_delta=d.max_drawdown_delta,
                ic_delta=d.ic_delta,
                hit_rate_delta=d.hit_rate_delta,
                calibration_delta=d.calibration_delta,
                marginal_information_gain=mig,
                recommend_larger_weight=bool(helps_alpha or helps_sharpe or (mig or 0) > 0),
                recommend_smaller_weight=bool(hurts and not helps_dd and not helps_cal),
                notes=_notes(eng, helps_alpha, helps_sharpe, helps_dd, helps_cal, mig),
            )
        )

    engines.sort(key=lambda e: (e.marginal_information_gain or -999), reverse=True)
    return ContributionReport(
        report_id=_report_id(dataset.dataset_id, weight_set_id, as_of),
        as_of=as_of,
        dataset_id=dataset.dataset_id,
        weight_set_id=weight_set_id,
        engines=engines,
        production_influence=False,
    )


def _notes(
    eng: str,
    helps_alpha: bool,
    helps_sharpe: bool,
    helps_dd: bool,
    helps_cal: bool,
    mig: float | None,
) -> list[str]:
    out = [f"leave_one_out_engine={eng}"]
    if helps_alpha:
        out.append("improves_alpha")
    if helps_sharpe:
        out.append("improves_sharpe")
    if helps_dd:
        out.append("improves_drawdown")
    if helps_cal:
        out.append("improves_calibration")
    if mig is not None:
        out.append(f"mig={mig}")
    return out


def contribution_summary(report: ContributionReport) -> dict[str, Any]:
    return {
        "report_id": report.report_id,
        "larger_weight": [e.engine for e in report.engines if e.recommend_larger_weight],
        "smaller_weight": [e.engine for e in report.engines if e.recommend_smaller_weight],
        "by_mig": [
            {"engine": e.engine, "mig": e.marginal_information_gain}
            for e in report.engines
            if e.engine != "E02"
        ],
    }
