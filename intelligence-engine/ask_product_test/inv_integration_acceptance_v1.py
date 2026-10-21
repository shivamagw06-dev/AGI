"""Investment Integration Acceptance Suite v1.0 — 75 live questions via KUL.

Phase 3.2.5 gate: Investment Intelligence registered as first-class KUL provider,
investment questions routed to INV before generic retrieval, no BUY/SELL leakage.
"""

from __future__ import annotations

from typing import Any, Dict, List

from investment_intelligence.policy import has_recommendation_leak

INV_INTEGRATION_CASES: List[Dict[str, Any]] = []


def _add(category: str, prompt: str, *, must_any: List[str], require_inv: bool = True):
    INV_INTEGRATION_CASES.append(
        {
            "id": f"INVI-{len(INV_INTEGRATION_CASES)+1:02d}",
            "category": category,
            "prompt": prompt,
            "require_inv": require_inv,
            "must_any": must_any,
        }
    )


# Investment Thesis (8)
for prompt, must in [
    ("What is the investment thesis for Reliance Industries?", ["thesis", "reliance", "risk", "quality"]),
    ("Evaluate Reliance's investment quality.", ["quality", "reliance", "invest"]),
    ("What is the investment thesis for TCS?", ["thesis", "tcs", "quality", "risk"]),
    ("Why is Asian Paints considered high business quality from an investment perspective?", ["quality", "asian", "brand", "distribution"]),
    ("Evaluate DMart's quality.", ["quality", "dmart", "retail"]),
    ("Assess Berger Paints' investment case.", ["berger", "quality", "invest"]),
    ("Explain the investment thesis for HDFC Bank.", ["thesis", "hdfc", "bank", "credit"]),
    ("So what does Infosys mean for an investor?", ["infosys", "invest", "risk", "monitor"]),
]:
    _add("investment_thesis", prompt, must_any=must)

# Business / Financial Quality (8)
for prompt, must in [
    ("Evaluate business quality of TCS.", ["quality", "business", "tcs"]),
    ("Assess management quality of Infosys using available evidence.", ["quality", "management", "infosys", "evidence"]),
    ("Evaluate financial quality signals for HDFC Bank.", ["quality", "financial", "hdfc", "bank"]),
    ("Compare Asian Paints and Berger from a quality perspective.", ["asian", "berger", "quality"]),
    ("Compare TCS and Infosys from a quality perspective.", ["tcs", "infosys", "quality"]),
    ("What drives business quality at Reliance?", ["quality", "business", "reliance"]),
    ("Assess DMart's business quality.", ["dmart", "quality", "business"]),
    ("Evaluate JSW Steel's investment quality.", ["jsw", "quality", "steel", "risk"]),
]:
    _add("business_quality", prompt, must_any=must)

# Capital Allocation (7)
for prompt, must in [
    ("Assess HDFC Bank's capital allocation.", ["capital", "allocat", "hdfc"]),
    ("Evaluate capital allocation for Reliance Industries.", ["capital", "allocat", "reliance"]),
    ("Evaluate capital allocation for TCS.", ["capital", "allocat", "tcs", "dividend", "buyback"]),
    ("Assess capital allocation at Asian Paints.", ["capital", "allocat", "asian"]),
    ("How does DMart allocate capital?", ["capital", "allocat", "dmart", "store"]),
    ("Evaluate capital allocation for Infosys.", ["capital", "allocat", "infosys"]),
    ("Assess capital allocation quality at Berger Paints.", ["capital", "allocat", "berger"]),
]:
    _add("capital_allocation", prompt, must_any=must)

# Catalysts (7)
for prompt, must in [
    ("What are Infosys' biggest catalysts?", ["catalyst", "infosys"]),
    ("What are key catalysts for TCS?", ["catalyst", "tcs"]),
    ("What could rerate TCS?", ["catalyst", "tcs", "rerate", "deal", "margin"]),
    ("What are key catalysts for Reliance Industries?", ["catalyst", "reliance"]),
    ("Explain catalysts for Asian Paints.", ["catalyst", "asian"]),
    ("What catalysts matter for HDFC Bank?", ["catalyst", "hdfc", "bank"]),
    ("What are key catalysts for DMart?", ["catalyst", "dmart"]),
]:
    _add("catalysts", prompt, must_any=must)

# Risks (8)
for prompt, must in [
    ("What are Reliance's biggest investment risks?", ["risk", "reliance"]),
    ("Evaluate JSW Steel's investment risks.", ["risk", "jsw", "steel", "spread", "leverage"]),
    ("Explain downside risks for IndiGo.", ["risk", "indigo", "fuel", "airline"]),
    ("What are the biggest investment risks for TCS?", ["risk", "tcs"]),
    ("What investment risks dominate for HDFC Bank?", ["risk", "hdfc", "credit", "bank"]),
    ("Assess investment risks for Asian Paints.", ["risk", "asian", "competition"]),
    ("What are Infosys' major investment risks?", ["risk", "infosys"]),
    ("Explain investment risks for DMart.", ["risk", "dmart"]),
]:
    _add("risks", prompt, must_any=must)

# Scenarios (6)
for prompt, must in [
    ("Outline bull, base, and bear scenarios for Reliance Industries.", ["bull", "base", "bear", "scenario", "reliance"]),
    ("Outline bull, base, and bear scenarios for TCS.", ["bull", "base", "bear", "scenario", "tcs"]),
    ("Outline bull and bear cases for HDFC Bank.", ["bull", "bear", "scenario", "hdfc"]),
    ("Explain scenario analysis for Infosys.", ["scenario", "bull", "bear", "infosys"]),
    ("Outline bull, base, and bear scenarios for Asian Paints.", ["bull", "base", "bear", "asian"]),
    ("Explain downside and base scenarios for IndiGo.", ["scenario", "bear", "base", "indigo", "risk"]),
]:
    _add("scenarios", prompt, must_any=must)

# Valuation Drivers (6)
for prompt, must in [
    ("What drives valuation for TCS?", ["valuat", "driver", "tcs", "margin", "growth"]),
    ("What drives valuation for Reliance Industries?", ["valuat", "driver", "reliance"]),
    ("Why might ROIC improve for TCS?", ["roic", "tcs", "margin"]),
    ("What drives valuation for HDFC Bank?", ["valuat", "bank", "hdfc", "nim", "credit"]),
    ("Explain valuation drivers for Asian Paints.", ["valuat", "asian", "margin", "volume"]),
    ("What drives valuation for Infosys?", ["valuat", "infosys", "growth", "margin"]),
]:
    _add("valuation_drivers", prompt, must_any=must)

# Monitoring (6)
for prompt, must in [
    ("How should investors monitor HDFC Bank?", ["monitor", "hdfc", "casa", "nim", "credit"]),
    ("Explain monitoring priorities for Asian Paints.", ["monitor", "asian", "volume", "margin"]),
    ("How should investors monitor TCS?", ["monitor", "tcs", "utilization", "deal"]),
    ("What are DMart's key investment monitoring points?", ["monitor", "dmart", "sssg"]),
    ("How should investors monitor Reliance Industries?", ["monitor", "reliance", "capex"]),
    ("How should investors monitor Infosys?", ["monitor", "infosys", "guidance", "margin"]),
]:
    _add("monitoring", prompt, must_any=must)

# Evidence (5)
for prompt, must in [
    ("Explain Berger Paints' evidence strength.", ["evidence", "berger", "strength"]),
    ("What is the evidence strength for conclusions on Asian Paints?", ["evidence", "asian", "strength"]),
    ("What unknowns remain for Reliance Industries?", ["unknown", "reliance", "evidence"]),
    ("Evaluate evidence strength for TCS investment conclusions.", ["evidence", "tcs", "strength"]),
    ("What is the evidence strength for Infosys?", ["evidence", "infosys", "strength"]),
]:
    _add("evidence", prompt, must_any=must)

# Comparisons (5)
for prompt, must in [
    ("Compare TCS and Infosys as businesses from an investment perspective.", ["tcs", "infosys", "quality", "invest"]),
    ("Compare Asian Paints and Berger from an investment quality perspective.", ["asian", "berger", "quality"]),
    ("Compare Reliance and TCS investment risk profiles.", ["reliance", "tcs", "risk"]),
    ("Compare HDFC Bank and Infosys from an investment perspective.", ["hdfc", "infosys", "invest", "quality", "risk"]),
    ("Compare DMart and Asian Paints on quality from an investment lens.", ["dmart", "asian", "quality"]),
]:
    _add("comparisons", prompt, must_any=must)

# Committee (4)
for prompt, must in [
    ("Run an investment committee simulation for Reliance Industries.", ["committee", "reliance", "no buy", "no sell", "recommend"]),
    ("Run an investment committee simulation for TCS.", ["committee", "tcs", "synthesis"]),
    ("What should an investment committee debate about HDFC Bank?", ["committee", "hdfc", "bank", "credit"]),
    ("Run an investment committee simulation for Asian Paints.", ["committee", "asian", "quality"]),
]:
    _add("committee", prompt, must_any=must)

# Financial quality / founder extras to reach 75
for prompt, must in [
    ("Assess IndiGo's investment risks and monitoring priorities.", ["indigo", "risk", "monitor", "fuel"]),
    ("Evaluate JSW Steel's catalysts and risks.", ["jsw", "catalyst", "risk"]),
    ("Analyze investment quality of Infosys.", ["infosys", "quality", "invest"]),
    ("Analyze capital allocation and risks for Reliance.", ["reliance", "capital", "risk"]),
    ("Evaluate monitoring points and unknowns for TCS.", ["tcs", "monitor", "unknown"]),
]:
    _add("founder_extras", prompt, must_any=must)

assert len(INV_INTEGRATION_CASES) == 75, len(INV_INTEGRATION_CASES)


def _summary_is_direct(summary: str) -> bool:
    s = (summary or "").strip()
    if len(s) < 24:
        return False
    low = s.lower()
    hedges = (
        "insufficient unified knowledge",
        "i don't know",
        "unable to answer",
        "no information available",
        "analyse via",
    )
    if any(h in low for h in hedges):
        return False
    if low.startswith(("framework", "intent:", "planning:")):
        return False
    return True


def _blob(payload: Dict[str, Any]) -> str:
    parts = [payload.get("summary"), " ".join(payload.get("why") or [])]
    ci = payload.get("company_intelligence") or {}
    inv = ci.get("investment") if isinstance(ci, dict) else {}
    if isinstance(inv, dict):
        parts.append(str(inv))
    for r in payload.get("provider_results") or []:
        if isinstance(r, dict) and not r.get("empty"):
            parts.append(r.get("summary") or "")
            parts.append(" ".join(r.get("why") or []))
            raw = r.get("raw") or {}
            if isinstance(raw, dict):
                parts.append(str(raw.get("entity") or ""))
                parts.append(str(raw.get("executive_summary") or raw.get("summary") or ""))
                for key in (
                    "thesis",
                    "quality",
                    "catalysts",
                    "risks",
                    "scenarios",
                    "valuation",
                    "capital_allocation",
                    "committee",
                    "evidence",
                ):
                    block = raw.get(key)
                    if isinstance(block, dict):
                        parts.append(block.get("summary") or "")
                        parts.append(str(block.get("composite_score") or ""))
                        parts.append(str(block.get("synthesis") or ""))
                    elif isinstance(block, list):
                        for item in block[:6]:
                            if isinstance(item, dict):
                                parts.append(item.get("name") or "")
                                parts.append(item.get("severity") or "")
                                parts.append(item.get("direction") or "")
                parts.append(" ".join(str(x) for x in (raw.get("unknowns") or [])[:6]))
                parts.append(" ".join(str(x) for x in (raw.get("monitoring_points") or [])[:6]))
                parts.append(str(raw.get("recommendation_policy") or ""))
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_inv_integration_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    diag = payload.get("diagnostics") or {}
    consulted = list(diag.get("providers_consulted") or [])
    plan_ids = list(((diag.get("plan") or {}).get("provider_ids")) or [])
    text = _blob(payload)
    summary = str(payload.get("summary") or "")

    assertions: Dict[str, bool] = {}

    if case.get("require_inv"):
        assertions["inv_selected"] = "investment_intelligence" in sources or (
            "investment_intelligence" in consulted
        )
        assertions["kul_plan_has_inv"] = (
            "investment_intelligence" in plan_ids or "investment_intelligence" in consulted
        )
        assertions["inv_leads_or_used"] = (
            "investment_intelligence" in sources
            or (plan_ids[:1] == ["investment_intelligence"])
            or ("investment_intelligence" in consulted and any(m in text for m in (case.get("must_any") or [])[:2]))
        )

    assertions["provider_ordering_ok"] = (
        "investment_intelligence" not in plan_ids
        or plan_ids.index("investment_intelligence")
        <= min(
            (plan_ids.index(p) for p in ("business_intelligence", "industry_intelligence", "legacy_kip") if p in plan_ids),
            default=0,
        )
    )
    assertions["no_generic_retrieval_only"] = sources != ["legacy_kip"] and (
        "legacy_kip" not in sources or len(sources) > 1
    )
    assertions["direct_answer_first"] = _summary_is_direct(summary)
    assertions["no_hallucination"] = payload.get("fabricated") is False
    assertions["no_framework_leakage"] = not summary.lower().startswith(
        ("analyse via", "framework", "intent:", "planning:")
    )
    # Policy strings like observations_only_no_buy_sell contain the substring "buy";
    # use the shared leak detector (allows policy / negation contexts).
    assertions["no_recommendation_leakage"] = not has_recommendation_leak(summary)

    must = case.get("must_any") or []
    if must:
        hits = sum(1 for m in must if m.lower() in text)
        need = 1 if len(must) <= 2 else min(2, len(must))
        assertions["topic_grounding"] = hits >= need

    passed = all(assertions.values()) if assertions else False
    return {
        "id": case["id"],
        "category": case["category"],
        "prompt": case["prompt"],
        "sources": sources,
        "consulted": consulted,
        "plan_ids": plan_ids,
        "assertions": assertions,
        "failed_assertions": [k for k, v in assertions.items() if not v],
        "summary": summary[:240],
        "pass": passed,
    }
