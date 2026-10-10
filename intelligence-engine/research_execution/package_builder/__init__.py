"""Package builder — assemble the immutable Institutional Research Execution Package."""

from __future__ import annotations

import time
from typing import Any

from research_execution.package_audit import build_audit
from research_execution.package_memory import remember_package
from research_execution.package_validator import validate_package
from research_execution.package_version import new_package_ids
from research_execution.research_contract import build_research_contract
from research_execution.schema import ARCHITECTURE_STATUS, IREP_VERSION


def _unwrap(slice_: dict[str, Any] | None, key: str) -> dict[str, Any]:
    if not slice_:
        return {}
    if key in slice_ and isinstance(slice_.get(key), dict):
        return slice_[key]
    return slice_


def _safe_call(fn, *args, **kwargs) -> dict[str, Any]:
    try:
        out = fn(*args, **kwargs)
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def _hydrate_inputs(question: str, body: dict[str, Any]) -> dict[str, Any]:
    """Gather RQ1 slices from payload or live soft-wires."""
    ontology = body.get("research_ontology") or {}
    ere = body.get("entity_resolution") or {}
    roe = body.get("research_objective") or {}
    cie = body.get("context_intelligence") or {}
    iar = body.get("analyst_router") or {}
    ilr = body.get("layer_router") or {}
    iape = body.get("acquisition_planner") or body.get("api_plan") or {}
    drbe = body.get("research_blueprint") or body.get("blueprint") or {}
    ivce = body.get("validation_engine") or body.get("validation") or {}

    if not ontology:
        try:
            from research_ontology.production import soft_slice_for_ask_agi

            ontology = soft_slice_for_ask_agi(question) or {}
        except Exception:
            ontology = {}
    if not ere:
        try:
            from entity_resolution.production import soft_slice_for_ask_agi as ere_soft

            ere = ere_soft(question, body) or {}
        except Exception:
            ere = {}
    if not roe:
        try:
            from research_objective.production import soft_slice_for_ask_agi as roe_soft

            roe = roe_soft(
                question,
                {
                    "entity_resolution": _unwrap(ere, "entity_resolution"),
                    "intent": _unwrap(ontology, "research_ontology"),
                },
            ) or {}
        except Exception:
            roe = {}
    if not cie:
        try:
            from context_intelligence.production import soft_slice_for_ask_agi as cie_soft

            cie = cie_soft(
                question,
                {
                    "entity_resolution": _unwrap(ere, "entity_resolution"),
                    "research_objective": _unwrap(roe, "research_objective"),
                    "skip_iar": True,
                },
            ) or {}
        except Exception:
            cie = {}
    if not iar:
        try:
            from analyst_router.production import soft_slice_for_ask_agi as iar_soft

            iar = iar_soft(question, {"research_objective": _unwrap(roe, "research_objective")}) or {}
        except Exception:
            iar = {}
    if not ilr:
        try:
            from layer_router.production import soft_slice_for_ask_agi as ilr_soft

            ilr = ilr_soft(
                question,
                {
                    "research_objective": _unwrap(roe, "research_objective"),
                    "analyst_router": _unwrap(iar, "analyst_router"),
                    "skip_iar": True,
                },
            ) or {}
        except Exception:
            ilr = {}

    # Optional sprints 7–9 if packages are available
    if not iape:
        try:
            from acquisition_planner.production import soft_slice_for_ask_agi as iape_soft

            iape = iape_soft(
                question,
                {
                    "primary_objective": (_unwrap(roe, "research_objective") or {}).get("primary_objective"),
                    "required_layers": (_unwrap(ilr, "layer_router") or {}).get("required_layers"),
                },
            ) or {}
        except Exception:
            iape = {}
    if not drbe:
        try:
            from research_blueprint.production import soft_slice_for_ask_agi as drbe_soft

            drbe = drbe_soft(
                question,
                {
                    "primary_objective": (_unwrap(roe, "research_objective") or {}).get("primary_objective")
                    or (_unwrap(iar, "analyst_router") or {}).get("primary_objective"),
                    "required_analysts": (_unwrap(iar, "analyst_router") or {}).get("required_analysts"),
                },
            ) or {}
        except Exception:
            drbe = {}
    if not ivce:
        try:
            from validation_engine.production import soft_slice_for_ask_agi as ivce_soft

            ivce = ivce_soft(
                question,
                {
                    "research_ontology": ontology,
                    "entity_resolution": ere,
                    "research_objective": roe,
                    "context_intelligence": cie,
                    "analyst_router": iar,
                    "layer_router": ilr,
                    "acquisition_planner": iape,
                    "research_blueprint": drbe,
                },
            ) or {}
        except Exception:
            ivce = {}

    return {
        "ontology": ontology,
        "ere": ere,
        "roe": roe,
        "cie": cie,
        "iar": iar,
        "ilr": ilr,
        "iape": iape,
        "drbe": drbe,
        "ivce": ivce,
    }


def _infer_blueprint(question: str, primary_objective: str | None) -> dict[str, Any]:
    q = question.lower()
    obj = (primary_objective or "").lower()
    if "explain" in q or "educational" in obj:
        return {
            "report_type": "educational_guide",
            "report_name": "Educational Guide",
            "section_order": [
                "definition",
                "importance",
                "calculation",
                "examples",
                "common_mistakes",
                "case_study",
                "summary",
            ],
            "section_owner": {
                "definition": "Academy",
                "importance": "Academy",
                "calculation": "Financial",
                "examples": "Academy",
                "common_mistakes": "Academy",
                "case_study": "Academy",
                "summary": "Research Writer",
            },
            "quality_rules": {"writing_style": "educational", "citation_rules": "recommended"},
            "inferred": True,
        }
    if "compare" in q or "peer comparison" in obj:
        return {
            "report_type": "comparison_report",
            "report_name": "Comparison Report",
            "section_order": [
                "executive_summary",
                "business_comparison",
                "financial_comparison",
                "competitive_position",
                "valuation_comparison",
                "historical_comparison",
                "risk_comparison",
                "conclusion",
            ],
            "section_owner": {
                "business_comparison": "Business",
                "financial_comparison": "Financial",
                "valuation_comparison": "Valuation",
                "competitive_position": "Sector",
                "risk_comparison": "Risk",
            },
            "quality_rules": {"writing_style": "comparison_note", "citation_rules": "required"},
            "inferred": True,
        }
    if "versus history" in q or "historical" in obj:
        return {
            "report_type": "historical_valuation_report",
            "report_name": "Historical Valuation Report",
            "section_order": [
                "executive_summary",
                "historical_valuation",
                "historical_percentiles",
                "peer_comparison",
                "macro_drivers",
                "market_expectations",
                "scenario_analysis",
                "conclusion",
            ],
            "section_owner": {"historical_valuation": "Valuation", "macro_drivers": "Macro"},
            "quality_rules": {"writing_style": "valuation_note", "citation_rules": "required"},
            "inferred": True,
        }
    if "portfolio" in q or "portfolio" in obj:
        return {
            "report_type": "portfolio_memorandum",
            "report_name": "Portfolio Memorandum",
            "section_order": [
                "executive_summary",
                "portfolio_construction",
                "risk",
                "portfolio_fit",
                "recommendation",
                "conclusion",
            ],
            "section_owner": {"portfolio_construction": "Portfolio", "risk": "Risk"},
            "quality_rules": {"writing_style": "portfolio_memo", "citation_rules": "required"},
            "inferred": True,
        }
    if "rbi" in q or "macro" in obj:
        return {
            "report_type": "macro_intelligence_report",
            "report_name": "Macro Intelligence Report",
            "section_order": [
                "executive_summary",
                "macro_drivers",
                "policy",
                "transmission",
                "forecast",
                "risks",
                "conclusion",
            ],
            "section_owner": {"macro_drivers": "Macro", "policy": "Macro", "forecast": "Forecast"},
            "quality_rules": {"writing_style": "macro_brief", "citation_rules": "required"},
            "inferred": True,
        }
    return {
        "report_type": "institutional_investment_report",
        "report_name": "Institutional Investment Report",
        "section_order": [
            "executive_summary",
            "investment_thesis",
            "business_quality",
            "financial_quality",
            "valuation",
            "risk",
            "forecast",
            "portfolio_fit",
            "committee_opinion",
            "cio_summary",
        ],
        "section_owner": {
            "business_quality": "Business",
            "financial_quality": "Financial",
            "valuation": "Valuation",
            "risk": "Risk",
            "forecast": "Forecast",
            "portfolio_fit": "Portfolio",
            "committee_opinion": "Committee",
            "cio_summary": "CIO",
        },
        "quality_rules": {"writing_style": "institutional_memo", "citation_rules": "required"},
        "inferred": True,
    }


def _infer_api_plan(question: str, entity: dict[str, Any], layers: list[str]) -> dict[str, Any]:
    providers = []
    reuse = []
    if entity.get("ticker") or entity.get("canonical_name"):
        providers.extend(["groww", "company_ir"])
        reuse.extend(["fil", "pil"])
    if any(l in layers for l in ("Macro", "MDI", "CIG")):
        providers.append("fred")
    if "FIL" in layers or "fil" in reuse:
        reuse = sorted(set(reuse + ["fil"]))
    if not providers and not reuse:
        reuse = ["ilm", "ikg"]
    return {
        "providers": providers,
        "internal_reuse": reuse,
        "fallback_chain": ["indianapi", "yahoo_finance", "nse", "bse"],
        "freshness": "daily" if "should i" in question.lower() else "existing_knowledge",
        "authority": "tier1_preferred",
        "inferred": True,
    }


def _infer_validation(question: str, entity: dict[str, Any]) -> dict[str, Any]:
    q = question.lower()
    if any(x in q for x in ("analyse tata", "analyze tata", "buy tata", "should i buy tata")):
        return {
            "readiness_state": "CLARIFICATION_REQUIRED",
            "execution_allowed": False,
            "overall_readiness": 0.55,
            "warnings": [],
            "clarifications": [{"type": "entity_disambiguation", "prompt": "Which company do you mean?"}],
            "confidence": 0.55,
            "inferred": True,
        }
    if q.strip() in {"compare", "analyse", "analyze"} or q.startswith("compare ") and " vs " not in q and " versus " not in q and " with " not in q:
        if q.startswith("compare ") and len(q.split()) <= 3:
            return {
                "readiness_state": "CLARIFICATION_REQUIRED",
                "execution_allowed": False,
                "overall_readiness": 0.6,
                "warnings": [],
                "clarifications": [{"type": "comparison_target", "prompt": "Compare with which company?"}],
                "confidence": 0.6,
                "inferred": True,
            }
    if "guaranteed returns" in q or "sure shot" in q:
        return {
            "readiness_state": "BLOCKED",
            "execution_allowed": False,
            "overall_readiness": 0.3,
            "warnings": ["policy: disallowed_request"],
            "clarifications": [],
            "confidence": 0.3,
            "inferred": True,
        }
    ready = 0.91 if entity.get("canonical_name") or entity.get("ticker") else 0.82
    return {
        "readiness_state": "READY_WITH_WARNINGS" if ready < 0.9 else "READY",
        "execution_allowed": True,
        "overall_readiness": ready,
        "warnings": ["Soft validation inferred — IVCE package not mounted"],
        "clarifications": [],
        "confidence": ready,
        "inferred": True,
    }


def build_execution_package(question: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
    t0 = time.perf_counter()
    payload = body or {}
    ids = new_package_ids(question)
    hydrated = _hydrate_inputs(question, payload)

    ontology = _unwrap(hydrated["ontology"], "research_ontology")
    ere = _unwrap(hydrated["ere"], "entity_resolution")
    roe = _unwrap(hydrated["roe"], "research_objective")
    cie = _unwrap(hydrated["cie"], "context_intelligence")
    iar = _unwrap(hydrated["iar"], "analyst_router")
    ilr = _unwrap(hydrated["ilr"], "layer_router")
    iape = hydrated["iape"] if isinstance(hydrated["iape"], dict) else {}
    drbe = hydrated["drbe"] if isinstance(hydrated["drbe"], dict) else {}
    ivce = hydrated["ivce"] if isinstance(hydrated["ivce"], dict) else {}
    # unwrap nested soft-slices
    if "acquisition_planner" in iape:
        iape = iape.get("acquisition_planner") or iape
    if "research_blueprint" in drbe and isinstance(drbe.get("research_blueprint"), dict):
        drbe = drbe["research_blueprint"]
    if "validation_engine" in ivce and isinstance(ivce.get("validation_engine"), dict):
        ivce = ivce["validation_engine"]

    canonical = ere.get("canonical_entity") or {}
    entity = {
        "canonical_name": canonical.get("canonical_name") or ere.get("entity"),
        "ticker": ere.get("ticker") or canonical.get("ticker"),
        "entity_type": ere.get("entity_type") or canonical.get("entity_type"),
        "sector": ere.get("sector") or canonical.get("sector"),
        "industry": ere.get("industry") or canonical.get("industry"),
        "relationships": ere.get("relationships") or canonical.get("relationships") or {},
        "knowledge_graph_node": ere.get("knowledge_graph_id") or canonical.get("knowledge_graph_id"),
        "status": canonical.get("status") or ere.get("status"),
        "needs_clarification": ere.get("needs_clarification"),
        "possible_matches": ere.get("possible_matches") or [],
    }

    primary_objective = (
        roe.get("primary_objective")
        or iar.get("primary_objective")
        or ilr.get("primary_objective")
        or ontology.get("primary_intent")
        or ontology.get("intent")
    )
    intent = {
        "primary_intent": ontology.get("primary_intent") or ontology.get("intent") or primary_objective,
        "secondary_intents": ontology.get("secondary_intents") or ontology.get("secondary") or [],
        "research_objective": primary_objective,
        "decision_type": roe.get("decision_type") or ontology.get("decision_type"),
        "research_depth": roe.get("research_depth") or "standard",
        "expected_deliverable": roe.get("expected_deliverable") or ontology.get("expected_deliverable"),
        "intent_family": ontology.get("intent_family") or ontology.get("family") or payload.get("intent_family"),
        "confidence": ontology.get("confidence") or roe.get("confidence"),
    }

    context_card = cie.get("research_context_card") or cie.get("context_card") or cie
    context = {
        "market_regime": context_card.get("market_regime") or cie.get("market_regime"),
        "macro": context_card.get("macro") or cie.get("macro"),
        "historical": context_card.get("historical") or cie.get("historical"),
        "portfolio": context_card.get("portfolio") or cie.get("portfolio"),
        "event": context_card.get("event") or cie.get("event"),
        "expectations": context_card.get("expectations") or cie.get("expectations"),
        "scenario": context_card.get("scenario") or cie.get("scenario"),
        "time_horizon": context_card.get("time_horizon")
        or cie.get("time_horizon")
        or roe.get("time_horizon")
        or "long-term",
        "confidence": cie.get("confidence"),
    }

    analyst_plan = {
        "required_analysts": list(iar.get("required_analysts") or []),
        "optional_analysts": list(iar.get("optional_analysts") or []),
        "suppressed_analysts": list(iar.get("suppressed_analysts") or []),
        "speaking_order": list(iar.get("speaking_order") or []),
        "weights": iar.get("weights") or {},
        "dependencies": iar.get("dependencies") or {},
        "routing_confidence": iar.get("routing_confidence"),
    }
    layer_plan = {
        "required_layers": list(ilr.get("required_layers") or []),
        "optional_layers": list(ilr.get("optional_layers") or []),
        "suppressed_layers": list(ilr.get("suppressed_layers") or []),
        "parallel_groups": ilr.get("parallel_groups") or [],
        "dependencies": (ilr.get("execution_graph") or {}).get("dependencies")
        or ilr.get("dependencies")
        or {},
        "confidence_contribution": ilr.get("expected_contributions") or ilr.get("confidence_plan") or {},
        "estimated_runtime": ilr.get("estimated_runtime"),
        "runtime_reduction": ilr.get("runtime_reduction"),
    }

    if drbe.get("report_type") or drbe.get("section_order"):
        blueprint = {
            "report_type": drbe.get("report_type"),
            "report_name": drbe.get("report_name"),
            "section_order": list(drbe.get("section_order") or []),
            "section_owner": drbe.get("section_owner") or {},
            "mandatory_sections": list(drbe.get("mandatory_sections") or []),
            "optional_sections": list(drbe.get("optional_sections") or []),
            "hidden_sections": list(drbe.get("hidden_sections") or []),
            "suppressed_sections": list(drbe.get("suppressed_sections") or []),
            "quality_rules": drbe.get("quality_rules") or {},
            "evidence_requirements": (drbe.get("quality_rules") or {}).get("evidence_requirements")
            or drbe.get("evidence_requirements"),
            "assignment_book": drbe.get("assignment_book"),
            "inferred": False,
        }
    else:
        blueprint = _infer_blueprint(question, str(primary_objective) if primary_objective else None)

    if iape.get("selected_providers") or iape.get("providers") or iape.get("reuse_internal_layers"):
        api_plan = {
            "providers": [
                p.get("provider") if isinstance(p, dict) else p
                for p in (iape.get("selected_providers") or iape.get("providers") or [])
            ],
            "internal_reuse": [
                r.get("provider") if isinstance(r, dict) else r
                for r in (iape.get("reuse_internal_layers") or iape.get("internal_reuse") or [])
            ],
            "fallback_chain": iape.get("fallback_providers") or iape.get("fallback_chain") or [],
            "freshness": (iape.get("freshness_plan") or {}).get("required_freshness")
            or iape.get("freshness"),
            "authority": (iape.get("authority_plan") or {}).get("minimum_authority_tier")
            or iape.get("authority"),
            "evidence_budget": iape.get("evidence_budget"),
            "inferred": False,
        }
    else:
        api_plan = _infer_api_plan(question, entity, layer_plan["required_layers"])

    if ivce.get("readiness_state") or ivce.get("overall_readiness") is not None:
        validation = {
            "readiness_state": ivce.get("readiness_state"),
            "execution_allowed": ivce.get("execution_allowed"),
            "overall_readiness": ivce.get("overall_readiness"),
            "warnings": list(ivce.get("warnings") or []),
            "clarifications": list(ivce.get("clarifications") or []),
            "confidence": ivce.get("confidence"),
            "readiness_memo": ivce.get("readiness_memo"),
            "inferred": False,
        }
    else:
        validation = _infer_validation(question, entity)

    contract = build_research_contract(
        question=question,
        intent=intent,
        entity=entity,
        analyst_plan=analyst_plan,
        blueprint=blueprint,
    )

    est_runtime = float(layer_plan.get("estimated_runtime") or 0) or (
        800 + 120 * len(analyst_plan["required_analysts"]) + 80 * len(layer_plan["required_layers"])
    )
    expected_confidence = float(
        validation.get("overall_readiness")
        or iar.get("routing_confidence")
        or 0.85
    )
    execution_plan = {
        "estimated_runtime_ms": round(est_runtime, 2),
        "estimated_runtime_seconds": round(est_runtime / 1000.0, 2),
        "estimated_cost_units": len(api_plan.get("providers") or [])
        + max(0, len(layer_plan["required_layers"]) // 3),
        "expected_confidence": round(expected_confidence, 4),
        "expected_evidence_count": int(contract.get("minimum_evidence") or 8),
        "expected_citations": int(contract.get("minimum_evidence") or 8),
        "may_execute": bool(validation.get("execution_allowed", True)),
        "consumers": [
            "Analysts",
            "Intelligence Layers",
            "Investment Committee",
            "Portfolio Office",
            "Decision Engine",
            "CIO",
            "Research Writer",
        ],
    }

    quality_targets = {
        "minimum_evidence": int(contract.get("minimum_evidence") or 8),
        "minimum_confidence": 0.85,
        "maximum_runtime_ms": max(4000, int(est_runtime * 1.5)),
        "maximum_missing_data": 2,
        "required_citations": int(contract.get("minimum_evidence") or 8),
        "required_peer_coverage": int(contract.get("minimum_peer_comparisons") or 0),
        "required_historical_coverage_years": int(contract.get("minimum_historical_coverage_years") or 0),
        "maximum_unsupported_claims": 0,
        "maximum_hallucinations": 0,
    }

    success_metrics = {
        "blueprint_accuracy_target": 0.99,
        "evidence_coverage_target": 0.95,
        "reasoning_quality_target": 0.9,
        "hallucination_target": 0.0,
        "institutional_score_target": 0.9,
    }

    sources = []
    for name, blob in (
        ("research_ontology", ontology),
        ("entity_resolution", ere),
        ("research_objective", roe),
        ("context_intelligence", cie),
        ("analyst_router", iar),
        ("layer_router", ilr),
        ("acquisition_planner", iape if not api_plan.get("inferred") else {}),
        ("research_blueprint", drbe if not blueprint.get("inferred") else {}),
        ("validation_engine", ivce if not validation.get("inferred") else {}),
    ):
        if blob:
            sources.append(name)

    package: dict[str, Any] = {
        "package_id": ids["package_id"],
        "immutable": True,
        "metadata": {
            **ids,
            "architecture_status": ARCHITECTURE_STATUS,
            "irep_version": IREP_VERSION,
            "sprint": 10,
            "sources": sources,
            "rq1_final_package": True,
        },
        "question": {
            "original": question,
            "normalised": " ".join(question.split()),
            "language": "en",
            "priority": payload.get("priority") or "standard",
        },
        "intent": intent,
        "entity": entity,
        "research_objective": {
            "primary_objective": primary_objective,
            "decision_type": intent.get("decision_type"),
            "research_depth": intent.get("research_depth"),
            "expected_deliverable": intent.get("expected_deliverable"),
            "time_horizon": context.get("time_horizon"),
            "raw": {k: roe.get(k) for k in ("objectives", "success_criteria", "constraints") if k in roe},
        },
        "context": context,
        "analyst_plan": analyst_plan,
        "layer_plan": layer_plan,
        "api_plan": api_plan,
        "blueprint": blueprint,
        "validation": validation,
        "execution_plan": execution_plan,
        "quality_targets": quality_targets,
        "success_metrics": success_metrics,
        "research_contract": contract,
    }

    validation_row = validate_package(package)
    package["package_complete"] = validation_row["package_complete"]
    package["package_consistent"] = validation_row["package_consistent"]
    package["validation_detail"] = validation_row
    package["audit"] = build_audit(package, validation_row)

    ms = (time.perf_counter() - t0) * 1000.0
    package["metrics"] = {
        "package_ms": round(ms, 4),
        "sources_count": len(sources),
        "immutable": True,
    }
    package["ok"] = True
    package["not_a_top_level_intelligence_layer"] = True
    package["irep_version"] = IREP_VERSION

    # Soft memory hook
    remember_package(package, outcome="planned")
    return package
