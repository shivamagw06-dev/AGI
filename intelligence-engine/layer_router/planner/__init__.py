"""ILR planner — compose objective/analysts into an execution plan (no execution)."""

from __future__ import annotations

import time
from typing import Any

from layer_router.confidence import build_confidence_plan
from layer_router.contribution import expected_contributions
from layer_router.cost_engine import estimate_cost
from layer_router.dependency_engine import build_dependencies
from layer_router.diagnostics import diagnose
from layer_router.execution_graph import build_execution_graph
from layer_router.parallel_engine import build_parallel_groups
from layer_router.priority_engine import score_importance
from layer_router.schema import ILR_VERSION, SPRINT
from layer_router.suppression_engine import suppress_layers

# Canonical required stacks by objective (institutional minimum)
_REQUIRED_STACKS: dict[str, list[str]] = {
    "Investment Evaluation": [
        "FIL",
        "FDI",
        "ACI",
        "EIL",
        "PIL",
        "CIG",
        "IKG",
        "FIE",
        "ILM",
        "Business",
        "Financial",
        "Valuation",
        "Risk",
        "Committee",
        "Portfolio",
        "IDE V2",
        "CIO",
        "Research Writer",
    ],
    "Historical Analysis": [
        "FIL",
        "EIL",
        "PIL",
        "CIG",
        "FIE",
        "Valuation",
        "Sector",
        "Macro",
        "Research Writer",
    ],
    "Peer Comparison": [
        "FIL",
        "EIL",
        "PIL",
        "Business",
        "Financial",
        "Valuation",
        "Sector",
        "Research Writer",
    ],
    "Educational": ["Research Writer", "ILM"],
    "Macro Impact": [
        "FIL",
        "EIL",
        "CIG",
        "Macro",
        "Sector",
        "FIE",
        "Risk",
        "Research Writer",
    ],
    "Portfolio Decision": [
        "FIL",
        "EIL",
        "PIL",
        "FIE",
        "Risk",
        "Valuation",
        "Portfolio",
        "SSL",
        "Committee",
        "IDE V2",
        "CIO",
        "Research Writer",
    ],
    "Risk Assessment": [
        "FIL",
        "EIL",
        "ACI",
        "FIE",
        "Macro",
        "Risk",
        "SSL",
        "Research Writer",
    ],
    "Valuation Assessment": [
        "FIL",
        "EIL",
        "PIL",
        "FIE",
        "Financial",
        "Valuation",
        "Research Writer",
    ],
    "Business Quality Assessment": [
        "FIL",
        "EIL",
        "MII",
        "Business",
        "Management",
        "Research Writer",
    ],
    "Screening": ["FIL", "EIL", "PIL", "Financial", "Valuation", "Research Writer"],
    "Forecast": ["FIL", "EIL", "CIG", "FIE", "Macro", "Financial", "Research Writer"],
    "News Impact": ["EIL", "FIE", "Risk", "Research Writer"],
    "Scenario Analysis": ["FIL", "EIL", "FIE", "Macro", "Risk", "SSL", "Committee", "Research Writer"],
}


def _resolve_priors(question: str, payload: dict[str, Any]) -> dict[str, Any]:
    roe = payload.get("research_objective") if isinstance(payload.get("research_objective"), dict) else {}
    if "research_objective" in roe and isinstance(roe.get("research_objective"), dict):
        roe = roe["research_objective"]
    iar = payload.get("analyst_router") if isinstance(payload.get("analyst_router"), dict) else {}
    if "analyst_router" in iar and isinstance(iar.get("analyst_router"), dict):
        iar = iar["analyst_router"]

    objective = payload.get("primary_objective") or roe.get("primary_objective")
    if not objective:
        try:
            from research_objective.production import plan_question

            plan = plan_question(question, {"skip_ere": True, "entity_resolution": {}})
            objective = plan.get("primary_objective")
            roe = {
                "primary_objective": objective,
                "question_type": plan.get("question_type"),
                "research_depth": plan.get("research_depth"),
            }
        except Exception:
            objective = "Investment Evaluation"

    required_analysts = list(payload.get("required_analysts") or iar.get("required_analysts") or [])
    if not required_analysts and not payload.get("skip_iar"):
        try:
            from analyst_router.router import route_question

            iar = route_question(
                question,
                {
                    "primary_objective": objective,
                    "question_type": roe.get("question_type"),
                    "research_depth": roe.get("research_depth"),
                },
            )
            required_analysts = list(iar.get("required_analysts") or [])
        except Exception:
            pass

    return {
        "primary_objective": objective,
        "question_type": roe.get("question_type") or payload.get("question_type"),
        "required_analysts": required_analysts,
        "roe": roe,
        "iar": iar,
    }


def plan_pipeline(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    body = payload or {}
    priors = _resolve_priors(question, body)
    objective = priors["primary_objective"]

    force_required = list(_REQUIRED_STACKS.get(objective or "", ["FIL", "EIL", "Research Writer"]))
    # Merge IAR analysts that are registered layers
    for a in priors["required_analysts"]:
        if a not in force_required and a in {
            "Business",
            "Financial",
            "Valuation",
            "Risk",
            "Sector",
            "Macro",
            "Management",
            "Ownership",
            "Portfolio",
            "Committee",
        }:
            # Insert before Committee/synthesis if present
            if "Committee" in force_required:
                idx = force_required.index("Committee")
                force_required.insert(idx, a)
            else:
                force_required.append(a)

    # Educational: minimal
    if objective == "Educational":
        force_required = ["ILM", "Research Writer"]

    importance = score_importance(objective, required_analysts=priors["required_analysts"])
    # Optional: Macro for investment evaluation (sprint example importance 55 → optional zone)
    force_optional: list[str] = []
    if objective == "Investment Evaluation":
        force_optional = ["Macro"]
    if objective == "Historical Analysis":
        force_optional = ["ILM", "IKG"]

    suppressed_plan = suppress_layers(
        importance["importance"],
        force_required=force_required,
        force_optional=force_optional,
    )
    required = suppressed_plan["required_layers"]
    optional = suppressed_plan["optional_layers"]
    suppressed = suppressed_plan["suppressed_layers"]

    participants = list(required) + [x for x in optional if x not in required]
    deps = build_dependencies(participants)
    modes = {r: "Required" for r in required}
    modes.update({o: "Optional" for o in optional})
    graph = build_execution_graph(
        participants,
        deps["dependency_edges"],
        modes=modes,
        importance=importance["importance"],
    )
    parallel = build_parallel_groups(graph["execution_order"], deps["dependency_edges"])
    cost = estimate_cost(required, optional, parallel["parallel_groups"])
    contrib = expected_contributions(
        required,
        optional,
        suppressed,
        importance["importance"],
        primary_objective=objective,
    )
    conf = build_confidence_plan(
        required,
        suppressed,
        expected_contributions=contrib["expected_contribution_by_layer"],
    )

    planning_ms = round((time.perf_counter() - t0) * 1000.0, 3)
    out: dict[str, Any] = {
        "ok": True,
        "ilr_version": ILR_VERSION,
        "sprint": SPRINT,
        "question": question,
        "primary_objective": objective,
        "question_type": priors.get("question_type"),
        "required_layers": required,
        "optional_layers": optional,
        "suppressed_layers": suppressed,
        "execution_graph": {
            "order": graph["execution_order"],
            "nodes": graph["nodes"],
            "edges": graph["edges"],
        },
        "parallel_groups": parallel["parallel_groups"],
        "dependencies": deps["dependencies"],
        "dependency_edges": deps["dependency_edges"],
        "importance": importance["importance"],
        "estimated_runtime": cost["estimated_runtime_ms"],
        "serial_runtime_ms": cost["serial_runtime_ms"],
        "runtime_reduction": cost["runtime_reduction"],
        "expected_cost": cost["expected_cost"],
        "confidence_plan": conf["confidence_plan"],
        "expected_contributions": contrib["expected_contributions"],
        "expected_contribution_by_layer": contrib["expected_contribution_by_layer"],
        "learning_hook": contrib["learning_hook"],
        "executed_layers": [],
        "planning_ms": planning_ms,
        "not_a_top_level_intelligence_layer": True,
        "no_automatic_execution": True,
    }
    out["diagnostics"] = diagnose(out)
    return out
