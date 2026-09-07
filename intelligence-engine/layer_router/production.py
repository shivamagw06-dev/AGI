"""ILR V1 production facade — RQ1 Sprint 6."""

from __future__ import annotations

from typing import Any

from layer_router.flags import flags_dict, is_enabled
from layer_router.planner import plan_pipeline
from layer_router.registry import all_layers, registry_stats
from layer_router.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    ILR_VERSION,
    MAX_PLANNING_MS_TARGET,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "q": "Should I buy HDFC Bank?",
        "objective": "Investment Evaluation",
        "required_contains": ["FIL", "EIL", "PIL", "Business", "Financial", "Valuation", "Committee", "Portfolio", "IDE V2", "CIO"],
        "suppressed_contains": ["Ownership", "SSL"],
        "order_has_edge": [("FIL", "EIL"), ("Business", "Committee"), ("IDE V2", "CIO")],
        "parallel_min_levels": 2,
        "contrib_fil": True,
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "objective": "Historical Analysis",
        "required_contains": ["PIL", "Valuation", "Sector", "Macro"],
        "suppressed_contains": ["Business", "Portfolio", "Management"],
    },
    {
        "q": "Compare TCS vs Infosys",
        "objective": "Peer Comparison",
        "required_contains": ["PIL", "Business", "Financial", "Valuation", "Sector"],
        "suppressed_contains": ["Portfolio", "SSL"],
    },
    {
        "q": "Explain ROIC",
        "objective": "Educational",
        "required_exact": ["ILM", "Research Writer"],
        "suppressed_contains": ["SSL", "Committee", "Portfolio"],
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "objective": "Macro Impact",
        "required_contains": ["Macro", "CIG", "Sector", "FIE"],
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "objective": "Portfolio Decision",
        "required_contains": ["Portfolio", "SSL", "Risk", "IDE V2"],
    },
    {
        "q": "What are the risks in Reliance Industries?",
        "objective": "Risk Assessment",
        "required_contains": ["Risk", "SSL", "EIL"],
    },
    {
        "q": "Is Infosys overvalued on PE?",
        "objective": "Valuation Assessment",
        "required_contains": ["Valuation", "PIL", "Financial"],
    },
]

_TEMPLATES: list[tuple[str, str, dict[str, Any]]] = [
    ("Should I buy {name}?", "Investment Evaluation", {"required_contains": ["FIL", "Business", "Valuation"]}),
    ("Should I sell {name}?", "Investment Evaluation", {"required_contains": ["Risk", "Committee"]}),
    ("Compare {name} vs {peer}", "Peer Comparison", {"required_contains": ["PIL", "Sector"]}),
    ("Explain {concept}", "Educational", {"required_exact": ["ILM", "Research Writer"]}),
    ("Is {index} expensive versus history?", "Historical Analysis", {"required_contains": ["PIL", "Valuation"], "suppressed_contains": ["Portfolio"]}),
    ("How will RBI rate cuts affect {sector}?", "Macro Impact", {"required_contains": ["Macro", "CIG"]}),
    ("Build a portfolio with {name}", "Portfolio Decision", {"required_contains": ["Portfolio", "SSL"]}),
    ("What are the risks in {name}?", "Risk Assessment", {"required_contains": ["Risk"]}),
    ("Is {name} overvalued?", "Valuation Assessment", {"required_contains": ["Valuation", "PIL"]}),
    ("Assess business quality of {name}", "Business Quality Assessment", {"required_contains": ["Business", "MII"]}),
    ("Forecast earnings for {name}", "Forecast", {"required_contains": ["FIE"]}),
    ("Screen for quality {sector} stocks", "Screening", {"required_contains": ["PIL", "FIL"]}),
    ("News impact on {name}", "News Impact", {"required_contains": ["EIL", "Risk"]}),
    ("Bull and bear case for {name}", "Scenario Analysis", {"required_contains": ["SSL", "FIE"]}),
]

_NAMES = ["HDFC Bank", "Infosys", "TCS", "Reliance", "SBI", "ICICI Bank", "Wipro", "Titan", "ITC", "Axis Bank"]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech"]
_SECTORS = ["banks", "IT", "auto", "pharma", "FMCG"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "WACC"]


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": ILR_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_planning_ms_target": MAX_PLANNING_MS_TARGET,
        "registry": registry_stats(),
        "not_a_top_level_intelligence_layer": True,
        "law": "No intelligence layer runs automatically.",
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "layers": all_layers()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "ilr_version": ILR_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "ilr_version": ILR_VERSION}
    return {"enabled": True, **plan_pipeline(question, body)}


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:8]:
        row = plan_pipeline(b["q"], {"primary_objective": b.get("objective"), "skip_iar": True})
        samples.append(
            {
                "question": b["q"],
                "primary_objective": row.get("primary_objective"),
                "required_layers": row.get("required_layers"),
                "optional_layers": row.get("optional_layers"),
                "suppressed_layers": row.get("suppressed_layers"),
                "execution_order": (row.get("execution_graph") or {}).get("order"),
                "parallel_groups": row.get("parallel_groups"),
                "estimated_runtime": row.get("estimated_runtime"),
                "runtime_reduction": row.get("runtime_reduction"),
                "planning_ms": row.get("planning_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "ilr_version": ILR_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "registry": registry_stats(),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/layer-router"],
        "api_prefix": "/v1/layer-router",
        "law": "Every execution path is explainable, reproducible, and dynamically optimised.",
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return plan_pipeline(q, body).get("diagnostics") or {}


def _expanded() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    i = 0
    while len(cases) < 1100:
        tmpl, objective, extra = _TEMPLATES[i % len(_TEMPLATES)]
        name = _NAMES[i % len(_NAMES)]
        peer = _PEERS[i % len(_PEERS)]
        if peer == name:
            peer = _PEERS[(i + 1) % len(_PEERS)]
        q = tmpl.format(
            name=name,
            peer=peer,
            sector=_SECTORS[i % len(_SECTORS)],
            index=_INDEXES[i % len(_INDEXES)],
            concept=_CONCEPTS[i % len(_CONCEPTS)],
        )
        cases.append({"q": q, "objective": objective, **extra, "kind": "template"})
        i += 1
    return cases


def _check(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    req = set(row.get("required_layers") or [])
    sup = set(row.get("suppressed_layers") or [])
    if b.get("required_contains") and not set(b["required_contains"]).issubset(req):
        errs.append("required_contains")
    if b.get("required_exact") is not None and set(row.get("required_layers") or []) != set(b["required_exact"]):
        errs.append("required_exact")
    if b.get("suppressed_contains") and not set(b["suppressed_contains"]).issubset(sup):
        errs.append("suppressed_contains")
    if b.get("order_has_edge"):
        edges = {(e["from"], e["to"]) for e in (row.get("dependency_edges") or [])}
        for a, c in b["order_has_edge"]:
            if (a, c) not in edges:
                # allow transitive: a before c in order
                order = list((row.get("execution_graph") or {}).get("order") or [])
                if a not in order or c not in order or order.index(a) > order.index(c):
                    errs.append(f"edge_{a}_{c}")
    if b.get("parallel_min_levels"):
        if len(row.get("parallel_groups") or []) < int(b["parallel_min_levels"]):
            errs.append("parallel")
    if b.get("contrib_fil"):
        by = row.get("expected_contribution_by_layer") or {}
        if "FIL" not in by or float(by["FIL"]) <= 0:
            errs.append("contrib")
    if req & sup:
        errs.append("overlap")
    if row.get("executed_layers"):
        errs.append("executed")
    # Dependency accuracy: deps of required ⊆ participants
    participants = req | set(row.get("optional_layers") or [])
    for layer, needs in (row.get("dependencies") or {}).items():
        if layer not in participants:
            continue
        for n in needs or []:
            if n not in participants:
                errs.append("dep")
                break
    return errs


def quality_gates() -> dict[str, Any]:
    cases = _expanded()
    passed = 0
    route_ok = dep_ok = par_ok = sup_ok = 0
    timed: list[float] = []
    reductions: list[float] = []
    failures: list[dict[str, Any]] = []

    for b in cases[:1100]:
        payload = {"primary_objective": b.get("objective"), "skip_iar": True}
        row = plan_pipeline(b["q"], payload)
        timed.append(float(row.get("planning_ms") or 0))
        reductions.append(float(row.get("runtime_reduction") or 0))
        errs = _check(b, row)

        if "required_contains" not in errs and "required_exact" not in errs:
            route_ok += 1
        if "dep" not in errs:
            dep_ok += 1
        if "parallel" not in errs and row.get("parallel_groups"):
            par_ok += 1
        if "suppressed_contains" not in errs:
            sup_ok += 1

        if not errs:
            passed += 1
        elif len(failures) < 25:
            failures.append(
                {
                    "question": b["q"],
                    "errors": errs,
                    "required": row.get("required_layers"),
                    "suppressed": row.get("suppressed_layers"),
                }
            )

    total = min(len(cases), 1100)
    avg_ms = round(sum(timed) / len(timed), 3) if timed else 0.0
    avg_red = round(sum(reductions) / len(reductions), 4) if reductions else 0.0
    return {
        "ok": (
            route_ok / total >= 0.99
            and dep_ok / total >= 1.0
            and par_ok / total >= 0.95
            and sup_ok / total >= 0.98
            and avg_ms <= MAX_PLANNING_MS_TARGET * 5
            and avg_red >= 0.25
            and total >= 1000
        ),
        "passed": passed,
        "total": total,
        "pass_rate": round(passed / total, 4) if total else 0.0,
        "layer_routing_accuracy": round(route_ok / total, 4) if total else 0.0,
        "dependency_accuracy": round(dep_ok / total, 4) if total else 0.0,
        "parallel_execution_accuracy": round(par_ok / total, 4) if total else 0.0,
        "suppressed_layer_accuracy": round(sup_ok / total, 4) if total else 0.0,
        "avg_planning_ms": avg_ms,
        "avg_runtime_reduction": avg_red,
        "p95_planning_ms": round(sorted(timed)[int(0.95 * (len(timed) - 1))], 3) if timed else 0.0,
        "target_planning_ms": MAX_PLANNING_MS_TARGET,
        "failures_sample": failures,
        "rule": "No irrelevant intelligence layers execute.",
    }


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    row = plan_pipeline(question or "", payload)
    return {
        "layer_router": {
            "enabled": True,
            "version": ILR_VERSION,
            "sprint": SPRINT,
            "primary_objective": row.get("primary_objective"),
            "required_layers": row.get("required_layers"),
            "optional_layers": row.get("optional_layers"),
            "suppressed_layers": row.get("suppressed_layers"),
            "execution_graph": row.get("execution_graph"),
            "parallel_groups": row.get("parallel_groups"),
            "estimated_runtime": row.get("estimated_runtime"),
            "runtime_reduction": row.get("runtime_reduction"),
            "expected_cost": row.get("expected_cost"),
            "confidence_plan": row.get("confidence_plan"),
            "expected_contributions": row.get("expected_contributions"),
            "planning_ms": row.get("planning_ms"),
            "no_layer_execution": True,
        }
    }
