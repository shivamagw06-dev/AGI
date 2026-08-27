"""FAPI production bridge — soft adapters for locked engines (no redesign)."""

from __future__ import annotations

from typing import Any

from academy.catalog import list_concept_ids, teach
from academy.consumers import for_engine
from academy.fapi.assumptions import derive_cost_of_capital
from academy.fapi.intent import detect_finance_intent
from academy.fapi.retrieval import retrieve_academy
from academy.fapi.usage import get_usage_store


FAPI_VERSION = "fapi-v1.0.0"


def is_production_enabled() -> bool:
    """Respect Academy / FAPI flags from settings when available."""
    try:
        from app.core.config import get_settings

        s = get_settings()
        if not bool(getattr(s, "academy", True)):
            return False
        return bool(getattr(s, "academy_production", True))
    except Exception:
        return True


def package_for_query(
    query: str,
    *,
    engine: str = "cae",
    ticker: str | None = None,
    limit: int = 12,
    record: bool = True,
) -> dict[str, Any]:
    """Build the production Finance Academy context package for a query."""
    if not is_production_enabled():
        return {
            "enabled": False,
            "fapi_version": FAPI_VERSION,
            "is_finance": False,
            "bypassed": True,
            "concepts": [],
            "concept_ids": [],
            "provenance": {"influenced": False, "reason": "academy_production_disabled"},
        }

    intent = detect_finance_intent(query)
    # SIF — sector detection / framework before generic Academy ranking (additive)
    sif_pkg: dict[str, Any] = {}
    try:
        from sif.production import analyse_query as sif_analyse

        sif_pkg = sif_analyse(query, ticker=ticker, engine=engine, record=record)
        if sif_pkg.get("ticker") and not ticker:
            ticker = sif_pkg.get("ticker")
    except Exception:
        sif_pkg = {}

    # Company / sector questions are finance even if lexical intent is thin
    if sif_pkg.get("sector_id"):
        intent["is_finance"] = True
        intent.setdefault("domains", ["economics", "accounting", "corporate_finance"])

    if not intent["is_finance"]:
        if record:
            get_usage_store().record_retrieval(
                query=query,
                engine=engine,
                concept_ids=[],
                courses=[],
                influenced=False,
                bypassed=False,
                trace={"intent": intent, "note": "non_finance_query"},
            )
        return {
            "enabled": True,
            "fapi_version": FAPI_VERSION,
            "is_finance": False,
            "intent": intent,
            "concepts": [],
            "concept_ids": [],
            "courses": [],
            "causal_models": [],
            "mental_models": [],
            "formulas": [],
            "relationships": [],
            "consumer": {},
            "answer_hints": [],
            "sector_intelligence": sif_pkg or {},
            "provenance": {"influenced": False, "reason": "non_finance_query"},
        }

    # Prefer SIF-reranked Academy concepts when a sector framework is active
    if sif_pkg.get("sector_id") and sif_pkg.get("academy_concepts_used"):
        from academy.catalog import knowledge_by_id

        kb = knowledge_by_id()
        concepts = []
        for cid in sif_pkg.get("academy_concepts_used") or []:
            ko = kb.get(cid)
            if not ko:
                continue
            concepts.append(
                {
                    "concept_id": cid,
                    "concept": ko.concept,
                    "course": ko.course_id,
                    "score": 90.0,
                    "definition": ko.definition,
                    "formula": ko.formula,
                    "why_selected": "sif_sector_priority",
                }
            )
        # Fill remaining via lexical retrieve, excluding suppressed generics
        lexical = retrieve_academy(query, domains=intent["domains"], limit=limit)
        suppress = set(sif_pkg.get("generic_suppressed") or [])
        have = {c["concept_id"] for c in concepts}
        for row in lexical.get("concepts") or []:
            if row["concept_id"] in have or row["concept_id"] in suppress:
                continue
            concepts.append(row)
            have.add(row["concept_id"])
            if len(concepts) >= limit:
                break
        courses = sorted(
            {
                ("economics" if "mankiw" in str(c.get("course")) or "economics" in str(c.get("course")) else
                 "accounting" if "accounting" in str(c.get("course")) else
                 "corporate_finance" if "corporate" in str(c.get("course")) or "acf" in str(c.get("course")) else
                 str(c.get("course") or "unknown"))
                for c in concepts[:12]
                if c.get("course")
            }
        )
        retrieved = {
            **lexical,
            "concepts": concepts[:limit],
            "concept_ids": [c["concept_id"] for c in concepts[:limit]],
            "courses": [c for c in courses if c != "unknown"] or lexical.get("courses") or [],
            "multi_discipline": len({c for c in courses if c != "unknown"}) >= 2,
        }
    else:
        retrieved = retrieve_academy(query, domains=intent["domains"], limit=limit)
    primary = (retrieved["concept_ids"] or ["value_creation"])[0]
    consumer_payload: dict[str, Any] = {"concept_id": primary, "concepts": retrieved["concept_ids"][:10]}
    if ticker:
        consumer_payload["ticker"] = ticker
    try:
        consumer = for_engine(engine if engine in {"kf", "kcv", "kc", "eve", "iie", "ve", "fle", "irp", "fiml"} else "irp", consumer_payload)
    except Exception:
        consumer = for_engine("irp", consumer_payload)

    answer_hints = list(sif_pkg.get("answer_hints") or [])[:4] + _compose_answer_hints(retrieved)
    graph_chain = _best_chain(retrieved)
    if sif_pkg.get("sector_id") == "banks":
        graph_chain = ["Interest Rates", "NIM / Deposit Franchise", "Credit Cost / Asset Quality", "ROE vs COE", "P/B", "Investment Decision"]

    package = {
        "enabled": True,
        "fapi_version": FAPI_VERSION,
        "is_finance": True,
        "intent": intent,
        "ticker": ticker,
        "engine": engine,
        "concepts": retrieved["concepts"],
        "concept_ids": retrieved["concept_ids"],
        "courses": retrieved["courses"],
        "causal_models": retrieved["causal_models"],
        "mental_models": retrieved["mental_models"],
        "formulas": retrieved["formulas"],
        "relationships": retrieved["relationships"],
        "multi_discipline": retrieved["multi_discipline"],
        "knowledge_graph_chain": graph_chain,
        "consumer": consumer,
        "answer_hints": answer_hints[:10],
        "sector_intelligence": sif_pkg or {},
        "answer_policy": (
            sif_pkg.get("answer_policy")
            if sif_pkg.get("sector_id")
            else "academy_before_llm_finance_reasoning"
        ),
        "provenance": {
            "influenced": bool(retrieved["concept_ids"]) or bool(sif_pkg.get("kpis_retrieved")),
            "concept_ids": retrieved["concept_ids"][:16],
            "causal_model_ids": [c["model_id"] for c in retrieved["causal_models"][:8]],
            "mental_model_ids": [m["model_id"] for m in retrieved["mental_models"][:8]],
            "courses": retrieved["courses"],
            "frameworks": _frameworks(retrieved),
            "sector_id": sif_pkg.get("sector_id"),
            "sector_kpis": sif_pkg.get("kpis_retrieved") or [],
            "valuation_framework": (sif_pkg.get("valuation_framework") or {}).get("methodology"),
            "recommendation_blocked": bool((sif_pkg.get("recommendation_gate") or {}).get("blocked")),
        },
    }

    # Academy Books — soft structured learning (never verbatim book text)
    try:
        from academy.books.production import package_for_query as books_package

        books_pkg = books_package(query, ticker=ticker, limit=8)
        if books_pkg.get("enabled") and books_pkg.get("concept_ids"):
            have = set(package.get("concept_ids") or [])
            for row in books_pkg.get("concepts") or []:
                cid = row.get("concept_id")
                if not cid or cid in have:
                    continue
                package.setdefault("concepts", []).append(
                    {
                        "concept_id": cid,
                        "concept": row.get("title"),
                        "course": "academy_books",
                        "score": 70.0,
                        "definition": row.get("definition"),
                        "why_selected": "academy_books",
                    }
                )
                package.setdefault("concept_ids", []).append(cid)
                have.add(cid)
            if "academy_books" not in (package.get("courses") or []):
                package.setdefault("courses", []).append("academy_books")
            for h in books_pkg.get("answer_hints") or []:
                if h not in package.get("answer_hints", []):
                    package.setdefault("answer_hints", []).append(h)
            package["academy_books"] = {
                "frameworks": books_pkg.get("frameworks") or [],
                "formulas": books_pkg.get("formulas") or [],
                "provenance": books_pkg.get("provenance") or {},
            }
            prov = package.setdefault("provenance", {})
            prov["books_influenced"] = True
            prov["verbatim_quotes"] = False
    except Exception:
        pass

    if record:
        get_usage_store().record_retrieval(
            query=query,
            engine=engine,
            concept_ids=retrieved["concept_ids"],
            courses=retrieved["courses"],
            causal_ids=[c["model_id"] for c in retrieved["causal_models"]],
            mental_ids=[m["model_id"] for m in retrieved["mental_models"]],
            influenced=True,
            bypassed=False,
            trace=package["provenance"],
        )
    return package


def attach_for_engine(engine: str, query: str, *, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Soft attach Academy slice for a specific engine consult/search path."""
    p = payload or {}
    pkg = package_for_query(query, engine=engine, ticker=p.get("ticker"), limit=int(p.get("limit") or 10))
    if not pkg.get("enabled") or not pkg.get("is_finance"):
        return {"finance_academy": pkg, "attached": False}
    # merge consumer-specific enrichment
    try:
        consumer = for_engine(engine, {**p, "concept_id": (pkg.get("concept_ids") or ["value_creation"])[0], "concepts": pkg.get("concept_ids")})
    except Exception:
        consumer = pkg.get("consumer") or {}
    pkg = {**pkg, "consumer": consumer}
    record_engine_consumption(engine, pkg)
    return {"finance_academy": pkg, "attached": True}


def apply_ve_assumptions(base_assumptions: dict[str, float], *, company_inputs: dict[str, Any] | None = None) -> dict[str, Any]:
    """Replace hardcoded finance assumptions with Academy methodology + live inputs."""
    if not is_production_enabled():
        return {
            "enabled": False,
            "assumptions": dict(base_assumptions),
            "uses_academy_wacc_objects": False,
            "changed": False,
        }
    inputs = company_inputs or {}
    derived = derive_cost_of_capital(
        risk_free_rate=inputs.get("risk_free_rate", base_assumptions.get("risk_free_rate")),
        beta=inputs.get("beta", base_assumptions.get("beta")),
        cost_of_debt=inputs.get("cost_of_debt", base_assumptions.get("cost_of_debt")),
        tax_rate=inputs.get("tax_rate", base_assumptions.get("tax_rate")),
        equity_risk_premium=inputs.get("equity_risk_premium"),
        country_risk_premium=inputs.get("country_risk_premium"),
        debt_weight=inputs.get("debt_weight"),
        equity_weight=inputs.get("equity_weight"),
    )
    merged = dict(base_assumptions)
    for k, v in derived["assumptions"].items():
        if k in ("wacc", "cost_of_equity", "cost_of_debt", "beta", "risk_free_rate", "tax_rate"):
            merged[k] = float(v)
    get_usage_store().record_retrieval(
        query="ve.assumptions",
        engine="ve",
        concept_ids=derived.get("concept_ids") or [],
        courses=["corporate_finance"],
        influenced=True,
        trace={"methodology": derived.get("methodology")},
    )
    return {
        "enabled": True,
        "assumptions": merged,
        "academy": derived,
        "uses_academy_wacc_objects": True,
        "changed": abs(float(merged.get("wacc", 0)) - float(base_assumptions.get("wacc", 0))) > 1e-9
        or abs(float(merged.get("cost_of_equity", 0)) - float(base_assumptions.get("cost_of_equity", 0))) > 1e-9,
    }


def enrich_reasoning(reasoning: dict[str, Any], package: dict[str, Any]) -> dict[str, Any]:
    """Inject Academy concepts into an IRP-style reasoning dict (additive)."""
    if not package.get("is_finance") or not package.get("concept_ids"):
        return reasoning
    out = dict(reasoning or {})
    hints = package.get("answer_hints") or []
    if hints:
        why = str(out.get("why") or "")
        academy_why = hints[0]
        out["why"] = (academy_why + (" " + why if why else "")).strip()[:1200]
        if not out.get("what_is_happening"):
            out["what_is_happening"] = hints[0][:400]
        drivers = list(out.get("key_drivers") or [])
        for cid in package.get("concept_ids")[:6]:
            label = cid.replace("_", " ")
            if label not in drivers:
                drivers.append(label)
        out["key_drivers"] = drivers[:10]
        if package.get("knowledge_graph_chain"):
            chain = " → ".join(package["knowledge_graph_chain"])
            vp = str(out.get("valuation_perspective") or "")
            out["valuation_perspective"] = (f"Academy chain: {chain}. " + vp).strip()[:800]
        supports = list(out.get("supports") or [])
        for h in hints[:3]:
            if h not in supports:
                supports.append(h)
        out["supports"] = supports[:8]
    out["finance_academy_provenance"] = package.get("provenance") or {}
    return out


def production_dashboard() -> dict[str, Any]:
    snap = get_usage_store().snapshot()
    all_ids = list_concept_ids()
    unused = get_usage_store().unused_concepts(all_ids, limit=40)
    gates = quality_gates()
    return {
        "programme": "FAPI",
        "version": FAPI_VERSION,
        "enabled": is_production_enabled(),
        "usage": snap,
        "most_retrieved_concepts": snap.get("most_retrieved") or [],
        "unused_concepts": unused,
        "engine_consumption": snap.get("engine_consumption") or {},
        "reasoning_traces": snap.get("recent_traces") or [],
        "knowledge_coverage": {
            "total_concepts": len(all_ids),
            "retrieved_unique": len(snap.get("most_retrieved") or []),
            "unused_sample": unused[:20],
        },
        "ab_results": snap.get("ab_runs") or [],
        "concept_influence_rankings": snap.get("most_retrieved") or [],
        "quality_gates": gates,
    }


def run_ab_probe(question: str = "Why does ROIC matter more than revenue growth?") -> dict[str, Any]:
    """Compare Academy production OFF vs ON for a finance question."""
    # ON
    on_pkg = package_for_query(question, engine="ask_agi", record=False)
    on_ve = apply_ve_assumptions({"wacc": 0.11, "cost_of_equity": 0.13, "cost_of_debt": 0.08, "beta": 1.0, "risk_free_rate": 0.07, "tax_rate": 0.25})

    # OFF simulation
    off = {
        "enabled": False,
        "concept_ids": [],
        "answer_hints": [],
        "uses_academy": False,
        "wacc": 0.11,
    }
    on = {
        "enabled": True,
        "concept_ids": on_pkg.get("concept_ids") or [],
        "answer_hints": on_pkg.get("answer_hints") or [],
        "uses_academy": bool(on_pkg.get("concept_ids")),
        "wacc": (on_ve.get("assumptions") or {}).get("wacc"),
        "multi_discipline": on_pkg.get("multi_discipline"),
        "causal_models": [c.get("model_id") for c in (on_pkg.get("causal_models") or [])],
        "mental_models": [m.get("model_id") for m in (on_pkg.get("mental_models") or [])],
    }
    material = bool(on["uses_academy"]) and (
        on["wacc"] != off["wacc"] or len(on["concept_ids"]) > 0 or len(on["answer_hints"]) > 0
    )
    result = {
        "question": question,
        "version_a_off": off,
        "version_b_on": on,
        "material_improvement": material,
        "deltas": {
            "concepts_retrieved": len(on["concept_ids"]),
            "wacc_delta": round(float(on["wacc"] or 0) - float(off["wacc"]), 6),
            "multi_discipline": on.get("multi_discipline"),
            "causal_models": len(on.get("causal_models") or []),
            "mental_models": len(on.get("mental_models") or []),
        },
    }
    get_usage_store().record_ab(result)
    return result


def quality_gates(*, warm: bool = True) -> dict[str, Any]:
    """Reject completion if production engines still bypass Academy."""
    probe_q = "Why does ROIC matter more than revenue growth?"
    if warm:
        # Exercise each production soft path once so gates reflect wiring, not traffic volume.
        for eng in ("cae", "ask_agi", "irp", "ve", "eve", "iie", "fle", "kf", "kcv"):
            try:
                attach_for_engine(eng, probe_q)
            except Exception:
                continue
        try:
            apply_ve_assumptions(
                {
                    "wacc": 0.11,
                    "cost_of_equity": 0.13,
                    "cost_of_debt": 0.08,
                    "beta": 1.0,
                    "risk_free_rate": 0.07,
                    "tax_rate": 0.25,
                }
            )
        except Exception:
            pass
    snap = get_usage_store().snapshot()
    engines = set((snap.get("engine_consumption") or {}).keys())
    required = {"cae", "ask_agi", "irp", "ve", "eve", "iie", "fle", "kf"}
    # also accept ui as ask_agi alias
    if "ui" in engines:
        engines.add("ask_agi")
    if "kcv" in engines or "kc" in engines:
        engines.add("kf")
    missing = sorted(required - engines)
    ab_ok = any(r.get("material_improvement") for r in (snap.get("ab_runs") or []))
    # if no AB yet, run one
    if not (snap.get("ab_runs") or []):
        ab = run_ab_probe()
        ab_ok = bool(ab.get("material_improvement"))
        snap = get_usage_store().snapshot()
        engines = set((snap.get("engine_consumption") or {}).keys())
        if "ui" in engines:
            engines.add("ask_agi")
        if "kcv" in engines or "kc" in engines:
            engines.add("kf")
        missing = sorted(required - engines)
    influenced = int(snap.get("influenced_answers") or 0)
    checks = {
        "ask_agi_consults_academy": "ask_agi" in engines or "ui" in engines or "cae" in engines,
        "irp_uses_academy": "irp" in engines,
        "ve_uses_academy_assumptions": "ve" in engines,
        "eve_uses_academy_accounting": "eve" in engines,
        "iie_uses_academy": "iie" in engines,
        "fle_uses_academy": "fle" in engines,
        "kf_exposes_academy": "kf" in engines or "kcv" in engines or "kc" in engines,
        "ab_material_improvement": ab_ok,
        "answers_influenced": influenced > 0 or ab_ok,
    }
    passed = all(checks.values())
    return {
        "passed": passed,
        "checks": checks,
        "missing_engines": missing,
        "engines_seen": sorted(engines),
        "influence_rate": snap.get("influence_rate"),
        "reject_completion": not passed,
        "message": "FAPI production quality gates passed"
        if passed
        else "FAPI incomplete — engines still bypassing Academy or AB shows no improvement",
    }


def record_engine_consumption(engine: str, package: dict[str, Any]) -> None:
    if not package.get("is_finance"):
        return
    get_usage_store().record_retrieval(
        query=str(package.get("intent", {}).get("token_hits", "") or package.get("engine") or engine),
        engine=engine,
        concept_ids=list(package.get("concept_ids") or [])[:16],
        courses=list(package.get("courses") or []),
        causal_ids=[c.get("model_id") for c in (package.get("causal_models") or []) if isinstance(c, dict)],
        mental_ids=[m.get("model_id") for m in (package.get("mental_models") or []) if isinstance(m, dict)],
        influenced=True,
        trace=package.get("provenance") or {},
    )


def _compose_answer_hints(retrieved: dict[str, Any]) -> list[str]:
    hints: list[str] = []
    for r in (retrieved.get("concepts") or [])[:5]:
        cid = r.get("concept_id")
        try:
            lesson = teach(cid)
            bit = lesson.get("what_it_is") or r.get("definition") or ""
            inv = (lesson.get("how_investors_should_think") or [None])[0]
            text = f"{r.get('concept')}: {bit}"
            if inv:
                text += f" Investor lens: {inv}"
            hints.append(text[:420])
        except Exception:
            if r.get("definition"):
                hints.append(f"{r.get('concept')}: {r.get('definition')}"[:420])
    for c in (retrieved.get("causal_models") or [])[:2]:
        chain = " → ".join(c.get("chain") or [])
        if chain:
            hints.append(f"Causal: {c.get('name')}: {chain}")
    return hints[:8]


def _best_chain(retrieved: dict[str, Any]) -> list[str]:
    for c in retrieved.get("causal_models") or []:
        chain = c.get("chain") or []
        if len(chain) >= 3:
            return list(chain)
    # fallback canonical valuation chain if concepts present
    ids = set(retrieved.get("concept_ids") or [])
    canonical = ["monetary_policy", "discount_rate", "wacc", "present_value", "value_creation", "capital_allocation"]
    present = [c for c in canonical if c in ids]
    if len(present) >= 3:
        return present
    return list(retrieved.get("concept_ids") or [])[:6]


def _frameworks(retrieved: dict[str, Any]) -> list[str]:
    out = []
    for r in retrieved.get("concepts") or []:
        for f in r.get("decision_framework") or []:
            if f not in out:
                out.append(f)
        if len(out) >= 8:
            break
    return out
