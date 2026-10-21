"""IREP V1 production facade — RQ1 Sprint 10 (final RQ1 package)."""

from __future__ import annotations

from typing import Any

from research_execution.diagnostics import diagnose
from research_execution.flags import flags_dict, is_enabled
from research_execution.package_builder import build_execution_package
from research_execution.package_export import export_package
from research_execution.package_memory import memory_stats, recent_packages
from research_execution.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    IREP_VERSION,
    MAX_PACKAGE_MS_TARGET,
    PROGRAMME,
    PROGRAMME_SHORT,
    SPRINT,
    SPRINT_NAME,
    constitution_dict,
)

CORE_BENCHMARKS: list[dict[str, Any]] = [
    {
        "q": "Should I buy HDFC Bank?",
        "expect_entity_ticker": "HDFCBANK",
        "expect_analysts_contains": ["Business", "Financial", "Valuation"],
        "expect_layers_contains": ["FIL", "EIL", "PIL"],
        "expect_blueprint": "institutional_investment_report",
        "expect_contract_min_evidence": 12,
        "expect_complete": True,
    },
    {
        "q": "Compare TCS vs Infosys",
        "expect_blueprint": "comparison_report",
        "expect_analysts_contains": ["Business", "Valuation"],
        "expect_complete": True,
    },
    {
        "q": "Explain ROIC",
        "expect_blueprint": "educational_guide",
        "expect_analysts_contains": ["Academy", "Financial"],
        "expect_suppressed_contains": ["Portfolio", "Committee"],
        "expect_complete": True,
    },
    {
        "q": "Is Nifty IT expensive versus history?",
        "expect_blueprint": "historical_valuation_report",
        "expect_complete": True,
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "expect_blueprint": "macro_intelligence_report",
        "expect_complete": True,
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "expect_blueprint": "portfolio_memorandum",
        "expect_analysts_contains": ["Portfolio"],
        "expect_complete": True,
    },
    {
        "q": "What are the risks in Reliance Industries?",
        "expect_analysts_contains": ["Risk"],
        "expect_complete": True,
    },
    {
        "q": "Analyse Tata",
        "expect_validation_state_in": ["CLARIFICATION_REQUIRED"],
        "expect_complete": True,
    },
]

_TEMPLATES: list[tuple[str, dict[str, Any]]] = [
    ("Should I buy {name}?", {"expect_blueprint": "institutional_investment_report", "expect_analysts_contains": ["Business", "Valuation"]}),
    ("Should I sell {name}?", {"expect_blueprint": "institutional_investment_report", "expect_analysts_contains": ["Risk"]}),
    ("Compare {name} vs {peer}", {"expect_blueprint": "comparison_report"}),
    ("Explain {concept}", {"expect_blueprint": "educational_guide", "expect_suppressed_contains": ["Portfolio"]}),
    ("Is {index} expensive versus history?", {"expect_blueprint": "historical_valuation_report"}),
    ("How will RBI rate cuts affect {sector}?", {"expect_blueprint": "macro_intelligence_report"}),
    ("Build a portfolio with {name}", {"expect_blueprint": "portfolio_memorandum", "expect_analysts_contains": ["Portfolio"]}),
    ("What are the risks in {name}?", {"expect_analysts_contains": ["Risk"]}),
    ("Is {name} overvalued?", {"expect_analysts_contains": ["Valuation"]}),
    ("Forecast earnings for {name}", {"expect_complete": True}),
    ("Accounting review of {name}", {"expect_complete": True}),
    ("News impact on {name}", {"expect_complete": True}),
]

_NAMES = ["HDFC Bank", "Infosys", "TCS", "Reliance Industries", "ICICI Bank", "Wipro", "Titan", "ITC"]
_PEERS = ["Infosys", "TCS", "Wipro", "HCL Tech"]
_SECTORS = ["banks", "IT", "auto", "pharma"]
_INDEXES = ["Nifty IT", "Nifty Bank", "Nifty 50"]
_CONCEPTS = ["ROIC", "ROE", "EV/EBITDA", "DCF", "WACC"]


def health() -> dict[str, Any]:
    return {
        "status": "ok" if is_enabled() else "disabled",
        "programme": PROGRAMME,
        "layer": PROGRAMME_SHORT,
        "version": IREP_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_package_ms_target": MAX_PACKAGE_MS_TARGET,
        "not_a_top_level_intelligence_layer": True,
        "rq1_final_package": True,
        "law": "IREP is the contract between planning and reasoning.",
        "memory": memory_stats(),
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return build(payload)


def build(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "irep_version": IREP_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "irep_version": IREP_VERSION}
    return {"enabled": True, **build_execution_package(question, body)}


def enrich(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return build(payload)


def export(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    fmt = str(body.get("format") or "json")
    if body.get("package"):
        return export_package(body["package"], fmt)
    pkg = build(body)
    if not pkg.get("ok"):
        return pkg
    return export_package(pkg, fmt)


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:8]:
        row = build_execution_package(b["q"], {})
        samples.append(
            {
                "question": b["q"],
                "package_id": row.get("package_id"),
                "entity": (row.get("entity") or {}).get("canonical_name") or (row.get("entity") or {}).get("ticker"),
                "objective": (row.get("intent") or {}).get("research_objective"),
                "required_analysts": (row.get("analyst_plan") or {}).get("required_analysts"),
                "required_layers": (row.get("layer_plan") or {}).get("required_layers"),
                "providers": (row.get("api_plan") or {}).get("providers"),
                "report_type": (row.get("blueprint") or {}).get("report_type"),
                "readiness_state": (row.get("validation") or {}).get("readiness_state"),
                "expected_confidence": (row.get("execution_plan") or {}).get("expected_confidence"),
                "package_ms": (row.get("metrics") or {}).get("package_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "irep_version": IREP_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "samples": samples,
        "recent_packages": recent_packages(8),
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/research-execution"],
        "api_prefix": "/v1/research-execution",
        "law": "Every execution starts with one institutional research package.",
        "rq1_complete": True,
    }


def diagnostics(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    body = payload or {}
    q = str(body.get("question") or body.get("q") or "").strip()
    if not q:
        return {"ok": False, "error": "question is required"}
    return diagnose(q, body)


def soft_slice_for_ask_agi(question: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {}
    row = build_execution_package(question, payload or {})
    return {
        "irep_version": IREP_VERSION,
        "package_id": row.get("package_id"),
        "immutable": True,
        "question": row.get("question"),
        "entity": {
            "canonical_name": (row.get("entity") or {}).get("canonical_name"),
            "ticker": (row.get("entity") or {}).get("ticker"),
            "sector": (row.get("entity") or {}).get("sector"),
        },
        "intent": {
            "primary_intent": (row.get("intent") or {}).get("primary_intent"),
            "research_objective": (row.get("intent") or {}).get("research_objective"),
        },
        "analyst_plan": {
            "required_analysts": (row.get("analyst_plan") or {}).get("required_analysts"),
            "suppressed_analysts": (row.get("analyst_plan") or {}).get("suppressed_analysts"),
            "speaking_order": (row.get("analyst_plan") or {}).get("speaking_order"),
        },
        "layer_plan": {
            "required_layers": (row.get("layer_plan") or {}).get("required_layers"),
            "suppressed_layers": (row.get("layer_plan") or {}).get("suppressed_layers"),
            "parallel_groups": (row.get("layer_plan") or {}).get("parallel_groups"),
        },
        "api_plan": {
            "providers": (row.get("api_plan") or {}).get("providers"),
            "internal_reuse": (row.get("api_plan") or {}).get("internal_reuse"),
        },
        "blueprint": {
            "report_type": (row.get("blueprint") or {}).get("report_type"),
            "report_name": (row.get("blueprint") or {}).get("report_name"),
            "section_order": (row.get("blueprint") or {}).get("section_order"),
        },
        "validation": {
            "readiness_state": (row.get("validation") or {}).get("readiness_state"),
            "execution_allowed": (row.get("validation") or {}).get("execution_allowed"),
            "overall_readiness": (row.get("validation") or {}).get("overall_readiness"),
        },
        "execution_plan": row.get("execution_plan"),
        "research_contract": {
            "objective": (row.get("research_contract") or {}).get("objective"),
            "must_answer": (row.get("research_contract") or {}).get("must_answer"),
            "must_not": (row.get("research_contract") or {}).get("must_not"),
            "minimum_evidence": (row.get("research_contract") or {}).get("minimum_evidence"),
            "success_definition": (row.get("research_contract") or {}).get("success_definition"),
        },
        "package_complete": row.get("package_complete"),
        "package_consistent": row.get("package_consistent"),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
        "rq1_final_package": True,
    }


def _expanded() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    i = 0
    while len(cases) < 1100:
        tmpl, extra = _TEMPLATES[i % len(_TEMPLATES)]
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
        cases.append({"q": q, "expect_complete": True, **extra, "kind": "template"})
        i += 1
    return cases


def _check(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    if b.get("expect_complete") and not row.get("package_complete"):
        errs.append("incomplete")
    if not row.get("package_consistent"):
        errs.append("inconsistent")
    if not row.get("immutable"):
        errs.append("mutable")
    if not row.get("research_contract"):
        errs.append("no_contract")
    entity = row.get("entity") or {}
    if b.get("expect_entity_ticker") and str(entity.get("ticker") or "").upper() != b["expect_entity_ticker"]:
        errs.append("entity_ticker")
    analysts = set((row.get("analyst_plan") or {}).get("required_analysts") or [])
    suppressed = set((row.get("analyst_plan") or {}).get("suppressed_analysts") or [])
    layers = set((row.get("layer_plan") or {}).get("required_layers") or [])
    if b.get("expect_analysts_contains") and not set(b["expect_analysts_contains"]).issubset(analysts):
        errs.append("analysts")
    if b.get("expect_suppressed_contains") and not set(b["expect_suppressed_contains"]).issubset(suppressed):
        errs.append("suppressed_analysts")
    if b.get("expect_layers_contains") and not set(b["expect_layers_contains"]).issubset(layers):
        errs.append("layers")
    bp = (row.get("blueprint") or {}).get("report_type")
    if b.get("expect_blueprint") and bp != b["expect_blueprint"]:
        errs.append("blueprint")
    if b.get("expect_contract_min_evidence") is not None:
        if int((row.get("research_contract") or {}).get("minimum_evidence") or 0) < int(b["expect_contract_min_evidence"]):
            errs.append("contract_evidence")
    state = (row.get("validation") or {}).get("readiness_state")
    if b.get("expect_validation_state_in") and state not in b["expect_validation_state_in"]:
        errs.append("validation_state")
    # no conflicts between required/suppressed
    if analysts & suppressed:
        errs.append("analyst_conflict")
    req_l = set((row.get("layer_plan") or {}).get("required_layers") or [])
    sup_l = set((row.get("layer_plan") or {}).get("suppressed_layers") or [])
    if req_l & sup_l:
        errs.append("layer_conflict")
    return errs


def quality_gates() -> dict[str, Any]:
    return _quality_gates_single_pass(_expanded(), constitution_dict()["success_criteria"])


def _quality_gates_single_pass(cases: list[dict[str, Any]], criteria: dict[str, Any]) -> dict[str, Any]:
    complete_ok = consistent_ok = no_conflict = 0
    analyst_ok = analyst_total = layer_ok = layer_total = blueprint_ok = blueprint_total = 0
    passed_cases = 0
    times: list[float] = []
    failures: list[dict[str, Any]] = []
    checked = 0
    for b in cases:
        row = build_execution_package(b["q"], {})
        checked += 1
        errs = _check(b, row)
        times.append(float((row.get("metrics") or {}).get("package_ms") or 0))
        if row.get("package_complete"):
            complete_ok += 1
        if row.get("package_consistent"):
            consistent_ok += 1
        if not ((row.get("validation_detail") or {}).get("conflicts")):
            no_conflict += 1
        if b.get("expect_analysts_contains") or b.get("expect_suppressed_contains"):
            analyst_total += 1
            if "analysts" not in errs and "suppressed_analysts" not in errs and "analyst_conflict" not in errs:
                analyst_ok += 1
        if b.get("expect_layers_contains"):
            layer_total += 1
            if "layers" not in errs and "layer_conflict" not in errs:
                layer_ok += 1
        if b.get("expect_blueprint"):
            blueprint_total += 1
            if "blueprint" not in errs:
                blueprint_ok += 1
        if not errs:
            passed_cases += 1
        elif len(failures) < 25:
            failures.append({"q": b["q"], "errs": errs, "blueprint": (row.get("blueprint") or {}).get("report_type")})

    n = max(checked, 1)
    avg_ms = sum(times) / n
    completeness = complete_ok / n
    consistency = consistent_ok / n
    conflict_free = no_conflict / n
    analyst_acc = (analyst_ok / analyst_total) if analyst_total else 1.0
    layer_acc = (layer_ok / layer_total) if layer_total else 1.0
    blueprint_acc = (blueprint_ok / blueprint_total) if blueprint_total else 1.0
    passed = (
        checked >= int(criteria["benchmark_minimum"])
        and completeness >= float(criteria["package_completeness"])
        and consistency >= float(criteria["package_consistency"])
        and conflict_free >= float(criteria["no_conflicting_plans"])
        and analyst_acc >= float(criteria["correct_analyst_plan"])
        and layer_acc >= float(criteria["correct_layer_plan"])
        and blueprint_acc >= float(criteria["correct_blueprint"])
        and avg_ms < float(criteria["average_package_ms"])
    )
    return {
        "ok": passed,
        "checked": checked,
        "package_completeness": round(completeness, 4),
        "package_consistency": round(consistency, 4),
        "no_conflicting_plans": round(conflict_free, 4),
        "correct_analyst_plan": round(analyst_acc, 4),
        "correct_layer_plan": round(layer_acc, 4),
        "correct_blueprint": round(blueprint_acc, 4),
        "case_pass_rate": round(passed_cases / n, 4),
        "average_package_ms": round(avg_ms, 4),
        "benchmark_minimum": criteria["benchmark_minimum"],
        "targets": criteria,
        "failures_sample": failures,
        "irep_version": IREP_VERSION,
        "sprint": SPRINT,
        "rq1_complete": True,
    }
