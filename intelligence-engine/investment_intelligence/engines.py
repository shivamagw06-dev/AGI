"""Deterministic Investment Intelligence engines — consume BI + Industry DNA."""

from __future__ import annotations

from typing import Any, Optional

from investment_intelligence.policy import strip_recommendation_language
from investment_intelligence.profiles import get_profile
from investment_intelligence.schema import (
    COMMITTEE_ROLES,
    QUALITY_DIMENSIONS,
    RECOMMENDATION_POLICY,
    RISK_TYPES,
    CatalystCard,
    CommitteeContribution,
    EvidenceCard,
    InvestmentThesis,
    QualityDimension,
    RiskCard,
    ScenarioCard,
)


def _industry_dna(industry_key: Optional[str]) -> dict[str, Any]:
    if not industry_key:
        return {}
    try:
        from industry_intelligence.dna_catalog import get_dna

        d = get_dna(industry_key)
        if not d:
            return {}
        return {
            "found": True,
            "key": d.key,
            "name": d.name,
            "valuation_methods": list(d.valuation_methods),
            "typical_risks": list(d.typical_risks),
            "capital_allocation_typical": d.capital_allocation_typical,
            "competitive_structure": d.competitive_structure,
            "cash_conversion": d.cash_conversion,
            "capital_intensity": d.capital_intensity,
            "primary_cycle": d.primary_cycle,
            "value_drivers": list(d.value_drivers),
            "why_valuation": d.why_valuation,
        }
    except Exception:
        return {}


def _rating(score: int) -> str:
    if score >= 80:
        return "strong"
    if score >= 65:
        return "good"
    if score >= 50:
        return "adequate"
    if score >= 35:
        return "weak"
    return "poor"


def evidence_card(profile: dict[str, Any]) -> dict[str, Any]:
    strength = profile.get("evidence_strength") or "medium"
    missing = list(profile.get("unknowns") or [])[:5]
    card = EvidenceCard(
        strength=strength,
        reasons=[
            f"Profile evidence strength tagged {strength}.",
            "Conclusions are observational and consume Industry DNA where available.",
        ],
        coverage="Structured investment profile + Industry DNA overlay",
        contradictions=[],
        missing_data=missing,
        freshness="mixed",
    )
    return card.to_dict()


def thesis(profile: dict[str, Any]) -> dict[str, Any]:
    dna = _industry_dna(profile.get("industry"))
    t = InvestmentThesis(
        entity=profile["name"],
        industry=profile.get("industry"),
        business_quality=profile["business_quality"],
        industry_position=profile["industry_position"]
        + (f"; structure={dna.get('competitive_structure')}" if dna.get("competitive_structure") else ""),
        competitive_advantage=profile["competitive_advantage"],
        capital_allocation=profile["capital_allocation"]
        or dna.get("capital_allocation_typical")
        or "",
        financial_strength=profile["financial_strength"],
        growth_drivers=list(profile["growth_drivers"]),
        valuation_drivers=list(profile["valuation_drivers"])
        + ([f"Industry methods: {', '.join(dna['valuation_methods'][:3])}"] if dna.get("valuation_methods") else []),
        key_risks=list(profile["key_risks"])[:6],
        catalysts=list(profile["catalysts_pos"])[:4],
        evidence_strength=profile.get("evidence_strength") or "medium",
        unknowns=list(profile.get("unknowns") or [])[:6],
    )
    out = t.to_dict()
    out["summary"] = strip_recommendation_language(
        f"Investment thesis for {profile['name']}: business quality — {profile['business_quality']}. "
        f"Industry position — {profile['industry_position']}. "
        f"Key risks include {', '.join(profile['key_risks'][:3])}. "
        f"Evidence strength: {out['evidence_strength']}. "
        f"No recommendation is issued (policy: {RECOMMENDATION_POLICY})."
    )
    out["industry_dna"] = dna
    return out


def catalysts(profile: dict[str, Any]) -> dict[str, Any]:
    cards: list[CatalystCard] = []
    for i, name in enumerate(profile.get("catalysts_pos") or []):
        cards.append(
            CatalystCard(
                key=f"pos_{i+1}",
                name=name,
                direction="positive",
                probability="medium",
                time_horizon="6-18 months",
                potential_impact="Material to earnings/cash or multiple if sustained",
                confidence=profile.get("evidence_strength") or "medium",
                supporting_evidence=[f"Mapped from investment profile for {profile['name']}"],
            )
        )
    for i, name in enumerate(profile.get("catalysts_neg") or []):
        cards.append(
            CatalystCard(
                key=f"neg_{i+1}",
                name=name,
                direction="negative",
                probability="medium",
                time_horizon="0-18 months",
                potential_impact="Could compress margins, growth, or multiples",
                confidence=profile.get("evidence_strength") or "medium",
                supporting_evidence=[f"Mapped from investment profile for {profile['name']}"],
            )
        )
    summary = strip_recommendation_language(
        f"Catalysts for {profile['name']}: positive — "
        + "; ".join(profile.get("catalysts_pos") or ["none listed"])
        + ". Negative — "
        + "; ".join(profile.get("catalysts_neg") or ["none listed"])
        + ". Each catalyst carries probability, horizon, impact, and confidence — not a trade call."
    )
    return {
        "entity": profile["name"],
        "catalysts": [c.to_dict() for c in cards],
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def risks(profile: dict[str, Any]) -> dict[str, Any]:
    dna = _industry_dna(profile.get("industry"))
    industry_risks = list(dna.get("typical_risks") or [])
    cards: list[RiskCard] = []
    # Map profile key risks onto typed risks
    typed = list(RISK_TYPES)
    profile_risks = list(profile.get("key_risks") or [])
    for i, rname in enumerate(profile_risks):
        key = typed[i % len(typed)]
        cards.append(
            RiskCard(
                key=key,
                name=rname,
                probability="medium",
                severity="high" if i < 2 else "medium",
                mitigants=["Monitor leading indicators", "Stress assumptions in bear case"],
                evidence=[f"Investment profile risk for {profile['name']}"],
                leading_indicators=list(profile.get("monitoring") or [])[:3],
            )
        )
    # Ensure industry risks appear
    for ir in industry_risks[:3]:
        if not any(ir.lower() in c.name.lower() for c in cards):
            cards.append(
                RiskCard(
                    key="industry",
                    name=ir,
                    probability="medium",
                    severity="medium",
                    mitigants=["Industry DNA monitoring KPIs"],
                    evidence=["Industry DNA typical risks"],
                    leading_indicators=["Industry cycle indicators"],
                )
            )
    summary = strip_recommendation_language(
        f"Key investment risks for {profile['name']}: "
        + "; ".join(profile_risks[:5])
        + ". Risks include probability, severity, mitigants, and leading indicators. "
        + "No BUY/SELL recommendation is issued."
    )
    return {
        "entity": profile["name"],
        "risks": [c.to_dict() for c in cards],
        "industry_risks": industry_risks,
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def scenarios(profile: dict[str, Any]) -> dict[str, Any]:
    cases = {
        "bull": ScenarioCard(
            case="bull",
            revenue="Above-trend growth as catalysts land",
            margins="Expansion via mix/utilization/pricing",
            cash_flow="FCF improves with operating leverage",
            capital_allocation="Growth investment funded by internal cash",
            valuation_drivers=list(profile["valuation_drivers"][:3]),
            risks=["Execution shortfall vs bull assumptions"],
            key_assumptions=list(profile["catalysts_pos"][:3]) or ["Demand recovery"],
            confidence="medium",
            unknowns=list(profile.get("unknowns") or [])[:3],
        ),
        "base": ScenarioCard(
            case="base",
            revenue="Trend growth aligned with industry mid-cycle",
            margins="Stable to modestly expanding",
            cash_flow="Cash conversion consistent with industry DNA",
            capital_allocation=profile["capital_allocation"],
            valuation_drivers=list(profile["valuation_drivers"][:3]),
            risks=list(profile["key_risks"][:2]),
            key_assumptions=["No severe cycle shock", "Management execution continues"],
            confidence="medium",
            unknowns=list(profile.get("unknowns") or [])[:3],
        ),
        "bear": ScenarioCard(
            case="bear",
            revenue="Growth slows or contracts",
            margins="Compression from costs/competition/cycle",
            cash_flow="FCF weakens; reinvestment needs persist",
            capital_allocation="Defensive: cut growth spend, protect balance sheet",
            valuation_drivers=["Multiple compression", "Earnings risk"],
            risks=list(profile["key_risks"][:4]),
            key_assumptions=list(profile["catalysts_neg"][:3]) or ["Demand shock"],
            confidence="medium",
            unknowns=["Depth/duration of downturn"],
        ),
    }
    summary = strip_recommendation_language(
        f"Scenarios for {profile['name']}: bull (catalysts land), base (mid-cycle), bear (risks bite). "
        f"Each scenario covers revenue, margins, cash flow, capital allocation, and valuation drivers. "
        f"No price targets are produced."
    )
    return {
        "entity": profile["name"],
        "scenarios": {k: v.to_dict() for k, v in cases.items()},
        "summary": summary,
        "policy": "no_price_targets",
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def quality(profile: dict[str, Any]) -> dict[str, Any]:
    scores = dict(profile.get("quality_scores") or {})
    dims: list[QualityDimension] = []
    for key in QUALITY_DIMENSIONS:
        sc = int(scores.get(key, 55))
        dims.append(
            QualityDimension(
                key=key,
                score=sc,
                rating=_rating(sc),
                why=f"{key.replace('_', ' ').title()} scored {sc}/100 on structured evidence for {profile['name']}.",
                helped=[profile["business_quality"][:80]] if sc >= 65 else [],
                hurt=list(profile["key_risks"][:1]) if sc < 70 else [],
                unknowns=list(profile.get("unknowns") or [])[:2],
            )
        )
    avg = round(sum(d.score for d in dims) / max(1, len(dims)))
    summary = strip_recommendation_language(
        f"Quality scorecard for {profile['name']}: composite {avg}/100 ({_rating(avg)}). "
        f"Strongest dimensions: "
        + ", ".join(d.key.replace("_", " ") for d in sorted(dims, key=lambda x: -x.score)[:3])
        + ". Weakest: "
        + ", ".join(d.key.replace("_", " ") for d in sorted(dims, key=lambda x: x.score)[:2])
        + ". Scorecard is observational — not a recommendation."
    )
    return {
        "entity": profile["name"],
        "composite_score": avg,
        "composite_rating": _rating(avg),
        "dimensions": [d.to_dict() for d in dims],
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def valuation_intel(profile: dict[str, Any]) -> dict[str, Any]:
    dna = _industry_dna(profile.get("industry"))
    methods = list(dna.get("valuation_methods") or ["Industry-appropriate multiples"])
    summary = strip_recommendation_language(
        f"Valuation intelligence for {profile['name']}: industry methods typically "
        f"{', '.join(methods)}. Drivers — {', '.join(profile['valuation_drivers'][:4])}. "
        f"{dna.get('why_valuation') or 'Valuation changes with growth, returns, and cycle.'} "
        f"Sensitivity runs through drivers and cost of capital — no price targets, no BUY/SELL."
    )
    return {
        "entity": profile["name"],
        "industry": profile.get("industry"),
        "valuation_methods": methods,
        "value_drivers": list(profile["valuation_drivers"]),
        "why_valuation_changes": [
            "Growth vs expectations",
            "ROIC / capital efficiency",
            "Margin trajectory",
            "Multiple expansion/compression with cycle and rates",
            "Cost of capital shifts",
        ],
        "sensitivity": [
            "Margins ± industry-typical band",
            "Growth ± cycle band",
            "Discount rate / cost of equity band",
        ],
        "why": dna.get("why_valuation") or "",
        "summary": summary,
        "policy": "no_price_targets",
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def capital_allocation(profile: dict[str, Any]) -> dict[str, Any]:
    dna = _industry_dna(profile.get("industry"))
    summary = strip_recommendation_language(
        f"Capital allocation for {profile['name']}: {profile['capital_allocation']}. "
        f"Industry typical: {dna.get('capital_allocation_typical') or 'see Industry DNA'}. "
        f"Evaluate allocation quality, discipline, consistency, and historical outcomes. "
        f"Observations only — recommendation policy remains no buy / no sell."
    )
    return {
        "entity": profile["name"],
        "allocation_summary": profile["capital_allocation"],
        "industry_typical": dna.get("capital_allocation_typical"),
        "dimensions": {
            "organic_investment": "Primary growth path when ROIC is attractive",
            "dividends": "Return excess cash when buffers allow",
            "buybacks": "Opportunistic when capital is surplus to growth needs",
            "acquisitions": "Only when strategic fit and returns clear",
            "debt_reduction": "Priority when leverage or refinancing risk rises",
            "capex": dna.get("capital_intensity") or "Industry-dependent",
        },
        "evaluation": {
            "allocation_quality": _rating(int((profile.get("quality_scores") or {}).get("capital_allocation", 60))),
            "discipline": "Assess consistency of ROIC vs reinvestment claims",
            "consistency": "Compare stated policy vs multi-year cash uses",
            "historical_outcomes": "Track incremental ROIC and dilution/leverage outcomes",
        },
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def committee(profile: dict[str, Any]) -> dict[str, Any]:
    th = thesis(profile)
    rk = risks(profile)
    ql = quality(profile)
    contributions = []
    role_map = {
        "business_analyst": [th["business_quality"], th["competitive_advantage"]],
        "financial_analyst": [th["financial_strength"], "Cash conversion and earnings quality matter."],
        "industry_analyst": [th["industry_position"], f"Industry: {profile.get('industry')}"],
        "valuation_analyst": [", ".join(th["valuation_drivers"][:3]), "No price targets."],
        "risk_analyst": ["; ".join(th["key_risks"][:3]), "Tail risks need monitoring points."],
        "governance_analyst": ["Governance score from quality scorecard.", "Board/capital discipline questions."],
        "portfolio_analyst": ["Relative quality vs peers is observational.", "Correlation to sector cycle."],
        "macro_analyst": ["Rates, growth, and commodity overlays by industry DNA.", "Cycle sensitivity."],
        "committee_chair": [
            "Synthesize quality, risks, catalysts, and unknowns.",
            "Committee does not issue BUY or SELL.",
        ],
    }
    for role in COMMITTEE_ROLES:
        obs = role_map.get(role, ["Observation pending denser evidence."])
        contributions.append(
            CommitteeContribution(
                role=role,
                observations=[strip_recommendation_language(o) for o in obs],
                questions=[f"What evidence would change the {role.replace('_', ' ')} view?"],
                agreement=["Evidence-backed quality and risk framing"],
                disagreement=["Magnitude of catalysts and cycle timing"] if role != "committee_chair" else [],
                confidence=profile.get("evidence_strength") or "medium",
            ).to_dict()
        )
    summary = strip_recommendation_language(
        f"Investment committee simulation for {profile['name']}: "
        f"composite quality {ql['composite_score']}/100; "
        f"primary risks {', '.join(th['key_risks'][:3])}. "
        f"Chair synthesis: evaluate attractiveness observationally; "
        f"recommendation policy remains NO BUY / NO SELL."
    )
    return {
        "entity": profile["name"],
        "contributions": contributions,
        "synthesis": summary,
        "summary": summary,
        "quality_composite": ql["composite_score"],
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }


def graph(profile: dict[str, Any]) -> dict[str, Any]:
    dna = _industry_dna(profile.get("industry"))
    obj = {
        "company": profile["name"],
        "financial": profile["financial_strength"],
        "business": profile["business_quality"],
        "industry": {
            "key": profile.get("industry"),
            "dna": dna,
        },
        "valuation": profile["valuation_drivers"],
        "capital_allocation": profile["capital_allocation"],
        "risks": profile["key_risks"],
        "catalysts": {
            "positive": profile.get("catalysts_pos"),
            "negative": profile.get("catalysts_neg"),
        },
        "evidence": evidence_card(profile),
        "scenarios": ["bull", "base", "bear"],
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
    }
    return {
        "entity": profile["name"],
        "investment_object": obj,
        "summary": strip_recommendation_language(
            f"Investment object for {profile['name']} links financial, business, industry DNA, "
            f"valuation drivers, capital allocation, risks, catalysts, evidence, and scenarios."
        ),
        "fabricated": False,
    }


def compare_quality(a_key: str, b_key: str) -> dict[str, Any]:
    a, b = get_profile(a_key), get_profile(b_key)
    if not a or not b:
        return {"found": False, "summary": "", "fabricated": False}
    qa, qb = quality(a), quality(b)
    summary = strip_recommendation_language(
        f"Quality comparison — {a['name']} vs {b['name']}: "
        f"composite {qa['composite_score']} vs {qb['composite_score']}. "
        f"{a['name']} business quality: {a['business_quality'][:100]}. "
        f"{b['name']} business quality: {b['business_quality'][:100]}. "
        f"This is a relative quality assessment, not a BUY/SELL recommendation."
    )
    return {
        "found": True,
        "entities": [a["name"], b["name"]],
        "scores": {a["key"]: qa["composite_score"], b["key"]: qb["composite_score"]},
        "summary": summary,
        "recommendation": None,
        "recommendation_policy": RECOMMENDATION_POLICY,
        "fabricated": False,
    }
