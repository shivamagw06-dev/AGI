"""Naive weighted vote — P0 Shadow (no Bayes / ML / probability calibration)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.engines.l4.collector import (
    CollectedInputs,
    e01_signed,
    e02_context,
    e03_signed,
    e14_signed,
)
from app.engines.l4.conflict import ConflictResolution
from app.engines.l4.mapping import LABEL_THRESHOLDS, VOTER_WEIGHTS, WEIGHT_SET_ID


@dataclass(frozen=True)
class FusionResult:
    composite_score: float
    label: str
    confidence: float
    engine_contributions: list[dict[str, Any]]
    dominant_drivers: list[dict[str, Any]]
    weight_set_id: str = WEIGHT_SET_ID


def fuse_shadow_vote(
    inputs: CollectedInputs,
    resolution: ConflictResolution,
    *,
    evidence: dict[str, list[dict[str, Any]]],
) -> FusionResult:
    e11_signed = 0.0
    e11_conf = 0.0
    e11_w = 0.0
    if inputs.e11 is not None:
        e11_signed = max(-1.0, min(1.0, (inputs.e11.composite_score - 50.0) / 50.0))
        e11_conf = float(inputs.e11.confidence)
        e11_w = min(float(inputs.e11.soft_voter_weight or 0.0), float(VOTER_WEIGHTS.get("E11", 0.05)))

    signed_map = {
        "E03": e03_signed(inputs.e03),
        "E01": e01_signed(inputs.e01),
        "E14": e14_signed(inputs.e14),
        "E11": e11_signed,
        "E02": 0.0,  # context only
    }
    conf_map = {
        "E03": float(inputs.e03.confidence) if inputs.e03 else 0.0,
        "E01": float(inputs.e01.confidence.value) if inputs.e01 else 0.0,
        "E14": float(inputs.e14.confidence.value) if inputs.e14 else 0.0,
        "E11": e11_conf,
        "E02": float(inputs.e02.factor_confidence) if inputs.e02 else 0.0,
    }

    num = 0.0
    den = 0.0
    contributions: list[dict[str, Any]] = []
    for eng, w in VOTER_WEIGHTS.items():
        if w <= 0:
            continue
        if eng == "E03" and inputs.e03 is None:
            continue
        if eng == "E01" and inputs.e01 is None:
            continue
        if eng == "E14" and inputs.e14 is None:
            continue
        if eng == "E11":
            # Chaos acceptance: absent soft voter ⇒ weight 0, L4 continues
            if inputs.e11 is None or e11_w <= 0:
                continue
            w = e11_w
        x = signed_map[eng]
        c = max(0.05, conf_map[eng])
        effective = w * c
        num += effective * x
        den += effective
        contributions.append(
            {
                "engine": eng,
                "weight": w,
                "confidence": round(c, 4),
                "signed": round(x, 4),
                "contribution": round(effective * x, 4),
                "direction": "bullish" if x > 0.05 else "bearish" if x < -0.05 else "neutral",
            }
        )

    blended = (num / den) if den > 0 else 0.0
    score = round(50.0 + 50.0 * max(-1.0, min(1.0, blended)), 1)

    if resolution.prefer_neutral:
        # Pull toward 50 without erasing signal entirely
        score = round(50.0 + (score - 50.0) * 0.35, 1)

    label = _label_from_score(score)

    voter_mean = (
        sum(conf_map[c["engine"]] for c in contributions) / len(contributions) if contributions else 0.4
    )
    completeness = inputs.completeness
    conf = max(
        0.05,
        min(
            0.95,
            voter_mean * resolution.confidence_mult * (0.6 + 0.4 * completeness),
        ),
    )
    conf = round(conf, 4)

    ranked = sorted(contributions, key=lambda c: abs(c["contribution"]), reverse=True)
    dominant = [
        {
            "engine": c["engine"],
            "contribution": abs(c["contribution"]),
            "direction": c["direction"] if c["engine"] != "E14" else "risk_penalty",
        }
        for c in ranked[:3]
    ]
    # Always surface E02 context in drivers metadata path via zero-weight note
    ctx = e02_context(inputs.e02)
    if ctx:
        dominant.append(
            {
                "engine": "E02",
                "contribution": 0.0,
                "direction": "context",
                "dominant_factor": ctx.get("dominant_factor"),
            }
        )

    _ = evidence  # used by caller for explanation; keep signature stable
    return FusionResult(
        composite_score=score,
        label=label,
        confidence=conf,
        engine_contributions=contributions,
        dominant_drivers=dominant,
    )


def _label_from_score(score: float) -> str:
    for threshold, label in LABEL_THRESHOLDS:
        if score >= threshold:
            return label
    return "Strong Bearish"
