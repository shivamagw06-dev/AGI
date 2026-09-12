"""Generate institutional learning records without modifying historical forecasts."""

from __future__ import annotations

from forecast_validation_learning.schema import (
    ForecastValidation,
    InvestmentLearning,
    LEARNING_CATEGORIES,
)


def _category_for(scope: str, validation: ForecastValidation) -> str:
    scope_l = (scope or "company").lower()
    if validation.validation_status in {"Incorrect", "Partially Correct"}:
        # Prefer calibration categories when probability miss is large
        modal = validation.expected_outcome.modal_scenario
        p = float((validation.expected_outcome.probability_distribution or {}).get(modal) or 0)
        if not validation.difference.scenario_match and p >= 45:
            return "Probability calibration"
        if int(validation.expected_outcome.confidence_pct or 0) >= 75 and validation.validation_status == "Incorrect":
            return "Confidence calibration"
        if validation.difference.catalyst_hit_rate < 0.34:
            return "Catalyst effectiveness"
        if not validation.difference.scenario_match:
            return "Scenario quality"
    mapping = {
        "company": "Company forecasting",
        "sector": "Sector forecasting",
        "market": "Market forecasting",
        "macro": "Macro forecasting",
    }
    cat = mapping.get(scope_l, "Company forecasting")
    return cat if cat in LEARNING_CATEGORIES else "Company forecasting"


def generate_learning(validation: ForecastValidation) -> InvestmentLearning:
    entity = validation.entity
    expected = validation.expected_outcome
    actual = validation.actual_outcome
    diff = validation.difference
    status = validation.validation_status

    topic = f"{entity} forecast validation ({validation.scope})"

    observations: list[str] = []
    if diff.scenario_match:
        observations.append(f"{expected.modal_scenario} scenario forecast accurate")
    else:
        observations.append(
            f"Expected {expected.modal_scenario}, realized {actual.realized_scenario}"
        )
    if diff.growth_match:
        observations.append("Growth direction aligned")
    else:
        observations.append(
            f"Growth systematically {'over' if expected.growth_direction == 'up' and actual.growth_direction != 'up' else 'mis'}-estimated "
            f"({expected.growth_direction}→{actual.growth_direction})"
        )
    if not diff.margin_match:
        if expected.margin_direction == "down" and actual.margin_direction in {"up", "stable"}:
            observations.append("Margins consistently underestimated")
        elif expected.margin_direction == "up" and actual.margin_direction == "down":
            observations.append("Margins overestimated versus outcome")
        else:
            observations.append(
                f"Margin path differed ({expected.margin_direction}→{actual.margin_direction})"
            )
    if diff.catalyst_hit_rate >= 0.5:
        observations.append("Key catalysts partially or fully materialized")
    elif expected.catalysts:
        observations.append("Catalyst set underperformed relative to watchlist")

    if actual.notes:
        observations.append(actual.notes)

    observation = ". ".join(observations[:4]) + ("." if observations else "")

    # Learning narrative
    if status == "Validated":
        learning = (
            f"Forecast for {entity} held under institutional scrutiny. "
            f"{diff.summary}. Process quality supports reuse of the same evidence hierarchy."
        )
        guidance = (
            "Maintain current weighting of evidence hierarchy for similar entities; "
            "continue registering forecasts before publication."
        )
    elif status == "Partially Correct":
        learning = (
            f"Partial accuracy on {entity}: directionally useful but incomplete. "
            f"{diff.summary}."
        )
        if "guidance" in observation.lower() or any(
            "guidance" in c.lower() for c in expected.catalysts
        ):
            learning = (
                f"Revenue or growth path was directionally right for {entity}, "
                "but management commentary / guidance carried more predictive value "
                "than valuation changes alone."
            )
            guidance = (
                "Increase weighting of management guidance for similar companies "
                "when constructing expected outcomes."
            )
        else:
            guidance = (
                "Tighten scenario boundaries and catalyst specificity before next publication."
            )
    elif status == "Incorrect":
        learning = (
            f"Forecast for {entity} missed realized path ({actual.realized_scenario}). "
            f"{diff.summary}."
        )
        if expected.modal_scenario == "Bull" and actual.realized_scenario in {"Base", "Bear"}:
            guidance = "Reduce overweight on Bull scenarios unless catalyst evidence is High."
        elif expected.modal_scenario == "Base" and actual.realized_scenario == "Bull":
            guidance = (
                "Bull probability calibration requires review for this cohort; "
                "do not silently raise point forecasts — adjust probability mass with evidence."
            )
        else:
            guidance = (
                "Record bias indicator and require additional contradictory evidence "
                "before republishing similar forecasts."
            )
    else:
        learning = f"Outcome for {entity} remains indeterminate; insufficient actual evidence."
        guidance = "Keep forecast in Monitoring until actual outcomes are institutionally observed."

    bias_flags: list[str] = []
    if expected.growth_direction == "up" and actual.growth_direction == "down":
        bias_flags.append("growth_overestimated")
    if expected.margin_direction == "down" and actual.margin_direction == "up":
        bias_flags.append("margins_underestimated")
    if expected.modal_scenario == "Bull" and not diff.scenario_match:
        bias_flags.append("bull_overweighted")
    if validation.scope == "macro" and diff.catalyst_hit_rate < 0.34:
        bias_flags.append("macro_catalysts_underweighted")
    if (
        float((expected.probability_distribution or {}).get("Bull") or 0) <= 30
        and actual.realized_scenario == "Bull"
    ):
        bias_flags.append("bull_probability_understated")

    return InvestmentLearning(
        topic=topic,
        observation=observation,
        learning=learning,
        future_guidance=guidance,
        category=_category_for(validation.scope, validation),
        forecast_id=validation.forecast_id,
        validation_id=validation.validation_id,
        entity=entity,
        scope=validation.scope,
        outcome_status=status,
        bias_flags=bias_flags,
        history_rewritten=False,
        knowledge_factory_updated=False,
        process_memory=True,
    )
