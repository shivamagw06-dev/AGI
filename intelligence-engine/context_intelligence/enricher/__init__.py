"""CIE enricher — compose all context dimensions + Research Context Card."""

from __future__ import annotations

import time
from typing import Any

from context_intelligence.comparison_context import detect_comparison_context
from context_intelligence.confidence import score_confidence
from context_intelligence.context_card import build_research_context_card
from context_intelligence.diagnostics import diagnose
from context_intelligence.entity_context import detect_entity_context
from context_intelligence.event_context import detect_event_context
from context_intelligence.expectation_context import detect_expectation_context
from context_intelligence.historical_context import detect_historical_context
from context_intelligence.macro_context import detect_macro_context
from context_intelligence.market_context import detect_market_context
from context_intelligence.portfolio_context import detect_portfolio_context
from context_intelligence.routing_context import prioritise_context
from context_intelligence.scenario_context import detect_scenario_context
from context_intelligence.schema import CIE_VERSION, SPRINT
from context_intelligence.time_context import detect_time_context
from context_intelligence.user_context import detect_user_context


def _resolve_priors(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    ere = payload.get("entity_resolution") if isinstance(payload.get("entity_resolution"), dict) else {}
    roe = payload.get("research_objective") if isinstance(payload.get("research_objective"), dict) else {}
    if "research_objective" in roe and isinstance(roe.get("research_objective"), dict):
        roe = roe["research_objective"]
    iar = payload.get("analyst_router") if isinstance(payload.get("analyst_router"), dict) else {}
    if "analyst_router" in iar and isinstance(iar.get("analyst_router"), dict):
        iar = iar["analyst_router"]

    if not roe.get("primary_objective") and not payload.get("primary_objective"):
        try:
            from research_objective.production import plan_question

            plan = plan_question(question, {"skip_ere": True, "entity_resolution": ere or {}})
            roe = {
                "primary_objective": plan.get("primary_objective"),
                "question_type": plan.get("question_type"),
                "decision_type": plan.get("decision_type"),
                "research_depth": plan.get("research_depth"),
                "expected_output": plan.get("expected_output"),
                "objective_confidence": plan.get("objective_confidence"),
            }
        except Exception:
            pass

    if payload.get("primary_objective"):
        roe = {
            **roe,
            "primary_objective": payload.get("primary_objective"),
            "question_type": payload.get("question_type") or roe.get("question_type"),
            "decision_type": payload.get("decision_type") or roe.get("decision_type"),
            "research_depth": payload.get("research_depth") or roe.get("research_depth"),
            "expected_output": payload.get("expected_output") or roe.get("expected_output"),
        }

    if not iar.get("required_analysts") and not payload.get("skip_iar"):
        try:
            from analyst_router.router import route_question

            iar = route_question(
                question,
                {
                    "primary_objective": roe.get("primary_objective"),
                    "question_type": roe.get("question_type"),
                    "research_depth": roe.get("research_depth"),
                },
            )
        except Exception:
            iar = {}

    return {"entity_resolution": ere, "research_objective": roe, "analyst_router": iar}


def enrich_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    body = payload or {}
    priors = _resolve_priors(question, body)
    ere = priors["entity_resolution"]
    roe = priors["research_objective"]
    iar = priors["analyst_router"]
    objective = roe.get("primary_objective")

    entity = detect_entity_context(question, entity_resolution=ere, research_objective=roe)
    time_ctx = detect_time_context(question, primary_objective=objective)
    event_ctx = detect_event_context(question)
    market_ctx = detect_market_context(
        question,
        primary_objective=objective,
        entity_type=entity.get("entity_type"),
        sector=entity.get("sector"),
    )
    macro_ctx = detect_macro_context(question, primary_objective=objective)
    hist_ctx = detect_historical_context(question, primary_objective=objective)
    comparison_ctx = detect_comparison_context(
        question,
        primary_objective=objective,
        peers=entity.get("peers"),
        entity=entity.get("entity"),
    )
    portfolio_ctx = detect_portfolio_context(
        question,
        primary_objective=objective,
        question_type=roe.get("question_type"),
    )
    expectation_ctx = detect_expectation_context(
        question,
        primary_objective=objective,
        entity_type=entity.get("entity_type"),
    )
    scenario_ctx = detect_scenario_context(question, primary_objective=objective)
    user_ctx = detect_user_context(
        question,
        primary_objective=objective,
        question_type=roe.get("question_type"),
        decision_type=roe.get("decision_type"),
        research_depth=roe.get("research_depth"),
    )
    industry_ctx = {
        "industry": entity.get("industry"),
        "sector": entity.get("sector"),
        "confidence": entity.get("confidence"),
        "required": bool(entity.get("industry") or entity.get("sector")),
    }
    geographic_ctx = {
        "geography": "India",
        "currency": "INR",
        "required": True,
        "confidence": 0.95,
    }
    catalyst_ctx = {
        "catalysts": list(event_ctx.get("catalyst_context") or []),
        "required": event_ctx.get("required"),
        "confidence": event_ctx.get("confidence"),
    }

    importance = prioritise_context(
        objective,
        comparison_lenses=comparison_ctx.get("lenses"),
        portfolio_required=bool(portfolio_ctx.get("required")),
        events=event_ctx.get("events"),
    )

    conf = score_confidence(
        {
            "entity_context": entity,
            "time_context": time_ctx,
            "market_context": market_ctx,
            "macro_context": macro_ctx,
            "historical_context": hist_ctx,
            "comparison_context": comparison_ctx,
            "portfolio_context": portfolio_ctx,
            "expectation_context": expectation_ctx,
            "scenario_context": scenario_ctx,
            "event_context": event_ctx,
            "user_context": user_ctx,
        }
    )

    iar_conf = None
    if isinstance(iar.get("routing_confidence"), dict):
        iar_conf = iar["routing_confidence"].get("routing_confidence")
    elif isinstance(roe.get("objective_confidence"), (int, float)):
        iar_conf = float(roe["objective_confidence"])

    card = build_research_context_card(
        question=question,
        primary_objective=objective,
        entity=entity,
        time_ctx=time_ctx,
        user_ctx=user_ctx,
        market_ctx=market_ctx,
        macro_ctx=macro_ctx,
        comparison_ctx=comparison_ctx,
        expectation_ctx=expectation_ctx,
        portfolio_ctx=portfolio_ctx,
        scenario_ctx=scenario_ctx,
        event_ctx=event_ctx,
        importance=importance,
        expected_output=roe.get("expected_output"),
        routing_confidence=iar_conf or conf["overall"],
        iar=iar,
    )

    # Missing / ignored
    missing = []
    if not entity.get("entity"):
        missing.append("entity_context")
    if not comparison_ctx.get("lenses") and objective in {"Peer Comparison", "Historical Analysis"}:
        missing.append("comparison_context")
    ignored = list(card.get("ignore") or [])

    runtime_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    out: dict[str, Any] = {
        "ok": True,
        "cie_version": CIE_VERSION,
        "sprint": SPRINT,
        "question": question,
        "primary_objective": objective,
        "entity_context": entity,
        "market_context": market_ctx,
        "macro_context": macro_ctx,
        "historical_context": hist_ctx,
        "time_context": time_ctx,
        "geographic_context": geographic_ctx,
        "industry_context": industry_ctx,
        "portfolio_context": portfolio_ctx,
        "expectation_context": expectation_ctx,
        "catalyst_context": catalyst_ctx,
        "comparison_context": comparison_ctx,
        "scenario_context": scenario_ctx,
        "event_context": event_ctx,
        "user_context": user_ctx,
        "context_importance": importance.get("context_importance"),
        "priority_order": importance.get("priority_order"),
        "research_context_card": card,
        "confidence": conf,
        "missing_context": missing,
        "ignored_context": ignored,
        "executed_layers": [],
        "executed_analysts": [],
        "runtime_ms": runtime_ms,
        "not_a_top_level_intelligence_layer": True,
    }
    out["diagnostics"] = diagnose(out)
    return out
