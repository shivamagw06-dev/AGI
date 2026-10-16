"""IAPE V1 production facade — RQ1 Sprint 7."""

from __future__ import annotations

from typing import Any

from acquisition_planner.acquisition_plan import build_acquisition_plan
from acquisition_planner.api_registry import PROVIDERS, all_providers, registry_stats
from acquisition_planner.diagnostics import diagnose
from acquisition_planner.flags import flags_dict, is_enabled
from acquisition_planner.schema import (
    ARCHITECTURE_STATUS,
    CONFIDENCE_THRESHOLD,
    IAPE_VERSION,
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
        "objective": "decision_support",
        "family": "company",
        "expect_evidence_contains": ["official_filings", "peer_metrics", "historical_valuation"],
        "expect_reuse_min": 1,
        "primary_in": {"historical_valuation": ["groww", "indianapi", "yahoo_finance", "fmp"]},
        "annual_report_primary_in": ["company_ir", "nse", "bse", "fil"],
    },
    {
        "q": "Is Infosys overvalued on PE?",
        "objective": "valuation_assessment",
        "expect_evidence_contains": ["historical_valuation", "peer_metrics"],
        "primary_in": {"historical_valuation": ["groww", "indianapi", "yahoo_finance", "fmp", "pil"]},
    },
    {
        "q": "Compare TCS vs Infosys",
        "objective": "comparison_assessment",
        "expect_evidence_contains": ["peer_metrics"],
        "expect_reuse_min": 1,
    },
    {
        "q": "Explain ROIC",
        "objective": "educational_explanation",
        "family": "educational",
        "expect_evidence_contains": ["knowledge_graph_context", "evidence_corpus"],
        "max_api_calls": 2,
        "expect_reuse_min": 1,
    },
    {
        "q": "How will RBI rate cuts affect banks?",
        "objective": "forecast_assessment",
        "family": "macro",
        "expect_evidence_contains": ["macro_data"],
        "primary_in": {"macro_data": ["fred", "rbi", "world_bank", "imf"]},
    },
    {
        "q": "Build a ₹500,000 portfolio",
        "objective": "portfolio_assessment",
        "family": "portfolio",
        "expect_evidence_contains": ["portfolio_exposure"],
    },
    {
        "q": "What is today's price of Reliance?",
        "objective": "fact_retrieval",
        "expect_evidence_contains": ["live_prices"],
        "primary_in": {"live_prices": ["groww", "indianapi", "yahoo_finance", "polygon", "finnhub"]},
    },
    {
        "q": "What are the risks in HDFC Bank?",
        "objective": "risk_assessment",
        "expect_evidence_contains": ["official_filings", "macro_data"],
    },
]

_TEMPLATES: list[tuple[str, str, str, dict[str, Any]]] = [
    ("Should I buy {name}?", "decision_support", "company", {"expect_evidence_contains": ["official_filings", "historical_valuation"]}),
    ("Should I sell {name}?", "decision_support", "company", {"expect_evidence_contains": ["official_filings"]}),
    ("Compare {name} vs {peer}", "comparison_assessment", "company", {"expect_evidence_contains": ["peer_metrics"]}),
    ("Explain {concept}", "educational_explanation", "educational", {"expect_evidence_contains": ["knowledge_graph_context"], "expect_reuse_min": 1}),
    ("Is {index} expensive versus history?", "valuation_assessment", "sector", {"expect_evidence_contains": ["historical_valuation"]}),
    ("How will RBI rate cuts affect {sector}?", "forecast_assessment", "macro", {"expect_evidence_contains": ["macro_data"]}),
    ("Build a portfolio with {name}", "portfolio_assessment", "portfolio", {"expect_evidence_contains": ["portfolio_exposure"]}),
    ("What are the risks in {name}?", "risk_assessment", "company", {"expect_evidence_contains": ["official_filings"]}),
    ("Is {name} overvalued?", "valuation_assessment", "company", {"expect_evidence_contains": ["historical_valuation", "peer_metrics"]}),
    ("Assess business quality of {name}", "opportunity_assessment", "company", {"expect_evidence_contains": ["management_commentary", "quarterly_results"]}),
    ("Forecast earnings for {name}", "forecast_assessment", "company", {"expect_evidence_contains": ["historical_financials", "management_commentary"]}),
    ("What is today's quote for {name}?", "fact_retrieval", "company", {"expect_evidence_contains": ["live_prices"]}),
    ("News impact on {name}", "monitoring_update", "company", {"expect_evidence_contains": ["press_flow"]}),
    ("Annual report highlights for {name}", "decision_support", "company", {"expect_evidence_contains": ["official_filings"]}),
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
        "version": IAPE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "architecture_status": ARCHITECTURE_STATUS,
        "enabled": is_enabled(),
        "flags": flags_dict(),
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "max_planning_ms_target": MAX_PLANNING_MS_TARGET,
        "registry": registry_stats(),
        "not_a_top_level_intelligence_layer": True,
        "law": "Every API call must have a reason.",
        "evidence_budget": True,
    }


def constitution() -> dict[str, Any]:
    return {"enabled": is_enabled(), **constitution_dict(), "providers": all_providers()}


def plan(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    if not is_enabled():
        return {"ok": False, "enabled": False, "iape_version": IAPE_VERSION}
    body = payload or {}
    question = str(body.get("question") or body.get("q") or body.get("text") or "").strip()
    if not question:
        return {"ok": False, "error": "question is required", "iape_version": IAPE_VERSION}
    return {"enabled": True, **build_acquisition_plan(question, body)}


def enrich(payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Alias for plan — soft-wire enrichment entrypoint."""
    return plan(payload)


def dashboard() -> dict[str, Any]:
    samples = []
    for b in CORE_BENCHMARKS[:8]:
        row = build_acquisition_plan(
            b["q"],
            {"primary_objective": b.get("objective"), "intent_family": b.get("family")},
        )
        samples.append(
            {
                "question": b["q"],
                "required_data": [r.get("evidence_key") for r in (row.get("required_data") or [])],
                "selected_providers": row.get("selected_providers"),
                "reuse_internal_layers": [
                    {"evidence_key": r.get("evidence_key"), "provider": r.get("provider")}
                    for r in (row.get("reuse_internal_layers") or [])
                ],
                "skipped_apis_count": len(row.get("skipped_apis") or []),
                "fallback_providers": row.get("fallback_providers"),
                "expected_runtime": row.get("expected_runtime"),
                "expected_quality": (row.get("expected_quality") or {}).get("expected_quality"),
                "confidence": row.get("confidence"),
                "api_reduction": (row.get("metrics") or {}).get("api_reduction"),
                "planning_ms": (row.get("metrics") or {}).get("planning_ms"),
            }
        )
    return {
        "programme": PROGRAMME,
        "iape_version": IAPE_VERSION,
        "sprint": SPRINT,
        "sprint_name": SPRINT_NAME,
        "enabled": is_enabled(),
        "architecture_status": ARCHITECTURE_STATUS,
        "flags": flags_dict(),
        "registry": registry_stats(),
        "samples": samples,
        "quality_gates": quality_gates(),
        "website_surfaces": ["/admin/acquisition-planner"],
        "api_prefix": "/v1/acquisition-planner",
        "law": "Acquire only the evidence necessary to answer the research objective.",
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
    row = build_acquisition_plan(question, payload or {})
    return {
        "iape_version": IAPE_VERSION,
        "question": row.get("question"),
        "required_data": [r.get("evidence_key") for r in (row.get("required_data") or [])],
        "selected_providers": row.get("selected_providers"),
        "reuse_internal_layers": [
            {"evidence_key": r.get("evidence_key"), "provider": r.get("provider")}
            for r in (row.get("reuse_internal_layers") or [])
        ],
        "skipped_apis": [
            {"evidence_key": s.get("evidence_key"), "provider": s.get("provider"), "reason": s.get("reason")}
            for s in (row.get("skipped_apis") or [])[:12]
        ],
        "fallback_providers": row.get("fallback_providers"),
        "evidence_budget": {
            "maximum_api_calls": (row.get("evidence_budget") or {}).get("maximum_api_calls"),
            "api_calls_used": (row.get("evidence_budget") or {}).get("api_calls_used"),
            "within_budget": (row.get("evidence_budget") or {}).get("within_budget"),
        },
        "expected_runtime": row.get("expected_runtime"),
        "expected_quality": (row.get("expected_quality") or {}).get("expected_quality"),
        "freshness_plan": {
            "required_freshness": (row.get("freshness_plan") or {}).get("required_freshness"),
        },
        "authority_plan": {
            "authority_compliance": (row.get("authority_plan") or {}).get("authority_compliance"),
            "minimum_authority_tier": (row.get("authority_plan") or {}).get("minimum_authority_tier"),
        },
        "confidence": row.get("confidence"),
        "metrics": row.get("metrics"),
        "not_a_top_level_intelligence_layer": True,
    }


def _expanded() -> list[dict[str, Any]]:
    cases = list(CORE_BENCHMARKS)
    i = 0
    while len(cases) < 1100:
        tmpl, objective, family, extra = _TEMPLATES[i % len(_TEMPLATES)]
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
        cases.append({"q": q, "objective": objective, "family": family, **extra, "kind": "template"})
        i += 1
    return cases


def _provider_for_evidence(row: dict[str, Any], evidence_key: str) -> str | None:
    for s in row.get("selected_providers") or []:
        if s.get("evidence_key") == evidence_key:
            return str(s.get("provider"))
    for r in row.get("reuse_internal_layers") or []:
        if r.get("evidence_key") == evidence_key:
            return str(r.get("provider"))
    return None


def _check(b: dict[str, Any], row: dict[str, Any]) -> list[str]:
    errs: list[str] = []
    keys = {str(r.get("evidence_key")) for r in (row.get("required_data") or [])}
    if b.get("expect_evidence_contains") and not set(b["expect_evidence_contains"]).issubset(keys):
        errs.append("evidence_contains")
    reuse_n = len(row.get("reuse_internal_layers") or [])
    if b.get("expect_reuse_min") is not None and reuse_n < int(b["expect_reuse_min"]):
        errs.append("reuse_min")
    if b.get("max_api_calls") is not None and len(row.get("selected_providers") or []) > int(b["max_api_calls"]):
        errs.append("max_api_calls")
    for ek, allowed in (b.get("primary_in") or {}).items():
        pid = _provider_for_evidence(row, ek)
        # ok if reused internal or selected in allowed
        if pid is None:
            # may be budget-skipped; only fail if evidence was required and neither reuse nor acquire
            if ek in keys:
                covered = any(r.get("evidence_key") == ek for r in (row.get("reuse_internal_layers") or []))
                covered = covered or any(s.get("evidence_key") == ek for s in (row.get("selected_providers") or []))
                if not covered:
                    errs.append(f"primary_missing:{ek}")
        elif pid not in allowed and pid not in PROVIDERS:
            errs.append(f"primary_invalid:{ek}")
        elif pid not in allowed and not PROVIDERS.get(pid, {}).get("internal"):
            # allow internal reuse even if not in allowed list
            errs.append(f"primary_in:{ek}")
    metrics = row.get("metrics") or {}
    if int(metrics.get("duplicate_fetches") or 0) != 0:
        errs.append("duplicate_fetches")
    if not (row.get("authority_plan") or {}).get("authority_compliance", True):
        errs.append("authority_compliance")
    if not row.get("mandatory_fields_present", True):
        errs.append("mandatory_fields")
    return errs


def quality_gates() -> dict[str, Any]:
    cases = _expanded()
    provider_ok = 0
    reuse_ok = 0
    authority_ok = 0
    fallback_ok = 0
    dup_ok = 0
    plan_times: list[float] = []
    reductions: list[float] = []
    failures: list[dict[str, Any]] = []
    checked = 0

    for b in cases:
        row = build_acquisition_plan(
            b["q"],
            {"primary_objective": b.get("objective"), "intent_family": b.get("family")},
        )
        checked += 1
        errs = _check(b, row)
        metrics = row.get("metrics") or {}
        plan_times.append(float(metrics.get("planning_ms") or 0))
        reductions.append(float(metrics.get("api_reduction") or 0))
        if int(metrics.get("duplicate_fetches") or 0) == 0:
            dup_ok += 1
        if (row.get("authority_plan") or {}).get("authority_compliance", False):
            authority_ok += 1
        if metrics.get("fallback_coverage"):
            fallback_ok += 1
        # reuse accuracy: if cache said reuse, provider must be internal
        reuse_good = True
        for r in row.get("reuse_internal_layers") or []:
            if not PROVIDERS.get(str(r.get("provider")), {}).get("internal"):
                reuse_good = False
                break
        if reuse_good:
            reuse_ok += 1
        if not errs:
            provider_ok += 1
        else:
            if len(failures) < 25:
                failures.append({"q": b["q"], "errs": errs})

    n = max(checked, 1)
    avg_ms = sum(plan_times) / n
    avg_reduction = sum(reductions) / n
    provider_acc = provider_ok / n
    reuse_acc = reuse_ok / n
    auth_acc = authority_ok / n
    fb_acc = fallback_ok / n
    dup_acc = dup_ok / n

    criteria = constitution_dict()["success_criteria"]
    passed = (
        checked >= int(criteria["benchmark_minimum"])
        and provider_acc >= float(criteria["provider_selection_accuracy"])
        and reuse_acc >= float(criteria["internal_reuse_accuracy"])
        and dup_acc >= 1.0
        and auth_acc >= float(criteria["authority_compliance"])
        and fb_acc >= float(criteria["fallback_success"])
        and avg_ms < float(criteria["average_planning_ms"])
        and avg_reduction >= float(criteria["average_api_reduction"])
    )
    return {
        "ok": passed,
        "checked": checked,
        "provider_selection_accuracy": round(provider_acc, 4),
        "internal_reuse_accuracy": round(reuse_acc, 4),
        "duplicate_api_calls": 0 if dup_acc == 1.0 else int(n - dup_ok),
        "authority_compliance": round(auth_acc, 4),
        "fallback_success": round(fb_acc, 4),
        "average_planning_ms": round(avg_ms, 4),
        "average_api_reduction": round(avg_reduction, 4),
        "benchmark_minimum": criteria["benchmark_minimum"],
        "targets": criteria,
        "failures_sample": failures,
        "iape_version": IAPE_VERSION,
        "sprint": SPRINT,
    }
