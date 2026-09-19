"""Research Context Card — case file for every downstream specialist."""

from __future__ import annotations

from typing import Any


def build_research_context_card(
    *,
    question: str,
    primary_objective: str | None,
    entity: dict[str, Any],
    time_ctx: dict[str, Any],
    user_ctx: dict[str, Any],
    market_ctx: dict[str, Any],
    macro_ctx: dict[str, Any],
    comparison_ctx: dict[str, Any],
    expectation_ctx: dict[str, Any],
    portfolio_ctx: dict[str, Any],
    scenario_ctx: dict[str, Any],
    event_ctx: dict[str, Any],
    importance: dict[str, Any],
    expected_output: str | None,
    routing_confidence: float | None,
    iar: dict[str, Any] | None = None,
) -> dict[str, Any]:
    required_analysts = list((iar or {}).get("required_analysts") or [])
    suppressed = list((iar or {}).get("suppressed_analysts") or [])

    # Priority areas from importance + objective defaults
    priority_areas = list(importance.get("priority_order") or [])[:5]
    if primary_objective == "Investment Evaluation":
        priority_areas = [
            "Business Quality",
            "Financial Strength",
            "Valuation",
            "Portfolio Fit",
            "Downside Risks",
        ]

    ignore = []
    for a in ("Technical Analysis", "Ownership Review", "Educational Content", "Academy"):
        # Map suppressions to ignore list
        if a.replace(" Review", "").replace(" Analysis", "").replace(" Content", "") in suppressed or a in suppressed:
            ignore.append(a)
    if "Ownership" in suppressed and "Ownership Review" not in ignore:
        ignore.append("Ownership Review")
    if "Academy" in suppressed and "Educational Content" not in ignore:
        ignore.append("Educational Content")
    if "Market" in suppressed and "Technical Analysis" not in ignore:
        ignore.append("Technical Analysis")
    if primary_objective == "Investment Evaluation":
        for x in ("Technical Analysis", "Ownership Review", "Educational Content"):
            if x not in ignore:
                ignore.append(x)

    card = {
        "title": "Research Context",
        "question": question,
        "primary_objective": primary_objective,
        "entity": entity.get("entity"),
        "entity_type": entity.get("entity_type"),
        "ticker": entity.get("ticker"),
        "time_horizon": time_ctx.get("time_horizon"),
        "decision_type": user_ctx.get("decision_type"),
        "market_regime": market_ctx.get("market_regime") or market_ctx.get("regime"),
        "macro_environment": macro_ctx.get("environment") or macro_ctx.get("summary"),
        "relevant_comparisons": comparison_ctx.get("relevant_comparisons") or [],
        "comparison_lenses": comparison_ctx.get("lenses") or [],
        "expected_deliverable": expected_output or "Research Note",
        "priority_areas": priority_areas,
        "ignore": ignore,
        "portfolio_required": bool(portfolio_ctx.get("required")),
        "scenario": scenario_ctx.get("scenario"),
        "expectation": expectation_ctx.get("summary"),
        "events": event_ctx.get("events") or [],
        "required_analysts": required_analysts,
        "routing_confidence": routing_confidence,
        "yaml_preview": _yaml_preview(
            question=question,
            primary_objective=primary_objective,
            entity=entity.get("entity"),
            time_horizon=time_ctx.get("time_horizon"),
            decision_type=user_ctx.get("decision_type"),
            market_regime=market_ctx.get("market_regime") or market_ctx.get("regime"),
            macro_environment=macro_ctx.get("environment"),
            comparisons=comparison_ctx.get("relevant_comparisons") or [],
            expected_output=expected_output,
            priority_areas=priority_areas,
            ignore=ignore,
            routing_confidence=routing_confidence,
        ),
    }
    return card


def _yaml_preview(
    *,
    question: str,
    primary_objective: str | None,
    entity: str | None,
    time_horizon: str | None,
    decision_type: str | None,
    market_regime: str | None,
    macro_environment: str | None,
    comparisons: list[str],
    expected_output: str | None,
    priority_areas: list[str],
    ignore: list[str],
    routing_confidence: float | None,
) -> str:
    lines = [
        "Research Context",
        "",
        f"Question: {question}",
        f"Primary Objective: {primary_objective or '—'}",
        f"Entity: {entity or '—'}",
        f"Time Horizon: {time_horizon or '—'}",
        f"Decision Type: {decision_type or '—'}",
        f"Market Regime: {market_regime or '—'}",
        "Macro Environment:",
    ]
    if macro_environment:
        for part in str(macro_environment).split(";"):
            lines.append(f"  {part.strip()}")
    else:
        lines.append("  —")
    lines.append("Relevant Comparisons:")
    if comparisons:
        for c in comparisons:
            lines.append(f"  ✓ {c}")
    else:
        lines.append("  —")
    lines.append(f"Expected Deliverable: {expected_output or '—'}")
    lines.append("Priority Areas:")
    for i, p in enumerate(priority_areas, 1):
        lines.append(f"  {i}. {p}")
    lines.append("Ignore:")
    for ig in ignore:
        lines.append(f"  {ig}")
    conf = f"{(routing_confidence or 0) * 100:.1f}%" if routing_confidence is not None else "—"
    lines.append(f"Routing Confidence: {conf}")
    return "\n".join(lines)
