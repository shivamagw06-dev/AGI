"""Side-by-side legacy vs SM_AGI_TECH parity audit (M0 exit: ≥99% within 0.1)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.engines.e03.legacy import (
    category_legacy,
    confidence_legacy,
    score_research_legacy,
)
from app.engines.e03.mapping import ENGINE_VERSION, MODEL_VERSION
from app.engines.e03.submodels.agi_tech import run_sm_agi_tech


class ParityRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    symbol: str
    legacy_score: float
    new_score: float
    difference: float
    legacy_label: str
    new_label: str
    agreement: bool
    confidence_difference: float
    timestamp: str
    engine_version: str = ENGINE_VERSION
    model_version: str = MODEL_VERSION


class ParityReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    as_of: str
    generated_at: str
    n_symbols: int
    agreement_rate: float
    bucket_agreement_rate: float
    confidence_agreement_rate: float
    mean_drift: float
    max_drift: float
    within_0_1_rate: float
    pass_threshold: float = 0.99
    passed: bool
    rows: list[ParityRow] = Field(default_factory=list)
    engine_version: str = ENGINE_VERSION
    model_version: str = MODEL_VERSION


def run_parity_audit(
    panels: dict[str, dict[str, Any]],
    *,
    as_of: str,
    score_tolerance: float = 0.1,
    generated_at: datetime | None = None,
) -> ParityReport:
    """Compare legacy score_research vs SM_AGI_TECH for each symbol panel."""
    ts = generated_at or datetime.now(timezone.utc)
    rows: list[ParityRow] = []
    drifts: list[float] = []
    score_ok = 0
    bucket_ok = 0
    conf_ok = 0

    for symbol, indicators in sorted(panels.items()):
        legacy_score = score_research_legacy(indicators)
        legacy_label = category_legacy(legacy_score)
        legacy_conf = confidence_legacy(legacy_score, indicators)
        result = run_sm_agi_tech(indicators)
        diff = round(result.agi_tech_score - legacy_score, 6)
        abs_diff = abs(diff)
        drifts.append(abs_diff)
        score_agree = abs_diff <= score_tolerance
        label_agree = result.label == legacy_label
        conf_diff = float(result.confidence_pct - legacy_conf)
        conf_agree = abs(conf_diff) <= 0.0  # exact for P0
        if score_agree:
            score_ok += 1
        if label_agree:
            bucket_ok += 1
        if conf_agree:
            conf_ok += 1
        rows.append(
            ParityRow(
                symbol=symbol.upper(),
                legacy_score=legacy_score,
                new_score=result.agi_tech_score,
                difference=diff,
                legacy_label=legacy_label,
                new_label=result.label,
                agreement=score_agree and label_agree,
                confidence_difference=conf_diff,
                timestamp=ts.isoformat(),
            )
        )

    n = max(len(rows), 1)
    mean_drift = sum(drifts) / len(drifts) if drifts else 0.0
    max_drift = max(drifts) if drifts else 0.0
    within = score_ok / n
    bucket = bucket_ok / n
    conf_rate = conf_ok / n
    # Primary gate: score within 0.1; also require bucket parity for pass
    passed = within >= 0.99 and bucket >= 0.99

    return ParityReport(
        as_of=as_of,
        generated_at=ts.isoformat(),
        n_symbols=len(rows),
        agreement_rate=round(within, 6),
        bucket_agreement_rate=round(bucket, 6),
        confidence_agreement_rate=round(conf_rate, 6),
        mean_drift=round(mean_drift, 6),
        max_drift=round(max_drift, 6),
        within_0_1_rate=round(within, 6),
        passed=passed,
        rows=rows,
    )
