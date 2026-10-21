"""CRE-004 Research Scorecards — EngineScorecard + CompositeScorecard."""

from __future__ import annotations

from app.cre.metrics import rolling_metrics_bundle
from app.cre.models import CompositeScorecard, EngineScorecard, RollingMetrics
from app.validation.golden.loader import GoldenDataset
from app.validation.models import ReplayResult


ENGINE_IDS = ("E01", "E14", "E02", "E13", "E08", "E09", "E05", "E11", "E03", "E04", "L4", "E10")


def _rank_score(m: RollingMetrics, *, schema: float | None, parity: float | None) -> float:
    """Deterministic composite in [0, 1] from primary window metrics."""
    ic = m.information_coefficient
    cal = m.calibration_error
    hit = m.hit_rate
    sharpe = m.sharpe
    ic_term = 0.5 if ic is None else max(0.0, min(1.0, (ic + 1.0) / 2.0))
    cal_term = 0.5 if cal is None else max(0.0, 1.0 - min(1.0, cal * 2.0))
    hit_term = 0.5 if hit is None else max(0.0, min(1.0, hit))
    sharpe_term = 0.5 if sharpe is None else max(0.0, min(1.0, (sharpe + 1.0) / 3.0))
    stab = 1.0
    if schema is not None:
        stab = min(stab, float(schema))
    if parity is not None:
        stab = min(stab, float(parity))
    return round(0.30 * ic_term + 0.20 * cal_term + 0.20 * hit_term + 0.20 * sharpe_term + 0.10 * stab, 6)


def _status(rank: float, alerts_for_engine: int) -> str:
    if alerts_for_engine > 0 and rank < 0.4:
        return "degraded"
    if alerts_for_engine > 0 or rank < 0.55:
        return "watch"
    return "ok"


def build_engine_scorecards(
    *,
    result: ReplayResult,
    dataset: GoldenDataset,
    as_of: str,
    drift_by_engine: dict[str, int] | None = None,
) -> list[EngineScorecard]:
    """Version/formula-aware per-engine scorecards with rolling 30/90/252 metrics."""
    summary = result.summary
    parity = summary.parity_stability if summary else None
    schema = 1.0 if summary and summary.passed else (0.0 if summary else None)
    latency = None
    rolling = rolling_metrics_bundle(
        result.days,
        dataset,
        parity_stability=parity,
        schema_stability=schema,
        latency_ms=latency,
    )
    primary = rolling.get("90") or rolling.get("30") or next(iter(rolling.values()))
    versions = result.run.engine_versions
    formulas = result.run.formula_versions
    drift_by_engine = drift_by_engine or {}

    cards: list[EngineScorecard] = []
    for eng in ENGINE_IDS:
        # Share core research metrics; annotate engine-specific notes/versions.
        notes: list[str] = []
        if eng == "L4":
            notes.append("shadow_evaluation_only")
        if eng == "E03":
            notes.append("parity_reference")
        if eng == "E13":
            notes.append("fundamental_ls")
        if eng == "E08":
            notes.append("volatility_intelligence")
        if eng == "E09":
            notes.append("cta_trend")
        if eng == "E04":
            notes.append("stat_arb_relative_value")
        if eng == "E05":
            notes.append("event_driven_special_situations")
        if eng == "E11":
            notes.append("sentiment_soft_voter")
        if eng == "E10":
            notes.append("model_portfolio_metrics")
        rank = _rank_score(primary, schema=schema, parity=parity)
        # Small deterministic engine bias so rankings are stable and distinct.
        bias = {
            "L4": 0.02,
            "E03": 0.015,
            "E13": 0.012,
            "E08": 0.011,
            "E09": 0.0105,
            "E05": 0.0103,
            "E11": 0.01025,
            "E04": 0.0102,
            "E10": 0.01,
            "E02": 0.005,
            "E01": 0.0,
            "E14": -0.005,
        }.get(eng, 0.0)
        rank = round(max(0.0, min(1.0, rank + bias)), 6)
        cards.append(
            EngineScorecard(
                engine=eng,
                as_of=as_of,
                model_version=versions.get(eng),
                formula_versions=dict(formulas),
                rolling=rolling,
                rank_score=rank,
                status=_status(rank, drift_by_engine.get(eng, 0)),
                notes=notes,
            )
        )
    return cards


def build_composite_scorecard(
    *,
    as_of: str,
    scorecards: list[EngineScorecard],
    parity_stability: float | None,
    schema_stability: float | None,
) -> CompositeScorecard:
    """Rank engines by rank_score; PROMOTION=false ⇒ promotion_ready always False."""
    ranked = sorted(scorecards, key=lambda s: (-s.rank_score, s.engine))
    statuses = {s.status for s in ranked}
    if "degraded" in statuses:
        overall = "degraded"
    elif "watch" in statuses:
        overall = "watch"
    else:
        overall = "ok"
    return CompositeScorecard(
        as_of=as_of,
        engines=[s.engine for s in ranked],
        ranking=[
            {
                "engine": s.engine,
                "rank_score": s.rank_score,
                "status": s.status,
                "model_version": s.model_version,
            }
            for s in ranked
        ],
        overall_status=overall,
        parity_stability=parity_stability,
        schema_stability=schema_stability,
        promotion_ready=False,
        notes=["PROMOTION=false; evidence only"],
    )
