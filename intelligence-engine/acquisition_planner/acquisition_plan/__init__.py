"""Acquisition plan composer — WHAT / FROM WHERE / ORDER / WHY."""

from __future__ import annotations

import time
from typing import Any

from acquisition_planner.api_registry import PROVIDERS
from acquisition_planner.cache_manager import inspect_internal_cache
from acquisition_planner.confidence_engine import estimate_confidence
from acquisition_planner.cost_engine import score_costs
from acquisition_planner.evidence_budget import apply_evidence_budget, resolve_budget
from acquisition_planner.evidence_requirements import derive_evidence_requirements
from acquisition_planner.fallback_engine import build_fallback_chains
from acquisition_planner.freshness_engine import resolve_freshness_plan
from acquisition_planner.provider_selector import select_providers_for_evidence
from acquisition_planner.quality_engine import score_acquisition_quality
from acquisition_planner.redundancy_detector import detect_redundancy
from acquisition_planner.schema import (
    AUTHORITY_TIERS,
    IAPE_VERSION,
    MANDATORY_OUTPUT_FIELDS,
    constitution_dict,
)


def _infer_objective(question: str, body: dict[str, Any]) -> tuple[str, str]:
    obj = str(body.get("primary_objective") or body.get("objective") or "").strip().lower()
    family = str(body.get("intent_family") or body.get("family") or "").strip().lower()
    q = question.lower()
    if not obj:
        if "explain" in q or "what is" in q or "define" in q:
            obj = "educational_explanation"
        elif "compare" in q or " vs " in q:
            obj = "comparison_assessment"
        elif "portfolio" in q or "allocate" in q:
            obj = "portfolio_assessment"
        elif "risk" in q:
            obj = "risk_assessment"
        elif "forecast" in q or "will " in q:
            obj = "forecast_assessment"
        elif "price" in q or "today" in q or "quote" in q:
            obj = "fact_retrieval"
        elif "buy" in q or "sell" in q or "should i" in q:
            obj = "decision_support"
        elif "overvalued" in q or "pe" in q or "valuation" in q:
            obj = "valuation_assessment"
        else:
            obj = "decision_support"
    if not family:
        if "rbi" in q or "macro" in q or "inflation" in q or "rate cut" in q:
            family = "macro"
        elif "portfolio" in q:
            family = "portfolio"
        elif obj == "educational_explanation":
            family = "educational"
        elif "sector" in q or "nifty" in q:
            family = "sector"
        else:
            family = "company"
    # normalize objective aliases from ROE/ILR
    aliases = {
        "investment evaluation": "decision_support",
        "valuation assessment": "valuation_assessment",
        "risk assessment": "risk_assessment",
        "peer comparison": "comparison_assessment",
        "educational": "educational_explanation",
        "macro impact": "forecast_assessment",
        "portfolio decision": "portfolio_assessment",
        "historical analysis": "valuation_assessment",
        "forecast": "forecast_assessment",
        "business quality assessment": "opportunity_assessment",
        "news impact": "monitoring_update",
        "screening": "comparison_assessment",
        "scenario analysis": "forecast_assessment",
    }
    obj = aliases.get(obj, obj)
    return obj, family


def build_acquisition_plan(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    payload = body or {}
    primary_objective, intent_family = _infer_objective(question, payload)
    required_layers = list(payload.get("required_layers") or [])

    evidence = derive_evidence_requirements(
        research_question=question,
        primary_objective=primary_objective,
        intent_family=intent_family,
        required_layers=required_layers,
    )
    freshness_plan = resolve_freshness_plan(
        primary_objective=primary_objective,
        required_data=evidence["required_data"],
    )
    budget = resolve_budget(payload.get("evidence_budget") if isinstance(payload.get("evidence_budget"), dict) else None)
    # align budget freshness with plan
    budget["required_freshness"] = freshness_plan.get("required_freshness") or budget.get("required_freshness")

    cache = inspect_internal_cache(
        required_data=evidence["required_data"],
        freshness_plan=freshness_plan,
        inventory=payload.get("internal_inventory") if isinstance(payload.get("internal_inventory"), dict) else None,
    )
    reused_keys = {str(r.get("evidence_key")) for r in cache["reuse_internal_layers"]}

    selections: list[dict[str, Any]] = []
    acquire_candidates: list[dict[str, Any]] = []
    skipped_apis: list[dict[str, Any]] = []

    for item in evidence["required_data"]:
        key = str(item.get("evidence_key") or "")
        if key in reused_keys:
            skipped_apis.append(
                {
                    "evidence_key": key,
                    "action": "skip_external",
                    "reason": "Reusing internal intelligence",
                    "providers_skipped": list(item.get("preferred_providers") or []),
                }
            )
            continue
        sel = select_providers_for_evidence(
            evidence_item=item,
            min_authority_tier=int(budget.get("minimum_authority_tier") or 2),
        )
        selections.append(sel)
        primary = sel.get("primary")
        if primary:
            acquire_candidates.append(
                {
                    "evidence_key": key,
                    "label": item.get("label"),
                    "provider": primary["provider"],
                    "provider_name": primary.get("name"),
                    "tier": primary.get("tier"),
                    "authority_score": primary.get("authority_score"),
                    "expected_latency_ms": primary.get("expected_latency_ms"),
                    "cost": primary.get("cost"),
                    "expected_value": PROVIDERS.get(primary["provider"], {}).get("expected_value"),
                    "action": "acquire",
                    "research_purpose": item.get("research_purpose"),
                    "destination_layer": _destination_layer(key),
                    "fallbacks": [f.get("provider") for f in (sel.get("fallbacks") or [])],
                }
            )
            # mark lower-authority preferred APIs as skipped when not primary
            for pid in item.get("preferred_providers") or []:
                if pid != primary["provider"] and pid not in (primary.get("fallback_providers") or [])[:1]:
                    if not PROVIDERS.get(pid, {}).get("internal"):
                        skipped_apis.append(
                            {
                                "evidence_key": key,
                                "provider": pid,
                                "action": "skip",
                                "reason": f"Lower priority than {primary['provider']}",
                            }
                        )

    # quality preview before budget
    preview_quality = score_acquisition_quality(
        required_data=evidence["required_data"],
        acquire_steps=acquire_candidates,
        reuse_steps=cache["reuse_internal_layers"],
        freshness_plan=freshness_plan,
    )
    budgeted = apply_evidence_budget(
        acquire_candidates=acquire_candidates,
        reuse_steps=cache["reuse_internal_layers"],
        budget=budget,
        quality_preview=float(preview_quality.get("expected_quality") or 0.7),
    )
    for skip in budgeted.get("skipped_for_budget") or []:
        skipped_apis.append(
            {
                "evidence_key": skip.get("evidence_key"),
                "provider": skip.get("provider"),
                "action": "skip_budget",
                "reason": skip.get("skip_reason"),
            }
        )

    red = detect_redundancy(
        acquire_steps=budgeted["selected_acquire"],
        reuse_steps=cache["reuse_internal_layers"],
    )
    acquire_final = red["deduped_acquire"]

    # also mark duplicates as skipped
    for dup in red["duplicate_fetches_prevented"]:
        skipped_apis.append({**dup, "action": "skip_duplicate"})

    quality = score_acquisition_quality(
        required_data=evidence["required_data"],
        acquire_steps=acquire_final,
        reuse_steps=cache["reuse_internal_layers"],
        freshness_plan=freshness_plan,
    )
    costs = score_costs(acquire_final, cache["reuse_internal_layers"])
    fallbacks = build_fallback_chains(selections)
    authority_ok = all(bool(s.get("authority_compliant", True)) for s in selections) if selections else True
    conf = estimate_confidence(
        quality=quality,
        reuse_count=cache["reuse_count"],
        acquire_count=len(acquire_final),
        duplicate_count=0,  # prevented, not executed
        authority_compliant=authority_ok,
    )

    # API reduction vs naive fetch-all preferred externals
    naive = 0
    for item in evidence["required_data"]:
        prefs = [p for p in (item.get("preferred_providers") or []) if not PROVIDERS.get(p, {}).get("internal")]
        naive += max(1, min(2, len(prefs)))  # naive would hit 1-2 APIs per need
    actual = len(acquire_final)
    reduction = ((naive - actual) / naive) if naive else 1.0

    visual_plan = []
    for r in cache["reuse_internal_layers"]:
        visual_plan.append(
            {
                "question": question,
                "evidence_requirement": r.get("evidence_key"),
                "selected_provider": r.get("provider"),
                "retrieved_evidence": "reuse",
                "destination_layer": _destination_layer(str(r.get("evidence_key"))),
            }
        )
    for a in acquire_final:
        visual_plan.append(
            {
                "question": question,
                "evidence_requirement": a.get("evidence_key"),
                "selected_provider": a.get("provider"),
                "retrieved_evidence": "acquire",
                "destination_layer": a.get("destination_layer"),
            }
        )

    authority_plan = {
        "tiers": AUTHORITY_TIERS,
        "minimum_authority_tier": budget.get("minimum_authority_tier"),
        "selected_tiers": sorted({int(a.get("tier") or 5) for a in acquire_final}),
        "tier1_preferred": True,
        "authority_compliance": authority_ok,
    }

    planning_ms = (time.perf_counter() - t0) * 1000.0
    plan = {
        "ok": True,
        "question": question,
        "primary_objective": primary_objective,
        "intent_family": intent_family,
        "required_data": evidence["required_data"],
        "selected_providers": [
            {
                "evidence_key": a.get("evidence_key"),
                "provider": a.get("provider"),
                "provider_name": a.get("provider_name"),
                "tier": a.get("tier"),
                "research_purpose": a.get("research_purpose"),
            }
            for a in acquire_final
        ],
        "reuse_internal_layers": cache["reuse_internal_layers"],
        "skipped_apis": skipped_apis,
        "fallback_providers": fallbacks.get("fallback_providers"),
        "fallback_chains": fallbacks.get("fallback_chains"),
        "evidence_budget": {
            **budgeted.get("budget", budget),
            "api_calls_used": budgeted.get("api_calls_used"),
            "runtime_ms_used": budgeted.get("runtime_ms_used"),
            "within_budget": budgeted.get("within_budget"),
            "optimisation": budgeted.get("optimisation"),
            "skipped_for_budget": len(budgeted.get("skipped_for_budget") or []),
        },
        "expected_runtime": {
            "planning_ms": round(planning_ms, 4),
            "acquisition_ms": costs.get("expected_runtime_ms"),
            "total_ms": round(planning_ms + float(costs.get("expected_runtime_ms") or 0), 2),
        },
        "expected_quality": quality,
        "freshness_plan": freshness_plan,
        "authority_plan": authority_plan,
        "confidence": conf.get("confidence"),
        "confidence_detail": conf,
        "executed_acquisitions": [
            {
                "order": i + 1,
                "action": a.get("action"),
                "provider": a.get("provider"),
                "evidence_key": a.get("evidence_key"),
                "why": a.get("research_purpose"),
                "destination_layer": a.get("destination_layer"),
            }
            for i, a in enumerate(acquire_final)
        ]
        + [
            {
                "order": len(acquire_final) + i + 1,
                "action": "reuse",
                "provider": r.get("provider"),
                "evidence_key": r.get("evidence_key"),
                "why": r.get("reason"),
                "destination_layer": _destination_layer(str(r.get("evidence_key"))),
            }
            for i, r in enumerate(cache["reuse_internal_layers"])
        ],
        "visual_plan": visual_plan,
        "metrics": {
            "planning_ms": round(planning_ms, 4),
            "api_calls": actual,
            "reuse_count": cache["reuse_count"],
            "duplicate_fetches": 0,
            "duplicates_prevented": red.get("duplicate_count", 0),
            "api_reduction": round(max(0.0, reduction), 4),
            "naive_api_calls": naive,
            "authority_compliance": authority_ok,
            "fallback_coverage": fallbacks.get("fallback_coverage"),
        },
        "iape_version": IAPE_VERSION,
        "constitution_id": constitution_dict().get("id"),
        "not_a_top_level_intelligence_layer": True,
        "mandatory_fields_present": all(
            f in {
                "question",
                "required_data",
                "selected_providers",
                "reuse_internal_layers",
                "skipped_apis",
                "fallback_providers",
                "evidence_budget",
                "expected_runtime",
                "expected_quality",
                "freshness_plan",
                "authority_plan",
                "confidence",
                "executed_acquisitions",
            }
            for f in MANDATORY_OUTPUT_FIELDS
        ),
    }
    return plan


def _destination_layer(evidence_key: str) -> str:
    mapping = {
        "official_filings": "FIL",
        "quarterly_results": "FIL",
        "historical_financials": "FIL",
        "peer_metrics": "PIL",
        "macro_data": "MDI",
        "management_commentary": "MIL",
        "historical_valuation": "PIL",
        "portfolio_exposure": "ILM",
        "live_prices": "QIL",
        "regulatory_policy": "RIL",
        "press_flow": "EIL",
        "knowledge_graph_context": "IKG",
        "evidence_corpus": "EIL",
    }
    return mapping.get(evidence_key, "EIL")
