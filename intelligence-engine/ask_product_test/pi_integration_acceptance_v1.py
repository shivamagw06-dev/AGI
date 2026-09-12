"""Portfolio Integration Acceptance Suite v1.0 - 75 live questions via KUL.

Phase 3.3.5 gate: Portfolio Intelligence registered as first-class KUL provider,
portfolio questions routed to PI before generic retrieval, no BUY/SELL leakage.
"""

from __future__ import annotations

from typing import Any, Dict, List

from investment_intelligence.policy import has_recommendation_leak

PI_INTEGRATION_CASES: List[Dict[str, Any]] = []


def _add(category: str, prompt: str, *, must_any: List[str], require_pi: bool = True):
    PI_INTEGRATION_CASES.append(
        {
            "id": f"PII-{len(PI_INTEGRATION_CASES)+1:02d}",
            "category": category,
            "prompt": prompt,
            "require_pi": require_pi,
            "must_any": must_any,
        }
    )


# Construction (12)
for prompt, must in [
    (
        "Use portfolio construction intelligence for AGIB Core India to explain allocation logic.",
        ["portfolio", "construction", "agib", "allocation"],
    ),
    (
        "Analyze AGIB Concentrated Growth portfolio construction and conviction sizing.",
        ["portfolio", "construction", "concentrated", "sizing"],
    ),
    (
        "For AGIB Core India portfolio, summarize diversification, sector balance, and cash.",
        ["portfolio", "agib", "diversification", "sector"],
    ),
    (
        "Use portfolio construction research to explain why AGIB Concentrated Growth holds concentrated positions.",
        ["portfolio", "concentrated", "construction", "positions"],
    ),
    (
        "What does AGIB Core India portfolio construction say about top holdings and allocation logic?",
        ["portfolio", "agib", "holdings", "allocation"],
    ),
    (
        "Assess AGIB Concentrated Growth position sizing and diversification trade-offs.",
        ["portfolio", "concentrated", "sizing", "diversification"],
    ),
    (
        "Use portfolio construction intelligence to explain AGIB Core India sector balance.",
        ["portfolio", "agib", "construction", "sector"],
    ),
    (
        "For Concentrated Growth, summarize portfolio construction around conviction and cash weight.",
        ["portfolio", "concentrated", "conviction", "cash"],
    ),
    (
        "Explain AGIB Core India canonical portfolio object and construction assumptions.",
        ["portfolio", "agib", "object", "construction"],
    ),
    (
        "Use portfolio construction to show AGIB Concentrated Growth allocation by sleeve.",
        ["portfolio", "concentrated", "allocation", "sleeve"],
    ),
    (
        "What construction risks come from AGIB Core India top-three concentration?",
        ["portfolio", "agib", "top", "concentration"],
    ),
    (
        "Summarize Concentrated Growth portfolio construction, diversification, and unknowns.",
        ["portfolio", "concentrated", "diversification", "unknown"],
    ),
]:
    _add("construction", prompt, must_any=must)


# Exposures (10)
for prompt, must in [
    (
        "Use factor exposure intelligence for AGIB Core India portfolio by sector and style.",
        ["portfolio", "exposure", "agib", "sector"],
    ),
    (
        "Summarize Concentrated Growth portfolio exposures across sector, factor, and market cap.",
        ["portfolio", "exposure", "concentrated", "factor"],
    ),
    (
        "What are AGIB Core India factor exposures and hidden concentration risks?",
        ["portfolio", "agib", "factor", "concentration"],
    ),
    (
        "Use portfolio exposure analysis for Concentrated Growth currency and sector exposure.",
        ["portfolio", "concentrated", "currency", "sector"],
    ),
    (
        "Explain AGIB Core India style exposure, quality tilt, and cash exposure.",
        ["portfolio", "agib", "style", "cash"],
    ),
    (
        "For Concentrated Growth, summarize commodity, technology, and interest rate exposures.",
        ["portfolio", "concentrated", "commodity", "technology"],
    ),
    (
        "Use AGIB Core India portfolio exposure intelligence to explain country and geography exposure.",
        ["portfolio", "agib", "country", "geography"],
    ),
    (
        "What factor exposure dominates Concentrated Growth portfolio risk?",
        ["portfolio", "concentrated", "factor", "risk"],
    ),
    (
        "Summarize AGIB Core India market cap and sector exposures from the portfolio object.",
        ["portfolio", "agib", "market cap", "sector"],
    ),
    (
        "Use portfolio exposure intelligence to compare Concentrated Growth factor and sector sleeves.",
        ["portfolio", "concentrated", "exposure", "sector"],
    ),
]:
    _add("exposures", prompt, must_any=must)


# Risk (10)
for prompt, must in [
    (
        "Use risk budget intelligence for AGIB Core India portfolio to explain key risks.",
        ["portfolio", "risk", "agib", "budget"],
    ),
    (
        "What is the Concentrated Growth portfolio risk budget and tail risk profile?",
        ["portfolio", "risk", "concentrated", "tail"],
    ),
    (
        "Analyze AGIB Core India concentration risk, liquidity risk, and drawdown risk.",
        ["portfolio", "agib", "concentration", "liquidity"],
    ),
    (
        "Which holdings dominate risk contribution in Concentrated Growth portfolio?",
        ["portfolio", "concentrated", "dominate", "risk"],
    ),
    (
        "Use portfolio risk budget for AGIB Core India sector risk and factor risk.",
        ["portfolio", "agib", "sector risk", "factor"],
    ),
    (
        "Explain Concentrated Growth largest risk positions and drawdown sensitivity.",
        ["portfolio", "concentrated", "largest risk", "drawdown"],
    ),
    (
        "What portfolio risks should be monitored for AGIB Core India?",
        ["portfolio", "agib", "risk", "monitor"],
    ),
    (
        "Use Concentrated Growth risk budget intelligence to summarize position risk.",
        ["portfolio", "concentrated", "risk budget", "position"],
    ),
    (
        "Assess AGIB Core India tail risk and hidden concentration from portfolio intelligence.",
        ["portfolio", "agib", "tail", "concentration"],
    ),
    (
        "For Concentrated Growth, explain sector risk, liquidity risk, and unknowns.",
        ["portfolio", "concentrated", "sector risk", "unknown"],
    ),
]:
    _add("risk", prompt, must_any=must)


# Quality (8)
for prompt, must in [
    (
        "Use portfolio quality intelligence to assess AGIB Core India business quality.",
        ["portfolio", "quality", "agib", "business"],
    ),
    (
        "Assess Concentrated Growth portfolio quality, evidence strength, and cash generation.",
        ["portfolio", "quality", "concentrated", "evidence"],
    ),
    (
        "What does AGIB Core India portfolio quality say about financial quality overlays?",
        ["portfolio", "agib", "quality", "financial"],
    ),
    (
        "Use Concentrated Growth portfolio quality to summarize weak evidence and strong evidence sleeves.",
        ["portfolio", "concentrated", "quality", "evidence"],
    ),
    (
        "Explain AGIB Core India quality tilt using Investment Intelligence quality overlays.",
        ["portfolio", "agib", "quality", "investment"],
    ),
    (
        "For Concentrated Growth, summarize portfolio quality and monitoring implications.",
        ["portfolio", "concentrated", "quality", "monitoring"],
    ),
    (
        "Use AGIB Core India portfolio quality intelligence to identify quality concentration.",
        ["portfolio", "agib", "quality", "concentration"],
    ),
    (
        "What quality risks show up in Concentrated Growth portfolio evidence strength?",
        ["portfolio", "concentrated", "quality", "risk"],
    ),
]:
    _add("quality", prompt, must_any=must)


# Scenarios (8)
for prompt, must in [
    (
        "Run portfolio scenario analysis for AGIB Core India under recession and recovery shocks.",
        ["portfolio", "scenario", "agib", "recession"],
    ),
    (
        "Use Concentrated Growth portfolio scenarios for bull, bear, and technology disruption cases.",
        ["portfolio", "scenario", "concentrated", "technology"],
    ),
    (
        "What happens to AGIB Core India portfolio under interest rate and commodity shocks?",
        ["portfolio", "agib", "interest", "commodity"],
    ),
    (
        "Run Concentrated Growth scenario analysis for regulatory and FX shocks.",
        ["portfolio", "concentrated", "scenario", "regulatory"],
    ),
    (
        "Use portfolio scenario intelligence to summarize AGIB Core India downside risk.",
        ["portfolio", "scenario", "agib", "downside"],
    ),
    (
        "For Concentrated Growth, explain bear scenario risk and recovery scenario strengths.",
        ["portfolio", "concentrated", "bear", "recovery"],
    ),
    (
        "Run AGIB Core India portfolio scenarios around sector rotation and liquidity stress.",
        ["portfolio", "agib", "scenario", "liquidity"],
    ),
    (
        "Use Concentrated Growth portfolio scenario analysis to explain macro exposure shocks.",
        ["portfolio", "concentrated", "scenario", "macro"],
    ),
]:
    _add("scenarios", prompt, must_any=must)


# Monitoring (8)
for prompt, must in [
    (
        "Use portfolio monitoring intelligence for AGIB Core India evidence freshness and risk drift.",
        ["portfolio", "monitor", "agib", "evidence"],
    ),
    (
        "What should be monitored in Concentrated Growth portfolio for deterioration signals?",
        ["portfolio", "monitor", "concentrated", "deteriorat"],
    ),
    (
        "Summarize AGIB Core India monitoring priorities for sector exposure and quality risk.",
        ["portfolio", "agib", "monitoring", "sector"],
    ),
    (
        "Use Concentrated Growth portfolio monitoring to identify rebalancing and drift signals.",
        ["portfolio", "concentrated", "monitoring", "drift"],
    ),
    (
        "What evidence freshness should AGIB Core India portfolio monitoring track?",
        ["portfolio", "agib", "evidence freshness", "track"],
    ),
    (
        "Use portfolio monitoring for Concentrated Growth risk budget changes.",
        ["portfolio", "concentrated", "monitoring", "risk"],
    ),
    (
        "How should AGIB Core India monitor hidden concentration and quality deterioration?",
        ["portfolio", "agib", "monitor", "concentration"],
    ),
    (
        "For Concentrated Growth, summarize monitoring priorities across holdings and scenarios.",
        ["portfolio", "concentrated", "monitoring", "scenarios"],
    ),
]:
    _add("monitoring", prompt, must_any=must)


# Comparison (7)
for prompt, must in [
    (
        "Compare AGIB Core India portfolio versus Concentrated Growth on construction and risk budget.",
        ["portfolio", "compare", "agib", "concentrated"],
    ),
    (
        "Use portfolio comparison intelligence for AGIB Core India and Concentrated Growth exposures.",
        ["portfolio", "comparison", "agib", "exposure"],
    ),
    (
        "Compare Concentrated Growth vs AGIB Core India on quality and evidence strength.",
        ["portfolio", "compare", "concentrated", "quality"],
    ),
    (
        "Which portfolio has more hidden concentration: AGIB Core India or Concentrated Growth?",
        ["portfolio", "agib", "concentrated", "concentration"],
    ),
    (
        "Compare AGIB Core India and Concentrated Growth scenario risks and monitoring priorities.",
        ["portfolio", "compare", "scenario", "monitoring"],
    ),
    (
        "Use portfolio comparison to explain sector exposure differences between AGIB Core India and Concentrated Growth.",
        ["portfolio", "comparison", "sector", "exposure"],
    ),
    (
        "Compare risk contribution and diversification benefits across AGIB Core India and Concentrated Growth.",
        ["portfolio", "compare", "risk", "diversification"],
    ),
]:
    _add("comparison", prompt, must_any=must)


# Policy (6)
for prompt, must in [
    (
        "For AGIB Core India portfolio, explain the no BUY/SELL recommendation policy and observations-only scope.",
        ["portfolio", "policy", "no buy", "observations"],
    ),
    (
        "Using Concentrated Growth portfolio intelligence, summarize policy limits on trade recommendations.",
        ["portfolio", "policy", "concentrated", "recommendation"],
    ),
    (
        "What can AGIB Core India portfolio intelligence say under the no trade advice policy?",
        ["portfolio", "agib", "policy", "trade"],
    ),
    (
        "For Concentrated Growth portfolio, explain observations-only policy around rebalancing questions.",
        ["portfolio", "concentrated", "policy", "rebalancing"],
    ),
    (
        "Use AGIB Core India portfolio policy context to avoid BUY/SELL advice while discussing risk.",
        ["portfolio", "policy", "no buy", "risk"],
    ),
    (
        "For Concentrated Growth, state the portfolio recommendation policy and what monitoring is allowed.",
        ["portfolio", "concentrated", "policy", "monitoring"],
    ),
]:
    _add("policy", prompt, must_any=must)


# Founder extras (6)
for prompt, must in [
    (
        "Use AGIB Core India portfolio knowledge graph to explain relationships among holdings and sector risk.",
        ["portfolio", "agib", "graph", "holdings"],
    ),
    (
        "For Concentrated Growth, summarize attribution, performance drivers, and portfolio unknowns.",
        ["portfolio", "concentrated", "attribution", "performance"],
    ),
    (
        "What changed in AGIB Core India portfolio drift, rebalancing, and monitoring priorities?",
        ["portfolio", "agib", "drift", "rebalancing"],
    ),
    (
        "Use Concentrated Growth canonical portfolio object to explain holdings, graph, and risk.",
        ["portfolio", "concentrated", "object", "risk"],
    ),
    (
        "Explain AGIB Core India attribution and evidence strength from portfolio intelligence.",
        ["portfolio", "agib", "attribution", "evidence"],
    ),
    (
        "Use Concentrated Growth portfolio relationship graph to summarize concentration and monitoring.",
        ["portfolio", "concentrated", "graph", "monitoring"],
    ),
]:
    _add("founder_extras", prompt, must_any=must)


assert len(PI_INTEGRATION_CASES) == 75, len(PI_INTEGRATION_CASES)


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
    portfolio = ci.get("portfolio") if isinstance(ci, dict) else {}
    if isinstance(portfolio, dict):
        parts.append(str(portfolio))
    for r in payload.get("provider_results") or []:
        if isinstance(r, dict) and not r.get("empty"):
            parts.append(r.get("summary") or "")
            parts.append(" ".join(r.get("why") or []))
            raw = r.get("raw") or {}
            if isinstance(raw, dict):
                for key in (
                    "portfolio_id",
                    "portfolio_name",
                    "portfolio_summary",
                    "summary",
                    "modules_used",
                    "portfolio_object",
                    "construction",
                    "diversification",
                    "exposures",
                    "sector_exposures",
                    "risk_budget",
                    "key_risks",
                    "correlation",
                    "quality",
                    "attribution",
                    "rebalancing",
                    "scenarios",
                    "monitoring",
                    "monitoring_priorities",
                    "graph",
                    "compare",
                    "evidence",
                    "unknowns",
                    "recommendation_policy",
                ):
                    parts.append(str(raw.get(key) or ""))
    return " ".join(str(p) for p in parts if p).lower()


def evaluate_pi_integration_case(case: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
    sources = list((payload.get("coverage") or {}).get("knowledge_sources_used") or [])
    diag = payload.get("diagnostics") or {}
    consulted = list(diag.get("providers_consulted") or [])
    plan_ids = list(((diag.get("plan") or {}).get("provider_ids")) or [])
    text = _blob(payload)
    summary = str(payload.get("summary") or "")

    assertions: Dict[str, bool] = {}

    if case.get("require_pi"):
        assertions["pi_selected"] = "portfolio_intelligence" in sources or (
            "portfolio_intelligence" in consulted
        )
        assertions["kul_plan_has_pi"] = (
            "portfolio_intelligence" in plan_ids or "portfolio_intelligence" in consulted
        )
        assertions["pi_leads_or_used"] = (
            "portfolio_intelligence" in sources
            or (plan_ids[:1] == ["portfolio_intelligence"])
            or ("portfolio_intelligence" in consulted and any(m in text for m in (case.get("must_any") or [])[:2]))
        )

    assertions["provider_ordering_ok"] = (
        "portfolio_intelligence" not in plan_ids
        or plan_ids.index("portfolio_intelligence")
        <= min(
            (
                plan_ids.index(p)
                for p in (
                    "investment_intelligence",
                    "business_intelligence",
                    "industry_intelligence",
                    "legacy_kip",
                )
                if p in plan_ids
            ),
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
