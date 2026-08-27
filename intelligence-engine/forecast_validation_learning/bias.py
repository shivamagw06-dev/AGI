"""Detect recurring forecasting biases across immutable validations."""

from __future__ import annotations

from typing import Any

from forecast_validation_learning.schema import BiasIndicator, ForecastValidation


def detect_biases(validations: list[ForecastValidation]) -> list[BiasIndicator]:
    if not validations:
        return []

    n = len(validations)
    growth_over = 0
    margin_under = 0
    bull_over = 0
    macro_under = 0
    bull_understated = 0

    for v in validations:
        exp = v.expected_outcome
        act = v.actual_outcome
        if exp.growth_direction == "up" and act.growth_direction == "down":
            growth_over += 1
        if exp.margin_direction in {"down", "stable"} and act.margin_direction == "up":
            if exp.margin_direction == "down" or (
                exp.margin_direction == "stable" and act.margin_direction == "up"
            ):
                if exp.margin_direction == "down":
                    margin_under += 1
        if exp.modal_scenario == "Bull" and act.realized_scenario in {"Base", "Bear"}:
            bull_over += 1
        if v.scope == "macro" and v.difference.catalyst_hit_rate < 0.34:
            macro_under += 1
        bull_p = float((exp.probability_distribution or {}).get("Bull") or 0)
        if bull_p <= 30 and act.realized_scenario == "Bull":
            bull_understated += 1

    indicators: list[BiasIndicator] = []

    def _sev(count: int) -> str:
        ratio = count / n
        if ratio >= 0.45:
            return "high"
        if ratio >= 0.25:
            return "moderate"
        return "low"

    if growth_over:
        indicators.append(
            BiasIndicator(
                code="growth_overestimated",
                label="Growth systematically overestimated",
                severity=_sev(growth_over),
                evidence_count=growth_over,
                detail=f"{growth_over}/{n} validations showed growth downside vs expected up.",
                recommendation="Require harder demand evidence before locking growth-up expected outcomes.",
            )
        )
    if margin_under:
        indicators.append(
            BiasIndicator(
                code="margins_underestimated",
                label="Margins consistently underestimated",
                severity=_sev(margin_under),
                evidence_count=margin_under,
                detail=f"{margin_under}/{n} validations realized stronger margins than expected.",
                recommendation="Increase weight of cost-discipline / mix evidence in margin paths.",
            )
        )
    if bull_over:
        indicators.append(
            BiasIndicator(
                code="bull_overweighted",
                label="Bull scenarios overweighted",
                severity=_sev(bull_over),
                evidence_count=bull_over,
                detail=f"{bull_over}/{n} Bull-modal forecasts failed to realize Bull.",
                recommendation="Cap Bull modal selection without High catalyst evidence.",
            )
        )
    if bull_understated:
        indicators.append(
            BiasIndicator(
                code="bull_probability_understated",
                label="Bull probability calibration requires review",
                severity=_sev(bull_understated),
                evidence_count=bull_understated,
                detail=(
                    f"{bull_understated}/{n} cases realized Bull while predicted Bull mass ≤ 30%."
                ),
                recommendation="Recalibrate Bull probability mass for similar cohorts — process review, not silent rewriting.",
            )
        )
    if macro_under:
        indicators.append(
            BiasIndicator(
                code="macro_catalysts_underweighted",
                label="Macro catalysts underweighted",
                severity=_sev(macro_under),
                evidence_count=macro_under,
                detail=f"{macro_under}/{n} macro validations had weak catalyst hit-rates.",
                recommendation="Elevate RBI / inflation / yield catalysts in macro expected outcomes.",
            )
        )

    return indicators


def bias_dashboard(validations: list[ForecastValidation]) -> dict[str, Any]:
    indicators = detect_biases(validations)
    return {
        "bias_indicators": [i.model_dump(mode="json") for i in indicators],
        "n_validations": len(validations),
        "process_improvement_only": True,
        "model_retraining": False,
        "history_rewritten": False,
    }
