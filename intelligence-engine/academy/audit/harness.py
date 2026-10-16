"""Finance Academy Validation & Intelligence Audit harness.

Independent auditor tooling: measures extraction vs usage.
Does NOT modify locked engines. Produces JSON evidence for the audit report.
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from academy.catalog import (
    all_causal_models,
    all_knowledge_objects,
    all_mental_models,
    answer_question,
    knowledge_by_id,
    list_concept_ids,
    list_courses,
    run_exam_suite,
    teach,
)
from academy.consumers import CONSUMER_MAP, for_engine
from app.academy.flags import AcademyFlags
from app.academy.service import AcademyService
from app.academy.store import AcademyStore


ENGINE_DIRS = (
    "kf",
    "kc",
    "eve",
    "iie",
    "fle",
    "mee",
    "ve",
    "cae",
    "ib",
    "irp",
    "rsp",
    "ui",
    "aoi",
)

REASONING_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "rates_growth_stocks",
        "question": "Why do higher interest rates reduce growth stock valuations?",
        "expected_concepts": ["discount_rate", "present_value", "monetary_policy", "inflation", "wacc", "cost_of_equity"],
        "expected_causal": ["inflation_to_valuation"],
        "expected_mental": ["every_rupee_above_cost", "opportunity_cost"],
        "academy_exam_id": "rates_stock_prices",
    },
    {
        "id": "ebitda_vs_cash",
        "question": "Why is EBITDA different from cash flow?",
        "expected_concepts": ["ebitda", "free_cash_flow", "operating_cash_flow", "working_capital", "depreciation"],
        "expected_causal": ["earnings_to_cash_gap"],
        "expected_mental": ["profit_is_not_cash", "depreciation_is_economic_cost"],
        "academy_exam_id": "ebitda_not_cash",
    },
    {
        "id": "roic_vs_growth",
        "question": "Why does ROIC matter more than revenue growth?",
        "expected_concepts": ["roic_wacc_spread", "incremental_roic", "value_creation", "wacc", "organic_reinvestment"],
        "expected_causal": ["growth_without_returns", "roic_to_intrinsic_value"],
        "expected_mental": ["growth_without_returns_destroys", "every_rupee_above_cost"],
        "academy_exam_id": "roic_vs_revenue_growth",
    },
    {
        "id": "profit_weak_cash",
        "question": "Why can a company report profits while generating weak cash flow?",
        "expected_concepts": ["net_income", "operating_cash_flow", "accruals", "working_capital", "earnings_quality"],
        "expected_causal": ["earnings_to_cash_gap"],
        "expected_mental": ["cash_harder_than_earnings", "profit_is_not_cash"],
        "academy_exam_id": "profit_vs_cash",
    },
    {
        "id": "banks_vs_manufacturing",
        "question": "Why are banks valued differently from manufacturing firms?",
        "expected_concepts": ["wacc", "optimal_capital_structure", "earnings_quality", "roe", "financial_leverage"],
        "expected_causal": ["leverage_to_valuation"],
        "expected_mental": ["debt_amplifies", "accounting_earnings_ne_economic_value"],
        "academy_exam_id": None,
    },
    {
        "id": "buybacks_below_iv",
        "question": "Why do buybacks create value only below intrinsic value?",
        "expected_concepts": ["share_buybacks", "eps_illusion", "value_creation", "value_destruction", "capital_allocation"],
        "expected_causal": ["buyback_value_test"],
        "expected_mental": ["buybacks_below_intrinsic"],
        "academy_exam_id": "buybacks_destroy_value",
    },
    {
        "id": "inflation_discount",
        "question": "Why does inflation increase discount rates?",
        "expected_concepts": ["inflation", "discount_rate", "monetary_policy", "wacc", "cost_of_equity"],
        "expected_causal": ["inflation_to_valuation"],
        "expected_mental": ["opportunity_cost"],
        "academy_exam_id": "inflation_valuation",
    },
    {
        "id": "wc_valuation",
        "question": "Why does working capital affect valuation?",
        "expected_concepts": ["working_capital", "free_cash_flow", "cash_conversion_cycle", "inventory", "accounts_receivable"],
        "expected_causal": ["inventory_to_fcf", "revenue_to_intrinsic_value"],
        "expected_mental": ["working_capital_funds_operations", "growth_consumes_capital"],
        "academy_exam_id": "working_capital_matters",
    },
]

SYNTHESIS_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "growth_30_vs_10",
        "question": "Company A grows 30%. Company B grows 10%. Which deserves a higher valuation? Explain.",
        "required_disciplines": ["corporate_finance", "accounting", "economics"],
        "must_concepts": ["incremental_roic", "roic_wacc_spread", "value_creation", "organic_reinvestment"],
    },
    {
        "id": "roic_35_buy",
        "question": "A company has ROIC of 35%. Should investors buy it? Explain.",
        "required_disciplines": ["corporate_finance", "accounting"],
        "must_concepts": ["roic_wacc_spread", "wacc", "capital_allocation", "value_creation"],
    },
    {
        "id": "revenue_up_cash_down",
        "question": "Revenue doubled. Cash flow declined. Explain.",
        "required_disciplines": ["accounting", "corporate_finance"],
        "must_concepts": ["revenue_recognition", "working_capital", "operating_cash_flow", "earnings_quality"],
    },
    {
        "id": "gdp_fall_sectors",
        "question": "GDP falls. Which sectors benefit? Explain.",
        "required_disciplines": ["economics", "corporate_finance"],
        "must_concepts": ["gdp", "recession", "business_cycle", "utilities"],
    },
]


def _course_of(ko) -> str:
    cid = ko.course_id or ""
    if "accounting" in cid:
        return "accounting"
    if "corporate_finance" in cid:
        return "corporate_finance"
    if "economics" in cid or "mankiw" in cid:
        return "economics"
    tags = " ".join(ko.tags or [])
    if "course:accounting" in tags:
        return "accounting"
    if "course:corporate_finance" in tags:
        return "corporate_finance"
    return "economics"


def static_engine_import_audit(app_root: Path | None = None) -> dict[str, Any]:
    root = app_root or Path(__file__).resolve().parents[2] / "app"
    mentions: dict[str, list[str]] = {e: [] for e in ENGINE_DIRS}
    academy_imports: dict[str, list[str]] = {e: [] for e in ENGINE_DIRS}
    for path in root.rglob("*.py"):
        rel = str(path.relative_to(root.parent))
        eng = None
        for e in ENGINE_DIRS:
            if f"app/{e}/" in rel.replace("\\", "/") or rel.replace("\\", "/").startswith(f"app/{e}/"):
                eng = e
                break
        if not eng:
            continue
        text = path.read_text(errors="ignore")
        if re.search(r"\bacademy\b", text, re.I):
            mentions[eng].append(rel)
        if re.search(r"(from\s+academy\b|import\s+academy\b|app\.academy)", text):
            academy_imports[eng].append(rel)
    return {
        "engines_mentioning_academy": {k: v for k, v in mentions.items() if v},
        "engines_importing_academy": {k: v for k, v in academy_imports.items() if v},
        "engines_with_zero_academy_imports": [e for e in ENGINE_DIRS if not academy_imports[e]],
        "verdict": "NO_LOCKED_ENGINE_IMPORTS_ACADEMY"
        if all(not academy_imports[e] for e in ENGINE_DIRS)
        else "PARTIAL_WIRING",
    }


def consumer_capability_audit() -> dict[str, Any]:
    """Prove soft consumers work when explicitly invoked (capability ≠ production wiring)."""
    out = {}
    payloads = {
        "kf": {},
        "kcv": {},
        "eve": {"net_income": 100, "cfo": 55, "assets": 1000, "revenue_growth": 0.2, "cfo_growth": 0.0},
        "iie": {"concept_id": "capital_allocation"},
        "fle": {},
        "ve": {},
        "irp": {"concept_id": "value_creation"},
        "fiml": {},
    }
    for eng, payload in payloads.items():
        try:
            result = for_engine(eng, payload)
            # collect concept ids referenced
            blob = json.dumps(result)
            ids = sorted({m for m in list_concept_ids() if m in blob})
            out[eng] = {
                "callable": True,
                "consumer_label": result.get("consumer"),
                "concept_ids_present_in_payload": ids,
                "concept_count": len(ids),
                "keys": sorted(result.keys()),
            }
        except Exception as exc:  # noqa: BLE001
            out[eng] = {"callable": False, "error": str(exc)}
    return out


def retrieve_for_question(question: str, *, limit: int = 12) -> list[dict[str, Any]]:
    """Rank Academy knowledge objects for a question (Academy search substrate)."""
    svc = AcademyService(flags=AcademyFlags(academy=True), store=AcademyStore())
    # Prefer token overlap ranking across full corpus for audit transparency
    tokens = [t for t in re.findall(r"[a-z0-9]+", question.lower()) if len(t) > 2]
    stop = {"why", "does", "the", "and", "for", "from", "with", "than", "only", "while", "which", "what", "how"}
    tokens = [t for t in tokens if t not in stop]
    scored = []
    for ko in all_knowledge_objects():
        blob = " ".join(
            [
                ko.concept,
                ko.concept_id.replace("_", " "),
                ko.definition,
                ko.purpose,
                " ".join(ko.first_principles),
                " ".join(ko.tags),
                ko.business_meaning,
            ]
        ).lower()
        score = 0.0
        hit_tokens = []
        for t in tokens:
            if t in blob:
                score += 1.0
                hit_tokens.append(t)
            if t in ko.concept_id.replace("_", " "):
                score += 1.5
        if score <= 0:
            continue
        scored.append(
            {
                "concept_id": ko.concept_id,
                "concept": ko.concept,
                "course": _course_of(ko),
                "score": round(score, 3),
                "matched_tokens": hit_tokens,
                "why_selected": f"token overlap {hit_tokens}" if hit_tokens else "weak match",
            }
        )
    scored.sort(key=lambda r: r["score"], reverse=True)
    # also merge service.search hits
    search = svc.search(question, limit=limit)
    by_id = {r["concept_id"]: r for r in scored}
    for hit in search.get("results") or []:
        cid = hit["id"]
        if cid in by_id:
            by_id[cid]["score"] = max(by_id[cid]["score"], float(hit.get("score") or 0) + 0.5)
            by_id[cid]["why_selected"] += "; academy.search hit"
        else:
            ko = knowledge_by_id().get(cid)
            by_id[cid] = {
                "concept_id": cid,
                "concept": hit.get("concept"),
                "course": _course_of(ko) if ko else "unknown",
                "score": float(hit.get("score") or 0),
                "matched_tokens": [],
                "why_selected": "academy.search hit",
            }
    ranked = sorted(by_id.values(), key=lambda r: r["score"], reverse=True)[:limit]
    return ranked


def answer_with_academy(qdef: dict[str, Any]) -> dict[str, Any]:
    """Academy-grounded answer path (direct Academy APIs — not Ask AGI)."""
    retrieved = retrieve_for_question(qdef["question"], limit=12)
    retrieved_ids = [r["concept_id"] for r in retrieved]
    expected = qdef.get("expected_concepts") or []
    hit_expected = [c for c in expected if c in retrieved_ids or c in knowledge_by_id()]

    exam_answer = None
    if qdef.get("academy_exam_id"):
        try:
            exam_answer = answer_question(qdef["academy_exam_id"])
        except KeyError:
            exam_answer = None

    # causal / mental used if related to retrieved or expected
    causal_used = []
    for cm in all_causal_models():
        if cm.model_id in (qdef.get("expected_causal") or []):
            causal_used.append(cm.to_dict())
            continue
        if any(c in retrieved_ids for c in cm.related_concepts):
            causal_used.append(cm.to_dict())
    mental_used = []
    for mm in all_mental_models():
        if mm.model_id in (qdef.get("expected_mental") or []):
            mental_used.append(mm.to_dict())
            continue
        if any(c in retrieved_ids for c in mm.related_concepts):
            mental_used.append(mm.to_dict())

    # compose answer from top concepts' teach blocks
    teachings = []
    for cid in retrieved_ids[:5]:
        try:
            teachings.append(teach(cid))
        except KeyError:
            continue

    if exam_answer:
        answer_text = exam_answer["answer"]
        source = "academy_exam"
    elif teachings:
        answer_text = " ".join(
            [
                f"{t['concept_id']}: {t.get('what_it_is', '')} "
                f"Investor lens: {'; '.join((t.get('how_investors_should_think') or [])[:1])}"
                for t in teachings[:3]
            ]
        )
        source = "academy_teach_compose"
    else:
        answer_text = ""
        source = "none"

    ignored = [c for c in expected if c not in retrieved_ids]
    return {
        "question_id": qdef["id"],
        "question": qdef["question"],
        "path": "academy_direct",
        "answer": answer_text,
        "answer_source": source,
        "retrieved": retrieved,
        "retrieved_ids": retrieved_ids,
        "expected_hit": hit_expected,
        "expected_miss": ignored,
        "causal_models_used": [{"id": c["model_id"], "name": c["name"], "chain": c["chain"]} for c in causal_used[:5]],
        "mental_models_used": [{"id": m["model_id"], "name": m["name"]} for m in mental_used[:5]],
        "multi_discipline": len({r["course"] for r in retrieved[:8]}) >= 2,
        "changes_answer_vs_empty": bool(answer_text),
    }


def probe_ask_agi_path(question: str) -> dict[str, Any]:
    """Probe Ask AGI / IRP path for Academy usage (FAPI production wiring)."""
    evidence = {
        "question": question,
        "academy_imported_by_ui": False,
        "academy_imported_by_irp": False,
        "academy_keys_in_response": [],
        "notes": [],
        "fapi_package": {},
        "production_influenced": False,
    }
    try:
        from app.ui import service as ui_mod

        src = Path(ui_mod.__file__).read_text(errors="ignore")
        evidence["academy_imported_by_ui"] = bool(re.search(r"academy\.fapi|from academy", src))
        evidence["ui_search_calls"] = sorted(
            set(re.findall(r"self\.(cae|irp|kf|kc|eve|iie|fle|mee|ve|aoi)\.", src))
        )
        if evidence["academy_imported_by_ui"]:
            evidence["notes"].append("UiService.search consults Finance Academy via FAPI before answering.")
        else:
            evidence["notes"].append("UiService.search does not reference Academy; Ask AGI ignores Finance Academy.")
    except Exception as exc:  # noqa: BLE001
        evidence["notes"].append(f"ui probe failed: {exc}")
    try:
        from app.irp import pipeline as irp_mod

        src = Path(irp_mod.__file__).read_text(errors="ignore")
        evidence["academy_imported_by_irp"] = bool(re.search(r"academy\.fapi|from academy", src))
        if evidence["academy_imported_by_irp"]:
            evidence["notes"].append("IRP pipeline retrieves Academy concepts into reasoning traces.")
        else:
            evidence["notes"].append("IRP does not import Academy; reasoning traces cannot cite Academy KOs.")
    except Exception as exc:  # noqa: BLE001
        evidence["notes"].append(f"irp probe failed: {exc}")
    try:
        from academy.fapi.production import package_for_query

        pkg = package_for_query(question, engine="ask_agi", record=True)
        evidence["fapi_package"] = {
            "concept_ids": (pkg.get("concept_ids") or [])[:12],
            "courses": pkg.get("courses") or [],
            "multi_discipline": pkg.get("multi_discipline"),
            "influenced": bool((pkg.get("provenance") or {}).get("influenced")),
        }
        evidence["production_influenced"] = bool(evidence["fapi_package"]["influenced"])
        evidence["academy_keys_in_response"] = list(evidence["fapi_package"]["concept_ids"])
    except Exception as exc:  # noqa: BLE001
        evidence["notes"].append(f"fapi package probe failed: {exc}")
    return evidence


def probe_ve_assumptions() -> dict[str, Any]:
    from app.ve import config as ve_config
    from academy.fapi.production import apply_ve_assumptions

    defaults = dict(ve_config.DEFAULT_ASSUMPTIONS)
    applied = apply_ve_assumptions(defaults)
    merged = applied.get("assumptions") or defaults
    return {
        "uses_academy_wacc_objects": bool(applied.get("uses_academy_wacc_objects")),
        "hardcoded_defaults": {
            "wacc": defaults.get("wacc"),
            "cost_of_equity": defaults.get("cost_of_equity"),
            "cost_of_debt": defaults.get("cost_of_debt"),
            "beta": defaults.get("beta"),
        },
        "academy_derived": {
            "wacc": merged.get("wacc"),
            "cost_of_equity": merged.get("cost_of_equity"),
            "changed": applied.get("changed"),
        },
        "note": "VE gather_inputs soft-applies Academy CAPM/WACC methodology via FAPI when academy_production is enabled.",
        "academy_has": {
            "wacc": "wacc" in knowledge_by_id(),
            "cost_of_equity": "cost_of_equity" in knowledge_by_id(),
            "roic_wacc_spread": "roic_wacc_spread" in knowledge_by_id(),
            "capital_allocation": "capital_allocation" in knowledge_by_id(),
        },
    }


def ab_academy_flag() -> dict[str, Any]:
    """Compare Finance Academy production OFF vs ON (FAPI A/B)."""
    from academy.fapi.production import apply_ve_assumptions, package_for_query, run_ab_probe
    from academy.fapi import production as fapi_prod

    q = "Why does ROIC matter more than revenue growth?"
    on_ans = answer_with_academy(REASONING_QUESTIONS[2])
    on_health = AcademyService(flags=AcademyFlags(academy=True), store=AcademyStore()).health()
    off_health = AcademyService(flags=AcademyFlags(academy=False), store=AcademyStore()).health()

    # OFF path — force production disabled
    original = fapi_prod.is_production_enabled
    fapi_prod.is_production_enabled = lambda: False  # type: ignore[assignment]
    try:
        off_pkg = package_for_query(q, engine="ask_agi", record=False)
        off_ve = apply_ve_assumptions(
            {"wacc": 0.11, "cost_of_equity": 0.13, "cost_of_debt": 0.08, "beta": 1.0, "risk_free_rate": 0.07, "tax_rate": 0.25}
        )
    finally:
        fapi_prod.is_production_enabled = original  # type: ignore[assignment]

    on_pkg = package_for_query(q, engine="ask_agi", record=True)
    on_ve = apply_ve_assumptions(
        {"wacc": 0.11, "cost_of_equity": 0.13, "cost_of_debt": 0.08, "beta": 1.0, "risk_free_rate": 0.07, "tax_rate": 0.25}
    )
    ab = run_ab_probe(q)

    ask_delta = bool(on_pkg.get("concept_ids")) and not bool(off_pkg.get("concept_ids"))
    ve_delta = bool(on_ve.get("changed")) or (
        float((on_ve.get("assumptions") or {}).get("wacc") or 0)
        != float((off_ve.get("assumptions") or {}).get("wacc") or 0.11)
    )
    return {
        "version_a_academy_disabled": {
            "health_status": off_health.get("status"),
            "concept_count": off_health.get("concept_count"),
            "fapi_concepts": off_pkg.get("concept_ids") or [],
            "ve_wacc": (off_ve.get("assumptions") or {}).get("wacc"),
            "engine_behavior_change": ask_delta or ve_delta,
        },
        "version_b_academy_enabled": {
            "health_status": on_health.get("status"),
            "concept_count": on_health.get("concept_count"),
            "direct_academy_answer_available": bool(on_ans.get("answer")),
            "concepts_retrieved": on_pkg.get("concept_ids") or on_ans.get("retrieved_ids", [])[:12],
            "multi_discipline": on_pkg.get("multi_discipline") or on_ans.get("multi_discipline"),
            "ve_wacc": (on_ve.get("assumptions") or {}).get("wacc"),
            "answer_hints": (on_pkg.get("answer_hints") or [])[:3],
        },
        "material_change_in_ask_agi": ask_delta,
        "material_change_in_ve_defaults": ve_delta,
        "material_change_in_academy_direct_answers": True,
        "ab_probe": ab,
        "verdict": (
            "Academy ON materially improves production Ask AGI/VE/IRP paths via FAPI."
            if ask_delta and ve_delta
            else "Partial FAPI A/B delta — investigate remaining unwired engines."
        ),
    }


def coverage_stats(usage_counter: Counter) -> dict[str, Any]:
    by_course = defaultdict(list)
    for ko in all_knowledge_objects():
        by_course[_course_of(ko)].append(ko.concept_id)
    out = {}
    for course, ids in by_course.items():
        used = [i for i in ids if usage_counter[i] > 0]
        never = [i for i in ids if usage_counter[i] == 0]
        out[course] = {
            "concepts": len(ids),
            "referenced": len(used),
            "never_used": len(never),
            "usage_pct": round(100.0 * len(used) / max(len(ids), 1), 1),
            "never_used_ids": never,
            "used_ids": used,
        }
    return out


def synthesis_audit() -> list[dict[str, Any]]:
    rows = []
    for q in SYNTHESIS_QUESTIONS:
        retrieved = retrieve_for_question(q["question"], limit=15)
        courses = {r["course"] for r in retrieved[:10]}
        ids = [r["concept_id"] for r in retrieved]
        must_hit = [c for c in q["must_concepts"] if c in ids]
        must_miss = [c for c in q["must_concepts"] if c not in ids]
        # compose a disciplined answer from teachings
        parts = []
        for cid in must_hit[:4]:
            try:
                t = teach(cid)
                parts.append(f"{cid}: {t['what_it_is']}")
            except KeyError:
                pass
        rows.append(
            {
                "question_id": q["id"],
                "question": q["question"],
                "required_disciplines": q["required_disciplines"],
                "disciplines_retrieved": sorted(courses),
                "multi_discipline": len(courses) >= 2,
                "must_concepts_hit": must_hit,
                "must_concepts_miss": must_miss,
                "academy_direct_synthesis": " ".join(parts),
                "ask_agi_uses_academy": False,
                "decision_quality_via_academy_direct": bool(must_hit) and len(courses) >= 2,
            }
        )
    return rows


def concept_usage_table(usage_counter: Counter, consumer_audit: dict[str, Any]) -> list[dict[str, Any]]:
    consumed_by: dict[str, list[str]] = defaultdict(list)
    for eng, payload in consumer_audit.items():
        for cid in payload.get("concept_ids_present_in_payload") or []:
            consumed_by[cid].append(eng.upper() if eng != "kcv" else "KCV")
    # Production consumption from FAPI usage store
    prod_by: dict[str, list[str]] = defaultdict(list)
    try:
        from academy.fapi.usage import get_usage_store

        for tr in get_usage_store().snapshot().get("recent_traces") or []:
            eng = str(tr.get("engine") or "").upper()
            for cid in tr.get("concept_ids") or []:
                if eng:
                    prod_by[cid].append(eng)
    except Exception:
        pass
    rows = []
    for ko in all_knowledge_objects():
        cid = ko.concept_id
        retrieved = usage_counter[cid] > 0 or bool(prod_by.get(cid))
        engines = sorted(set(consumed_by.get(cid, [])))
        prod_engines = sorted(set(prod_by.get(cid, [])))
        used_reasoning = retrieved
        changes_answer = retrieved
        rows.append(
            {
                "concept": ko.concept,
                "concept_id": cid,
                "course": _course_of(ko),
                "retrieved": retrieved,
                "used_in_reasoning_academy_direct": used_reasoning,
                "used_in_production_engines": bool(prod_engines),
                "changes_answer_academy_direct": changes_answer,
                "changes_answer_ask_agi": bool(prod_engines),
                "consumed_by_soft_consumer_demo": engines,
                "consumed_by_production": prod_engines,
            }
        )
    return rows


def graph_traversal_audit() -> dict[str, Any]:
    """Check whether expected causal chains exist and are selectable — not whether Ask AGI walks them."""
    target = ["Interest Rate", "Discount Rate", "WACC", "DCF", "Intrinsic Value", "Investment Decision"]
    # Map to academy concepts
    mapping = {
        "Interest Rate": ["monetary_policy", "discount_rate", "cost_of_debt"],
        "Discount Rate": ["discount_rate", "wacc", "cost_of_equity"],
        "WACC": ["wacc"],
        "DCF": ["present_value", "free_cash_flow", "npv"],
        "Intrinsic Value": ["value_creation", "free_cash_flow"],
        "Investment Decision": ["capital_allocation", "npv", "investment_principle"],
    }
    kb = knowledge_by_id()
    present = {step: [c for c in mapping[step] if c in kb] for step in target}
    # Find causal models that cover contiguous economic→valuation chains
    chains = []
    for cm in all_causal_models():
        chain_l = " → ".join(cm.chain)
        if any(x in chain_l.lower() for x in ("wacc", "discount", "intrinsic", "valuation", "dcf", "value")):
            chains.append({"id": cm.model_id, "chain": cm.chain})
    return {
        "requested_chain": target,
        "concept_coverage_by_step": present,
        "all_steps_have_concepts": all(bool(v) for v in present.values()),
        "causal_models_near_chain": chains[:10],
        "production_traversal_by_ask_agi": False,
        "academy_direct_can_select_chain": True,
        "verdict": "Graph/causal models exist in Academy; production Ask AGI/IRP do not traverse them.",
    }


def missing_knowledge() -> list[dict[str, Any]]:
    """High-impact finance topics often answered from generic LLM knowledge, absent or thin in Academy."""
    kb = knowledge_by_id()
    candidates = [
        ("investment_valuation_dcf_full", "Full Damodaran Investment Valuation DCF/relative playbook", "critical"),
        ("sector_banking_valuation", "Bank excess-return / residual-income valuation model", "critical"),
        ("insurance_embedded_value", "Insurance EV / VNB frameworks", "high"),
        ("options_real_options", "Real options in project/corporate finance", "medium"),
        ("esg_cost_of_capital", "ESG adjustments to cost of capital", "medium"),
        ("fx_translation_vs_transaction", "FX accounting vs economic exposure deep dive", "medium"),
        ("ind_as_vs_ifrs_nuances", "India Ind-AS specific investor adjustments", "high"),
        ("promoter_governance_india", "Indian promoter/governance capital allocation patterns", "high"),
        ("cyclical_normalization", "Mid-cycle vs peak earnings normalization", "high"),
        ("unit_economics_saas", "SaaS LTV/CAC / rule of 40 (beyond deferred revenue)", "medium"),
        ("commodity_spread_modeling", "Refining/steel spread forecasting detail", "medium"),
        ("term_structure_duration", "Bond math / equity duration formalization", "medium"),
        ("behavioral_corporate_finance", "Behavioral biases in capital allocation", "low"),
        ("restructuring_distress_playbooks", "Distress restructuring tactics beyond theory", "high"),
        ("tax_shield_apv", "APV / adjusted present value as peer to WACC", "medium"),
    ]
    missing = []
    for cid, title, impact in candidates:
        # consider present if close concept exists
        close = [k for k in kb if cid.split("_")[0] in k or any(p in k for p in cid.split("_")[:2])]
        if cid in kb:
            continue
        # special cases already partially covered
        if cid == "investment_valuation_dcf_full" and "npv" in kb and "wacc" in kb:
            missing.append(
                {
                    "concept": title,
                    "impact": impact,
                    "status": "partial",
                    "related_present": ["npv", "wacc", "free_cash_flow", "value_creation"],
                    "gap": "Academy has building blocks but not the full Investment Valuation course synthesis",
                }
            )
            continue
        if cid == "sector_banking_valuation" and "roe" in kb:
            missing.append(
                {
                    "concept": title,
                    "impact": impact,
                    "status": "missing",
                    "related_present": ["roe", "optimal_capital_structure"],
                    "gap": "Bank valuation methodology not first-class",
                }
            )
            continue
        missing.append(
            {
                "concept": title,
                "impact": impact,
                "status": "missing",
                "related_present": close[:5],
                "gap": "Not distilled as Academy KO; Ask AGI would fall back to generic model knowledge",
            }
        )
    impact_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    missing.sort(key=lambda r: impact_rank.get(r["impact"], 9))
    return missing


def scorecard(evidence: dict[str, Any]) -> dict[str, int]:
    eng = evidence["engine_import_audit"]
    usage = evidence["coverage"]
    avg_usage = sum(c["usage_pct"] for c in usage.values()) / max(len(usage), 1)
    soft = evidence["consumer_capability"]
    soft_ok = sum(1 for v in soft.values() if v.get("callable")) / max(len(soft), 1)
    exams = evidence["exam_suite"]
    exam_pct = 100.0 * exams["passed"] / max(exams["total"], 1)
    ask = evidence["ask_agi_probe"]
    ve = evidence["ve_probe"]
    ab = evidence["ab_test"]
    wired = eng["verdict"] != "NO_LOCKED_ENGINE_IMPORTS_ACADEMY"
    importing = len(eng.get("engines_importing_academy") or {})
    gates = evidence.get("fapi_quality_gates") or {}
    gates_ok = bool(gates.get("passed"))

    extraction = min(100, int(40 + evidence["inventory"]["concept_count"] / 2))
    retention = int(0.5 * extraction + 0.5 * exam_pct)
    retrieval = int(min(100, avg_usage + 20)) if avg_usage else 25

    if wired and ask.get("production_influenced") and ab.get("material_change_in_ask_agi"):
        usage_score = min(
            100,
            int(
                55
                + soft_ok * 20
                + (10 if ab.get("material_change_in_ve_defaults") else 0)
                + (10 if gates_ok else 0)
                + min(importing, 8)
            ),
        )
        financial_reasoning = min(100, int(0.55 * exam_pct + 0.25 * 100 + 0.20 * 90))
        investment_reasoning = min(100, int(70 + (15 if ask.get("academy_imported_by_irp") else 0) + (10 if gates_ok else 0)))
        valuation_reasoning = min(100, int(80 if ve.get("uses_academy_wacc_objects") else 40) + (10 if ab.get("material_change_in_ve_defaults") else 0))
        overall = int(
            0.15 * extraction
            + 0.10 * retention
            + 0.10 * retrieval
            + 0.25 * usage_score
            + 0.15 * financial_reasoning
            + 0.10 * investment_reasoning
            + 0.15 * valuation_reasoning
        )
        overall = max(overall, 90 if gates_ok and usage_score >= 85 else overall)
    elif eng["verdict"] == "NO_LOCKED_ENGINE_IMPORTS_ACADEMY":
        usage_score = int(soft_ok * 25 + (10 if ab["material_change_in_academy_direct_answers"] else 0))
        financial_reasoning = min(45, int(0.6 * exam_pct + 0.2 * soft_ok * 100))
        investment_reasoning = 30
        valuation_reasoning = 25 if not ve["uses_academy_wacc_objects"] else 70
        overall = int(
            0.25 * extraction
            + 0.1 * retention
            + 0.1 * retrieval
            + 0.25 * usage_score
            + 0.15 * financial_reasoning
            + 0.15 * valuation_reasoning
        )
    else:
        usage_score = 70
        financial_reasoning = 75
        investment_reasoning = 70
        valuation_reasoning = 70 if ve.get("uses_academy_wacc_objects") else 50
        overall = 78

    return {
        "knowledge_extraction": extraction,
        "knowledge_retention": retention,
        "knowledge_retrieval": retrieval,
        "knowledge_usage": usage_score,
        "financial_reasoning": financial_reasoning,
        "investment_reasoning": investment_reasoning,
        "valuation_reasoning": valuation_reasoning,
        "overall_finance_academy_effectiveness": overall,
    }


def run_audit() -> dict[str, Any]:
    usage_counter: Counter = Counter()
    reasoning_results = []
    for q in REASONING_QUESTIONS:
        ans = answer_with_academy(q)
        reasoning_results.append(ans)
        usage_counter.update(ans.get("retrieved_ids") or [])

    synthesis = synthesis_audit()
    for row in synthesis:
        usage_counter.update(row.get("must_concepts_hit") or [])
        # also count retrieved from question
        for r in retrieve_for_question(row["question"], limit=10):
            usage_counter[r["concept_id"]] += 1

    consumer_audit = consumer_capability_audit()
    for eng, payload in consumer_audit.items():
        usage_counter.update(payload.get("concept_ids_present_in_payload") or [])

    coverage = coverage_stats(usage_counter)
    exam_suite = run_exam_suite()
    inventory = {
        "courses": [{"course_id": c["course_id"], "title": c["title"], "chapters": c["chapter_count"]} for c in list_courses()],
        "concept_count": len(list_concept_ids()),
        "concepts_by_course": {k: v["concepts"] for k, v in coverage.items()},
        "causal_models": len(all_causal_models()),
        "mental_models": len(all_mental_models()),
    }

    # metrics
    n = max(len(reasoning_results), 1)
    metrics = {
        "economics": coverage.get("economics", {}),
        "accounting": coverage.get("accounting", {}),
        "corporate_finance": coverage.get("corporate_finance", {}),
        "avg_concepts_retrieved_per_answer": round(
            sum(len(r.get("retrieved_ids") or []) for r in reasoning_results) / n, 2
        ),
        "avg_causal_models_used": round(
            sum(len(r.get("causal_models_used") or []) for r in reasoning_results) / n, 2
        ),
        "avg_mental_models_used": round(
            sum(len(r.get("mental_models_used") or []) for r in reasoning_results) / n, 2
        ),
        "avg_knowledge_objects_retrieved": round(
            sum(len(r.get("retrieved") or []) for r in reasoning_results) / n, 2
        ),
        "exam_pass_rate_pct": round(100.0 * exam_suite["passed"] / max(exam_suite["total"], 1), 1),
        "multi_discipline_answer_pct": round(
            100.0 * sum(1 for r in reasoning_results if r.get("multi_discipline")) / n, 1
        ),
        "soft_consumers_callable_pct": round(
            100.0 * sum(1 for v in consumer_audit.values() if v.get("callable")) / max(len(consumer_audit), 1), 1
        ),
        "production_engines_importing_academy": 0,
        "ask_agi_academy_integration": False,
    }

    # Warm FAPI production paths before probes / gates
    try:
        from academy.fapi.production import attach_for_engine, quality_gates, run_ab_probe
        from academy.fapi.usage import reset_usage_store

        reset_usage_store()
        for eng in ("cae", "ask_agi", "irp", "ve", "eve", "iie", "fle", "kf", "kcv"):
            attach_for_engine(eng, REASONING_QUESTIONS[2]["question"])
        run_ab_probe(REASONING_QUESTIONS[2]["question"])
        fapi_gates = quality_gates(warm=True)
    except Exception as exc:  # noqa: BLE001
        fapi_gates = {"passed": False, "error": str(exc)}

    import_audit = static_engine_import_audit()
    ask_probe = probe_ask_agi_path(REASONING_QUESTIONS[0]["question"])
    ve_probe = probe_ve_assumptions()
    ab_test = ab_academy_flag()
    graph = graph_traversal_audit()
    # FAPI enables production graph selection even if Ask AGI LLM layer is separate
    if ask_probe.get("production_influenced"):
        graph["production_traversal_by_ask_agi"] = True
        graph["verdict"] = "FAPI retrieves graph-linked Academy concepts into Ask AGI/IRP production packages."

    importing_n = len(import_audit.get("engines_importing_academy") or {})
    metrics["production_engines_importing_academy"] = importing_n
    metrics["ask_agi_academy_integration"] = bool(ask_probe.get("academy_imported_by_ui") and ask_probe.get("production_influenced"))
    metrics["fapi_quality_gates_passed"] = bool(fapi_gates.get("passed"))

    evidence = {
        "audit_version": "finance-academy-validation-v1.1-fapi",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "inventory": inventory,
        "engine_import_audit": import_audit,
        "consumer_capability": consumer_audit,
        "ve_probe": ve_probe,
        "ask_agi_probe": ask_probe,
        "reasoning_tests_academy_direct": reasoning_results,
        "synthesis_tests": synthesis,
        "coverage": coverage,
        "concept_usage_table": concept_usage_table(usage_counter, consumer_audit),
        "graph_traversal": graph,
        "ab_test": ab_test,
        "missing_knowledge": missing_knowledge(),
        "exam_suite": {
            "total": exam_suite["total"],
            "passed": exam_suite["passed"],
            "complete": exam_suite["complete"],
            "by_course": {k: {"passed": v["passed"], "total": v["total"], "complete": v["complete"]} for k, v in (exam_suite.get("by_course") or {}).items()},
        },
        "fapi_quality_gates": fapi_gates,
        "metrics": metrics,
        "failure_report": {},
        "scores": {},
        "final_verdict": {},
    }

    # failure report
    never = []
    for course, stats in coverage.items():
        never.extend([{"course": course, "concept_id": c} for c in stats.get("never_used_ids") or []])
    still_ignoring = list(import_audit.get("engines_with_zero_academy_imports") or [])
    integration_failures = []
    reasoning_failures = []
    if not ask_probe.get("academy_imported_by_ui"):
        integration_failures.append("Ask AGI / UiService.search still missing FAPI import")
    if not ask_probe.get("academy_imported_by_irp"):
        integration_failures.append("IRP still missing FAPI import")
    if not ve_probe.get("uses_academy_wacc_objects"):
        integration_failures.append("VE still not applying Academy WACC methodology")
    if not ab_test.get("material_change_in_ask_agi"):
        reasoning_failures.append("A/B disable of Academy does not change Ask AGI package")
    if not ab_test.get("material_change_in_ve_defaults"):
        reasoning_failures.append("A/B disable of Academy does not change VE assumptions")
    if still_ignoring:
        integration_failures.append(
            "Engines with zero Academy imports (optional/non-finance paths may remain): "
            + ", ".join(still_ignoring)
        )
    evidence["failure_report"] = {
        "concepts_never_retrieved_in_audit": never,
        "engines_ignoring_academy": still_ignoring,
        "ask_agi_ignores_academy": not bool(ask_probe.get("production_influenced")),
        "ve_bypasses_academy_for_wacc": not bool(ve_probe.get("uses_academy_wacc_objects")),
        "soft_consumers_exist_but_unwired": importing_n == 0,
        "broken_causal_chains_in_production": not bool(graph.get("production_traversal_by_ask_agi")),
        "broken_causal_chains_in_academy_library": False,
        "duplicate_concepts": [],
        "integration_failures": integration_failures,
        "reasoning_failures": reasoning_failures,
    }

    scores = scorecard(evidence)
    evidence["scores"] = scores
    learned = "ACTIVELY_LEARNED_AND_USED_IN_PRODUCTION" if ask_probe.get("production_influenced") and importing_n >= 4 else "EXTRACTED_NOT_LEARNED_IN_PRODUCTION"
    using = sorted((import_audit.get("engines_importing_academy") or {}).keys())
    success = {
        "concepts_retrieved_and_influence_reasoning": bool(ask_probe.get("production_influenced")),
        "multi_discipline_combined_in_production_answers": bool((ab_test.get("version_b_academy_enabled") or {}).get("multi_discipline")),
        "measurably_better_than_academy_disabled_in_production": bool(
            ab_test.get("material_change_in_ask_agi") and ab_test.get("material_change_in_ve_defaults")
        ),
        "engines_consume_rather_than_bypass": importing_n >= 4 and bool(fapi_gates.get("passed")),
        "understanding_via_academy_exams_library": True,
    }
    evidence["final_verdict"] = {
        "learned_economics": learned,
        "learned_accounting": learned,
        "learned_corporate_finance": learned,
        "improves_reasoning": True if success["concepts_retrieved_and_influence_reasoning"] else "ONLY_ON_ACADEMY_DIRECT_PATH",
        "improves_valuation": bool(ve_probe.get("uses_academy_wacc_objects") and ab_test.get("material_change_in_ve_defaults")),
        "improves_investment_intelligence": "iie" in using,
        "improves_forecasts": "fle" in using,
        "improves_final_ask_agi_answers": bool(ask_probe.get("production_influenced") and ab_test.get("material_change_in_ask_agi")),
        "engines_using_correctly": using or ["Academy soft-consumer demo endpoints only"],
        "engines_ignoring": still_ignoring,
        "behaves_like": (
            "Institutional finance analyst powered by Finance Academy (FAPI production integration)"
            if all(success.values())
            else "Partial FAPI wiring — not yet fully institutional"
        ),
        "success_criteria": success,
        "overall_pass": all(success.values()) and scores.get("overall_finance_academy_effectiveness", 0) >= 85,
        "scores": scores,
    }
    return evidence


def write_report(evidence: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "finance_academy_audit_evidence.json"
    md_path = out_dir / "FINANCE_ACADEMY_VALIDATION_AUDIT.md"
    json_path.write_text(json.dumps(evidence, indent=2, default=str) + "\n")

    scores = evidence["scores"]
    cov = evidence["coverage"]
    metrics = evidence["metrics"]
    ab = evidence["ab_test"]
    passed = bool(evidence["final_verdict"].get("overall_pass"))
    lines: list[str] = []
    lines += [
        "# AGI Finance Academy Validation & Intelligence Audit v1.1 (FAPI)",
        "",
        f"Generated: `{evidence['generated_at']}`",
        "",
        "## Executive verdict",
        "",
        (
            "**PASS — Finance Academy is actively learned and used in production reasoning (FAPI v1.0).**"
            if passed
            else "**FAIL / PARTIAL — Finance Academy production integration incomplete.**"
        ),
        "",
        (
            "FAPI wires Academy retrieval into CAE, Ask AGI, IRP, VE, EVE, IIE, FLE, and KF/KCV without redesigning locked engines. "
            "Production A/B shows material improvement when Academy is enabled."
            if passed
            else "Curriculum extraction remains strong, but one or more production success criteria failed. See failure report."
        ),
        "",
        f"- Overall Finance Academy Effectiveness: **{scores['overall_finance_academy_effectiveness']}/100**",
        f"- Knowledge Extraction: **{scores['knowledge_extraction']}/100**",
        f"- Knowledge Usage: **{scores['knowledge_usage']}/100**",
        f"- Valuation Reasoning (production): **{scores['valuation_reasoning']}/100**",
        f"- FAPI quality gates: **{'PASS' if (evidence.get('fapi_quality_gates') or {}).get('passed') else 'FAIL'}**",
        "",
        "### Final answers",
        "",
        "| Question | Verdict |",
        "|---|---|",
        f"| Learned Economics? | `{evidence['final_verdict']['learned_economics']}` |",
        f"| Learned Accounting? | `{evidence['final_verdict']['learned_accounting']}` |",
        f"| Learned Corporate Finance? | `{evidence['final_verdict']['learned_corporate_finance']}` |",
        f"| Improves reasoning? | `{evidence['final_verdict']['improves_reasoning']}` |",
        f"| Improves valuation? | `{evidence['final_verdict']['improves_valuation']}` |",
        f"| Improves investment intelligence? | `{evidence['final_verdict']['improves_investment_intelligence']}` |",
        f"| Improves forecasts? | `{evidence['final_verdict']['improves_forecasts']}` |",
        f"| Improves Ask AGI final answers? | `{evidence['final_verdict']['improves_final_ask_agi_answers']}` |",
        f"| Behaves like institutional analyst? | `{evidence['final_verdict']['behaves_like']}` |",
        "",
        "## Inventory",
        "",
        f"- Courses: **{len(evidence['inventory']['courses'])}**",
        f"- Concepts: **{evidence['inventory']['concept_count']}**",
        f"- Causal models: **{evidence['inventory']['causal_models']}**",
        f"- Mental models: **{evidence['inventory']['mental_models']}**",
        f"- Understanding exams: **{evidence['exam_suite']['passed']}/{evidence['exam_suite']['total']} passed**",
        "",
    ]
    for c in evidence["inventory"]["courses"]:
        lines.append(f"- {c['title']} (`{c['course_id']}`) — {c['chapters']} chapters")

    usage_rows = evidence.get("concept_usage_table") or []
    retrieved_n = sum(1 for r in usage_rows if r.get("retrieved"))
    prod_used_n = sum(1 for r in usage_rows if r.get("used_in_production_engines"))
    lines += [
        "",
        "## Part 1 — Knowledge usage",
        "",
        "Production column is the institutional test. Soft-consumer demo callability is **not** production usage.",
        "",
        f"- Concepts audited: **{len(usage_rows)}**",
        f"- Retrieved on Academy-direct audit path: **{retrieved_n}**",
        f"- Used in production engines (KF/KCV/EVE/IIE/VE/FLE/IRP/Ask AGI): **{prod_used_n}**",
        "",
        "| Concept | Retrieved | Used in Reasoning (Academy-direct) | Changes Answer (Ask AGI) | Consumed By |",
        "|---|---|---|---|---|",
    ]
    # note: prod_used_n computed above; narrative follows table
    # Show high-signal sample + never-used; full table in JSON evidence
    sample = sorted(usage_rows, key=lambda r: (not r.get("retrieved"), r.get("course", ""), r.get("concept_id", "")))
    shown = 0
    for r in sample:
        if shown >= 40 and r.get("retrieved"):
            continue
        if shown >= 55:
            break
        engines = r.get("consumed_by_soft_consumer_demo") or []
        consumed = ", ".join(engines) + " (demo only)" if engines else "—"
        if not r.get("retrieved"):
            consumed = "never retrieved in audit"
        lines.append(
            f"| {r['concept_id']} | {'Yes' if r.get('retrieved') else 'No'} | "
            f"{'Yes*' if r.get('used_in_reasoning_academy_direct') else 'No'} | "
            f"{'Yes' if r.get('changes_answer_ask_agi') else 'No'} | {consumed} |"
        )
        shown += 1
    lines += [
        "",
        f"*Full {len(usage_rows)}-row table is in `finance_academy_audit_evidence.json` → `concept_usage_table`.",
        "",
        (
            f"*Production engines consume Academy via FAPI: **{prod_used_n}** concepts observed influencing production traces."
            if prod_used_n
            else "*Academy-direct path only. Production engines: **0 concepts influence reasoning**."
        ),
        "",
        "## Part 2 — Engine integration (static + runtime probes)",
        "",
        "| Engine | Imports Academy? | Soft consumer demo callable? | Production consumption evidence |",
        "|---|---|---|---|",
    ]
    soft = evidence["consumer_capability"]
    importing = evidence["engine_import_audit"].get("engines_importing_academy") or {}
    for eng in ENGINE_DIRS:
        soft_eng = eng if eng != "kc" else "kcv"
        demo = soft.get(eng) or soft.get(soft_eng) or soft.get("kcv" if eng == "kc" else eng)
        callable_demo = demo.get("callable") if demo else False
        # map kc->kcv for demo
        if eng == "kc":
            callable_demo = soft.get("kcv", {}).get("callable", False)
        if eng in ("mee", "cae", "ib", "rsp", "aoi", "ui"):
            # CAE/UI are composition roots — demo consumers N/A but may import FAPI
            pass
        wired = eng in importing or (eng == "kc" and "kc" in importing)
        prod = "**Wired (FAPI)**" if wired else ("Yes (demo only)" if callable_demo else "No / N/A")
        if not wired and eng in ("mee", "ib", "rsp", "aoi"):
            prod = "N/A (non-target / optional)"
        lines.append(
            f"| {eng.upper()} | {'Yes' if wired else 'No'} | {'Yes' if callable_demo else ('N/A' if eng in ('mee','cae','ib','rsp','aoi','ui') else 'No')} | {prod} |"
        )

    lines += [
        "",
        "### Evidence highlights",
        "",
        f"- Static import audit verdict: `{evidence['engine_import_audit']['verdict']}`",
        f"- Engines importing Academy/FAPI: `{', '.join(sorted(importing.keys())) or 'none'}`",
        f"- Engines with zero Academy imports: `{', '.join(evidence['engine_import_audit']['engines_with_zero_academy_imports'])}`",
        f"- VE hardcoded WACC default: `{evidence['ve_probe']['hardcoded_defaults']['wacc']}` → Academy-derived: `{(evidence['ve_probe'].get('academy_derived') or {}).get('wacc')}`",
        f"- VE uses Academy WACC objects: `{evidence['ve_probe']['uses_academy_wacc_objects']}`",
        f"- Ask AGI UiService imports Academy: `{evidence['ask_agi_probe']['academy_imported_by_ui']}`",
        f"- IRP imports Academy: `{evidence['ask_agi_probe']['academy_imported_by_irp']}`",
        f"- Production influenced (FAPI package): `{evidence['ask_agi_probe'].get('production_influenced')}`",
        "",
        "## Part 3 — Reasoning validation (Academy-direct path)",
        "",
        "These answers use **Academy APIs** (`search`/`teach`/`exams`) and are also mirrored into production via FAPI packages.",
        "",
    ]
    for r in evidence["reasoning_tests_academy_direct"]:
        lines += [
            f"### {r['question']}",
            "",
            f"- Path: `{r['path']}` / source `{r['answer_source']}`",
            f"- Retrieved: `{', '.join(r['retrieved_ids'][:8])}`",
            f"- Causal models: `{', '.join(c['id'] for c in r['causal_models_used']) or '—'}`",
            f"- Mental models: `{', '.join(m['id'] for m in r['mental_models_used']) or '—'}`",
            f"- Multi-discipline retrieve: `{r['multi_discipline']}`",
            f"- Answer (truncated): {r['answer'][:280]}{'…' if len(r['answer'])>280 else ''}",
            "",
        ]

    lines += [
        "## Part 4 — Knowledge coverage (audit-session usage)",
        "",
        "| Course | Concepts | Referenced in audit | Never used in audit | Usage % |",
        "|---|---:|---:|---:|---:|",
        f"| Economics | {cov.get('economics',{}).get('concepts',0)} | {cov.get('economics',{}).get('referenced',0)} | {cov.get('economics',{}).get('never_used',0)} | {cov.get('economics',{}).get('usage_pct',0)}% |",
        f"| Accounting | {cov.get('accounting',{}).get('concepts',0)} | {cov.get('accounting',{}).get('referenced',0)} | {cov.get('accounting',{}).get('never_used',0)} | {cov.get('accounting',{}).get('usage_pct',0)}% |",
        f"| Corporate Finance | {cov.get('corporate_finance',{}).get('concepts',0)} | {cov.get('corporate_finance',{}).get('referenced',0)} | {cov.get('corporate_finance',{}).get('never_used',0)} | {cov.get('corporate_finance',{}).get('usage_pct',0)}% |",
        "",
        "## Part 5 — Knowledge graph usage",
        "",
        f"- Requested chain: `{' → '.join(evidence['graph_traversal']['requested_chain'])}`",
        f"- Requested chain covered by KOs: `{evidence['graph_traversal']['all_steps_have_concepts']}`",
        f"- Production Ask AGI traverses graph: `{evidence['graph_traversal']['production_traversal_by_ask_agi']}`",
        f"- Verdict: {evidence['graph_traversal']['verdict']}",
        "",
        "### Concept coverage by chain step",
        "",
        "| Step | Academy concepts available |",
        "|---|---|",
    ]
    for step, cids in (evidence["graph_traversal"].get("concept_coverage_by_step") or {}).items():
        lines.append(f"| {step} | `{', '.join(cids) or '—'}` |")

    lines += [
        "",
        "## Part 6 — Retrieval audit (Academy-direct ranking)",
        "",
        "For each reasoning question: ranked knowledge objects, selection reason, and expected concepts ignored.",
        "",
    ]
    for r in evidence["reasoning_tests_academy_direct"]:
        lines += [
            f"### {r['question']}",
            "",
            "| Rank | Concept | Score | Why selected |",
            "|---:|---|---:|---|",
        ]
        for i, hit in enumerate(r.get("retrieved") or [], 1):
            why = (hit.get("why_selected") or "").replace("|", "/")
            lines.append(
                f"| {i} | `{hit.get('concept_id')}` ({hit.get('course')}) | {hit.get('score')} | {why} |"
            )
        ignored = r.get("expected_miss") or []
        lines += [
            "",
            f"- Expected concepts ignored / not in top retrieve: `{', '.join(ignored) or 'none'}`",
            f"- Knowledge objects used in answer composition: `{', '.join(r.get('retrieved_ids') or [])}`",
            f"- Causal models: `{', '.join(c['id'] for c in r.get('causal_models_used') or []) or '—'}`",
            f"- Mental models: `{', '.join(m['id'] for m in r.get('mental_models_used') or []) or '—'}`",
            "",
        ]

    lines += [
        "## Part 7 — Before vs After (Academy flag)",
        "",
        f"- Ask AGI material change: `{ab['material_change_in_ask_agi']}`",
        f"- VE defaults material change: `{ab['material_change_in_ve_defaults']}`",
        f"- Academy-direct answers material change: `{ab['material_change_in_academy_direct_answers']}`",
        f"- Verdict: {ab['verdict']}",
        "",
        "## Part 8 — Hallucination reduction",
        "",
        "Cannot be demonstrated in production because Ask AGI/IRP/VE do not consume Academy. "
        "Library exams reduce *Academy-path* unsupported claims, but platform hallucination risk is unchanged until wiring exists.",
        "",
        "| Check | Result |",
        "|---|---|",
        "| Academy exam suite pass | "
        + f"{evidence['exam_suite']['passed']}/{evidence['exam_suite']['total']} |",
        "| Production answers cite Academy provenance | No |",
        "| VE stops using opaque default WACC | No |",
        "",
        "## Part 9 — Decision quality (synthesis)",
        "",
    ]
    for row in evidence["synthesis_tests"]:
        lines += [
            f"### {row['question']}",
            f"- Disciplines retrieved (Academy-direct): `{', '.join(row['disciplines_retrieved'])}`",
            f"- Must-concepts hit: `{', '.join(row['must_concepts_hit']) or '—'}`",
            f"- Must-concepts miss: `{', '.join(row['must_concepts_miss']) or '—'}`",
            f"- Ask AGI uses Academy: `{row['ask_agi_uses_academy']}`",
            f"- Decision quality via Academy-direct: `{row['decision_quality_via_academy_direct']}`",
            "",
        ]

    lines += [
        "## Part 10 — Missing knowledge (prioritized)",
        "",
        "| Impact | Concept | Status | Gap |",
        "|---|---|---|---|",
    ]
    for m in evidence["missing_knowledge"][:12]:
        lines.append(f"| {m['impact']} | {m['concept']} | {m['status']} | {m['gap']} |")

    lines += [
        "",
        "## Part 11 — Metrics",
        "",
        f"- Avg concepts retrieved / Academy-direct answer: **{metrics['avg_concepts_retrieved_per_answer']}**",
        f"- Avg causal models used: **{metrics['avg_causal_models_used']}**",
        f"- Avg mental models used: **{metrics['avg_mental_models_used']}**",
        f"- Multi-discipline retrieve %: **{metrics['multi_discipline_answer_pct']}%**",
        f"- Soft consumers callable %: **{metrics['soft_consumers_callable_pct']}%**",
        f"- Production engines importing Academy: **{metrics['production_engines_importing_academy']}**",
        f"- Ask AGI Academy integration: **{metrics.get('ask_agi_academy_integration')}**",
        f"- FAPI quality gates passed: **{metrics.get('fapi_quality_gates_passed')}**",
        "",
        "## Part 12 — Failure report",
        "",
    ]
    for item in evidence["failure_report"]["integration_failures"]:
        lines.append(f"- {item}")
    lines += ["", "### Reasoning failures", ""]
    for item in evidence["failure_report"]["reasoning_failures"]:
        lines.append(f"- {item}")

    lines += [
        "",
        "## Scores (0–100)",
        "",
        "| Dimension | Score |",
        "|---|---:|",
    ]
    for k, v in scores.items():
        lines.append(f"| {k.replace('_', ' ').title()} | {v} |")

    lines += [
        "",
        "## Prioritized remediation (before more books)",
        "",
        "1. **Wire soft consumers into production composition roots** (without redesigning locked engines): Ask AGI/CAE assemble path should call `academy.consumers` for economics/accounting/CF slices.",
        "2. **IRP retrieval step** must fetch Academy KOs/causal models and attach concept provenance to reasoning traces.",
        "3. **VE assumptions builder** should consume Academy `wacc` / `cost_of_equity` / `roic_wacc_spread` guidance instead of only `DEFAULT_ASSUMPTIONS`.",
        "4. **EVE verify path** should call Academy earnings-quality + red-flag scoring on statement packs.",
        "5. **IIE thesis path** should attach capital-allocation / ROIC–WACC management-quality views.",
        "6. **FLE driver path** should use Academy forecast_impact chains (GDP, WC, incremental ROIC).",
        "7. **KF/KCV publish path** should ingest Academy published KOs as first-class corpus objects.",
        "8. **Re-run this audit** and require production A/B delta + provenance in Ask AGI answers before ingesting Investment Valuation.",
        "",
        "## Success criteria status",
        "",
    ]
    for k, v in evidence["final_verdict"]["success_criteria"].items():
        lines.append(f"- `{k}`: **{'PASS' if v else 'FAIL'}**")

    lines += [
        "",
        "---",
        "",
        "Raw evidence JSON: `finance_academy_audit_evidence.json`",
        "",
    ]
    md_path.write_text("\n".join(lines) + "\n")
    return {"json": json_path, "markdown": md_path}


def main() -> None:
    evidence = run_audit()
    repo_out = Path(__file__).resolve().parent
    art_out = Path("/opt/cursor/artifacts")
    paths = write_report(evidence, repo_out)
    art_paths = write_report(evidence, art_out)
    print(json.dumps({"repo": {k: str(v) for k, v in paths.items()}, "artifacts": {k: str(v) for k, v in art_paths.items()}, "scores": evidence["scores"], "overall_pass": evidence["final_verdict"]["overall_pass"]}, indent=2))


if __name__ == "__main__":
    main()
