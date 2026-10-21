"""Macro Analyst — Does macro help or hurt?"""

from __future__ import annotations

from typing import Any

from institutional_analysts.base import as_list, company_name, pick_confidence, structured_opinion


def analyse(ctx: dict[str, Any]) -> dict[str, Any]:
    briefing = ctx.get("institutional_briefing") if isinstance(ctx.get("institutional_briefing"), dict) else {}
    irp = ctx.get("irp") if isinstance(ctx.get("irp"), dict) else {}
    aws_macro = ctx.get("aws_macro") if isinstance(ctx.get("aws_macro"), dict) else {}
    leo = ctx.get("live_evidence") if isinstance(ctx.get("live_evidence"), dict) else {}
    de = ctx.get("decision_engine") if isinstance(ctx.get("decision_engine"), dict) else {}
    layers = {str(l.get("id")): l for l in (de.get("layers") or []) if isinstance(l, dict)}
    macro_layer = layers.get("macro") or {}
    macro = (
        briefing.get("macro")
        if isinstance(briefing.get("macro"), dict)
        else irp.get("macro")
        if isinstance(irp.get("macro"), dict)
        else aws_macro
    )
    if not isinstance(macro, dict):
        macro = {}
    name = company_name(ctx)

    transmission = (
        briefing.get("macro_transmission")
        or macro.get("transmission")
        or macro_layer.get("reasoning")
        or f"Macro transmits to {name} mainly through rates, liquidity, growth, and currency."
    )
    outlook = str(briefing.get("current_outlook") or macro.get("outlook") or macro_layer.get("reasoning") or "")
    stance = "Bullish" if any(w in outlook.lower() for w in ("support", "ease", "help", "construct")) else "Neutral"
    if any(w in outlook.lower() for w in ("hurt", "tight", "headwind", "pressure")):
        stance = "Bearish"

    evidence = as_list(leo.get("sources_used") or macro.get("evidence") or briefing.get("macro_drivers"), limit=6)
    if not evidence:
        evidence = ["Policy rate and liquidity backdrop", "Growth and inflation path"]

    coverage = pick_confidence(macro.get("confidence"), macro_layer.get("score"), default=0.55)
    return structured_opinion(
        role="macro",
        summary=f"Macro backdrop for {name}: rates, inflation, growth, and liquidity set the external constraint.",
        strengths=as_list([macro.get("liquidity") or "Liquidity conditions watchable", outlook or "Outlook data-dependent"], limit=3),
        weaknesses=as_list([macro.get("oil") or "Commodity shocks can alter the path", "Transmission lags remain uncertain"], limit=3),
        evidence=evidence,
        unanswered_questions=[
            "How quickly do policy rates transmit into funding costs and demand?",
            "Is growth resilient enough to offset any liquidity tightening?",
        ],
        sections={
            "interest_rates": macro.get("interest_rates") or macro.get("rates") or "Policy rates influence funding costs and multiples",
            "inflation": macro.get("inflation") or "Inflation path affects real incomes and input costs",
            "gdp": macro.get("gdp") or macro.get("growth") or "Growth cycle supports or pressures franchise demand",
            "liquidity": macro.get("liquidity") or "Liquidity conditions affect credit and risk appetite",
            "currency": macro.get("currency") or macro.get("fx") or "FX moves matter for foreign earnings and imports",
            "oil": macro.get("oil") or macro.get("commodity") or "Commodity shocks can alter margins and inflation",
            "macro_outlook": outlook or "Outlook remains data-dependent",
            "transmission": transmission,
            "drivers": briefing.get("macro_drivers") or macro.get("drivers") or ["Rates", "Growth", "Liquidity"],
        },
        stance=stance,
        confidence={
            "evidence": pick_confidence(0.5 + 0.05 * min(len(evidence), 4), default=0.52),
            "knowledge": coverage,
            "freshness": pick_confidence(leo.get("freshness_score"), default=0.55),
            "coverage": coverage,
        },
        score=float(macro_layer["score"]) if isinstance(macro_layer.get("score"), (int, float)) else None,
        ctx=ctx,
    )
