"""CRE-005 Promotion Evidence — evidence-only reports; never promotes when PROMOTION=false."""

from __future__ import annotations

from typing import Any

from app.cre.flags import CREFlags
from app.cre.models import CompositeScorecard, EngineScorecard, PromotionReport, RollingMetrics


def build_promotion_report(
    *,
    as_of: str,
    scorecards: list[EngineScorecard],
    composite: CompositeScorecard,
    flags: CREFlags,
    engine_versions: dict[str, str],
    formula_versions: dict[str, str],
    drift_alert_count: int,
    regression_alert_count: int,
) -> PromotionReport:
    """Assemble promotion evidence checklist. Ready is False unless PROMOTION=true AND gates pass."""
    best = max(scorecards, key=lambda s: s.rank_score) if scorecards else None
    primary: RollingMetrics | None = None
    if best is not None:
        primary = best.rolling.get("90") or best.rolling.get("30")

    checklist: list[dict[str, Any]] = [
        {
            "gate": "cre_enabled",
            "passed": flags.cre,
            "detail": "CRE platform active",
        },
        {
            "gate": "parity_stability",
            "passed": (composite.parity_stability or 0.0) >= 0.99,
            "detail": f"parity_stability={composite.parity_stability}",
        },
        {
            "gate": "schema_stability",
            "passed": (composite.schema_stability or 0.0) >= 1.0,
            "detail": f"schema_stability={composite.schema_stability}",
        },
        {
            "gate": "no_critical_regression",
            "passed": regression_alert_count == 0,
            "detail": f"regression_alerts={regression_alert_count}",
        },
        {
            "gate": "rolling_metrics_present",
            "passed": primary is not None and primary.days_used > 0,
            "detail": f"days_used={primary.days_used if primary else 0}",
        },
        {
            "gate": "rank_score_threshold",
            "passed": best is not None and best.rank_score >= 0.55,
            "detail": f"best={best.engine if best else None} rank_score={best.rank_score if best else None}",
        },
    ]

    blocking: list[str] = []
    if not flags.promotion:
        blocking.append("PROMOTION=false (evidence-only mode)")
    for item in checklist:
        if not item["passed"]:
            blocking.append(f"gate_failed:{item['gate']}")

    evidence_ready = all(i["passed"] for i in checklist)
    # Architecture lock: never mark ready when PROMOTION=false
    ready = bool(flags.promotion and evidence_ready)

    notes = [
        "PromotionReport is evidence only under P0",
        "No production influence",
        "No engine promotion side-effects",
    ]
    if drift_alert_count:
        notes.append(f"drift_alerts={drift_alert_count}")

    return PromotionReport(
        as_of=as_of,
        engine=best.engine if best else None,
        promotion_flag=flags.promotion,
        evidence_only=not flags.promotion,
        ready=ready,
        checklist=checklist,
        blocking_reasons=blocking,
        engine_versions=dict(engine_versions),
        formula_versions=dict(formula_versions),
        notes=notes,
    )
