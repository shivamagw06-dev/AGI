"""E14Assessment builder — per-object risk assessment (spec §9.2)."""

from __future__ import annotations

from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e14.features.builder import RiskFeatureVector
from app.engines.e14.mapping import MODEL_VERSION
from app.engines.e14.models.rules import RiskClassification


TargetType = Literal["signal", "portfolio", "note", "sleeve"]


class E14Assessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment_id: str
    target_type: TargetType
    target_id: str
    as_of: str
    risk_score: float
    crowding_score: float
    liquidity_score: float
    tail_risk_score: float
    size_multiplier: float
    confidence_adjustment: float
    expected_return_haircut: float
    max_allocation: float
    suggested_hedging: list[dict[str, Any]] = Field(default_factory=list)
    expected_drawdown_3m_p95: float | None = None
    risk_flags: list[dict[str, Any]] = Field(default_factory=list)
    taxonomy_ids: list[str] = Field(default_factory=list)
    gate: str
    explain: dict[str, Any] = Field(default_factory=dict)
    e14_state_hash: str | None = None
    model_version: str = MODEL_VERSION


def build_assessment(
    *,
    target_type: TargetType,
    target_id: str,
    as_of: str,
    fv: RiskFeatureVector,
    classification: RiskClassification,
    e14_state_hash: str | None = None,
    target_features: dict[str, float] | None = None,
) -> E14Assessment:
    """Merge firm classification with optional per-target feature overlays."""
    risk_score = classification.risk_score
    crowding = classification.crowding_score
    liquidity = classification.liquidity_score
    tail = classification.tail_risk_score
    size_mult = classification.size_multiplier
    conf_adj = classification.confidence_adjustment
    gate = classification.gate
    flags = list(classification.risk_flags)

    # Tighten from target overlays (P0 deterministic rules)
    tf = target_features or {}
    if "pct_adv_proposed" in tf and tf["pct_adv_proposed"] > 2.0:
        liquidity = min(liquidity, 35.0)
        size_mult = min(size_mult, 0.55)
        conf_adj = min(conf_adj, 0.80)
        flags.append(
            {
                "taxonomy_id": "RK_LIQUIDITY",
                "severity": "S2",
                "message": f"pct_adv_proposed {tf['pct_adv_proposed']:.2f} exceeds 2.0",
            }
        )
        if gate == "allow":
            gate = "allow_with_haircut"
    if "herding_agib" in tf and tf["herding_agib"] >= 65:
        crowding = max(crowding, tf["herding_agib"])
        risk_score = max(risk_score, 65.0)
    if risk_score >= 75:
        gate = "block_promotion"
    if risk_score >= 90:
        gate = "research_hedge_only"
        size_mult = min(size_mult, 0.40)

    # Max allocation (spec §7.9 simplified)
    w_policy = 0.08
    if crowding >= 80:
        w_crowd = 0.5 * w_policy
    elif crowding >= 65:
        w_crowd = 0.75 * w_policy
    else:
        w_crowd = w_policy
    w_liq = w_policy if liquidity >= 40 else 0.5 * w_policy
    max_alloc = min(w_policy, w_crowd, w_liq)

    haircut = float(max(0.0, min(1.0, 1.0 - conf_adj * (1.0 - risk_score / 200.0))))
    dd = fv.get("expected_dd_3m_p95")

    # Unique taxonomy ids from flags S2+
    tax_ids = sorted(
        {
            f["taxonomy_id"]
            for f in flags
            if f.get("severity") in {"S2", "S3", "S4"}
        }
    )
    if not tax_ids:
        tax_ids = list(classification.top_risk_drivers[:3])

    drivers = [
        {"feature": d, "contribution": round(classification.taxonomy_scores.get(d, 0) / 100.0, 3)}
        for d in classification.top_risk_drivers[:5]
    ]

    return E14Assessment(
        assessment_id=str(uuid4()),
        target_type=target_type,
        target_id=target_id,
        as_of=as_of,
        risk_score=float(round(risk_score, 4)),
        crowding_score=float(round(crowding, 2)),
        liquidity_score=float(round(liquidity, 2)),
        tail_risk_score=float(round(tail, 2)),
        size_multiplier=float(round(size_mult, 4)),
        confidence_adjustment=float(round(conf_adj, 4)),
        expected_return_haircut=float(round(haircut, 4)),
        max_allocation=float(round(max_alloc, 4)),
        suggested_hedging=list(classification.suggested_hedging),
        expected_drawdown_3m_p95=dd,
        risk_flags=flags,
        taxonomy_ids=tax_ids,
        gate=gate,
        explain={
            "top_risk_drivers": drivers,
            "narrative_points": [
                f"Firm playbook={classification.playbook}; gate={gate}",
                f"size_multiplier={size_mult:.2f}, confidence_adjustment={conf_adj:.2f}",
            ],
        },
        e14_state_hash=e14_state_hash,
        model_version=MODEL_VERSION,
    )
