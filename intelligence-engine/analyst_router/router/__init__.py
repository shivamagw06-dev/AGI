"""IAR core router — compose objective → participation plan (no execution)."""

from __future__ import annotations

import time
from typing import Any

from analyst_router.assignments import build_assignments
from analyst_router.confidence import score_routing
from analyst_router.dependencies import build_dependencies
from analyst_router.diagnostics import diagnose
from analyst_router.exclusions import build_exclusions
from analyst_router.participation_engine import participate
from analyst_router.schema import IAR_VERSION, SPRINT
from analyst_router.speaking_order import order_speakers
from analyst_router.weighting import assign_weights


def _resolve_objective(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    if payload.get("primary_objective"):
        return {
            "primary_objective": payload.get("primary_objective"),
            "question_type": payload.get("question_type"),
            "research_depth": payload.get("research_depth"),
            "objective_confidence": payload.get("objective_confidence"),
            "source": "prior",
        }
    roe = payload.get("research_objective")
    if isinstance(roe, dict) and (roe.get("primary_objective") or (roe.get("research_objective") or {}).get("primary_objective")):
        body = roe.get("research_objective") if "research_objective" in roe and isinstance(roe.get("research_objective"), dict) else roe
        return {
            "primary_objective": body.get("primary_objective"),
            "question_type": body.get("question_type"),
            "research_depth": body.get("research_depth"),
            "objective_confidence": (body.get("routing_confidence") or {}).get("objective_confidence")
            or body.get("objective_confidence"),
            "source": "research_objective",
        }
    try:
        from research_objective.production import plan_question

        row = plan_question(question, {"skip_ere": True, "entity_resolution": {}})
        return {
            "primary_objective": row.get("primary_objective"),
            "question_type": row.get("question_type"),
            "research_depth": row.get("research_depth"),
            "objective_confidence": row.get("objective_confidence"),
            "source": "roe_live",
        }
    except Exception as exc:  # pragma: no cover
        return {
            "primary_objective": None,
            "source": "fallback",
            "error": str(exc),
        }


def route_question(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    body = payload or {}
    obj = _resolve_objective(question, body)
    part = participate(
        obj.get("primary_objective"),
        question_type=obj.get("question_type"),
        depth=obj.get("research_depth"),
    )
    order = order_speakers(
        part["required_analysts"],
        part.get("optional_analysts"),
        part.get("synthesis_analysts"),
    )
    # Portfolio-style reviews weight optional specialists (Business/Forecast) when present
    include_optional_weights = obj.get("primary_objective") in {
        "Portfolio Decision",
        "Valuation Assessment",
        "Business Quality Assessment",
        "Risk Assessment",
    }
    weights = assign_weights(
        obj.get("primary_objective"),
        part["required_analysts"],
        part.get("optional_analysts"),
        include_optional=include_optional_weights,
    )
    participants = list(order["speaking_order"])
    deps = build_dependencies(participants)
    excl = build_exclusions(
        part["required_analysts"],
        part.get("optional_analysts") or [],
        part.get("suppressed_analysts") or [],
        part.get("synthesis_analysts"),
    )
    assignments = build_assignments(
        [a for a in participants if a in set(part["required_analysts"]) | set(part.get("optional_analysts") or []) | set(part.get("synthesis_analysts") or [])],
        primary_objective=obj.get("primary_objective"),
        question=question,
    )
    routing = score_routing(
        participation_confidence=float(part.get("participation_confidence") or 0.0),
        required=part["required_analysts"],
        speaking_order=order["speaking_order"],
        weights=weights.get("weights") or {},
        objective_confidence=obj.get("objective_confidence"),
    )
    routing_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    out: dict[str, Any] = {
        "ok": True,
        "iar_version": IAR_VERSION,
        "sprint": SPRINT,
        "question": question,
        "primary_objective": obj.get("primary_objective"),
        "question_type": obj.get("question_type"),
        "research_depth": obj.get("research_depth"),
        "objective_source": obj.get("source"),
        "required_analysts": part["required_analysts"],
        "optional_analysts": part.get("optional_analysts") or [],
        "suppressed_analysts": excl["suppressed_analysts"],
        "synthesis_analysts": part.get("synthesis_analysts") or [],
        "speaking_order": order["speaking_order"],
        "speaking_order_detailed": order["speaking_order_detailed"],
        "weights": weights.get("weights") or {},
        "optional_weights": weights.get("optional_weights") or {},
        "dependencies": deps.get("dependencies") or {},
        "dependency_edges": deps.get("dependency_edges") or [],
        "assignments": assignments,
        "exclusions": {
            "no_placeholders": True,
            "no_empty_sections": True,
            "execution_policy": excl.get("execution_policy"),
            "unavailable_policy": excl.get("unavailable_policy"),
            "mandate_walls": excl.get("mandate_walls"),
        },
        "routing_confidence": routing,
        "requires_clarification": not routing.get("passes_threshold"),
        "executed_analysts": [],
        "routing_ms": routing_ms,
        "not_a_top_level_intelligence_layer": True,
    }
    out["diagnostics"] = diagnose(out)
    return out
